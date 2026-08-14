# -*- coding: utf-8 -*-
"""
promote.py — safe promotion of APPROVED staging_artifacts into the reference
catalog (security_artifacts).

  validate  : check every ready item is promotable (no writes)
  plan      : produce a reviewable JSON plan + checksum (no writes to catalog)
  apply     : write a plan in ONE transaction per batch (all-or-nothing),
              normalize child collections, set promoted_artifact_id, audit;
              idempotent; rejects a stale plan (staging changed since plan)
  rollback  : reverse only what a batch created; refuse if downstream refs exist

Never modifies raw_artifacts. Never deletes staging.
"""
import argparse
import hashlib
import io
import json
import os
import sqlite3
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import _promote_common as C

PLAN_DIR = os.path.join(ROOT, 'consolidation', 'promotion')

# schema binds priority to its weight (CHECK): keep them in lock-step.
PRIORITY_WEIGHT = {'PRI-CRITICAL': 10, 'PRI-HIGH': 7, 'PRI-MEDIUM': 4, 'PRI-LOW': 1}

SOURCE_TYPE_MAP = {'FRAMEWORK': 'STANDARD', 'STANDARD': 'STANDARD', 'REGULATION': 'REGULATION',
                   'POLICY_TEMPLATE': 'DOCUMENT', 'THREAT_INTEL': 'DOCUMENT', 'GUIDELINE': 'DOCUMENT',
                   'DOCUMENT': 'DOCUMENT', 'SYSTEM': 'SYSTEM', 'TOOL': 'TOOL'}


def connect(db):
    if not os.path.exists(db):
        print(f"DB not found: {db}"); sys.exit(1)
    c = sqlite3.connect(db); c.row_factory = sqlite3.Row; c.execute("PRAGMA foreign_keys=ON")
    return c


def final_id(row):
    suffix = row['id'].split('-', 2)[-1]  # STG-CANON-AI-02 -> AI-02
    return f"SG-{row['proposed_type'][4:]}-{suffix}"


def derive_catalog_fields(conn, row, maps):
    first = maps[0] if maps else {}
    raw = conn.execute("SELECT source_catalog_id, source_type FROM raw_artifacts WHERE id=?",
                       (first.get('raw_id'),)).fetchone() if first.get('raw_id') else None
    cat_id = raw['source_catalog_id'] if raw else None
    src_type = SOURCE_TYPE_MAP.get((raw['source_type'] or '').upper() if raw else '', 'STANDARD')
    source = 'SRC-REG' if src_type == 'REGULATION' else 'SRC-STD'
    return {'source_catalog_id': cat_id, 'source_type': src_type, 'source': source,
            'granularity_level': 'GRN-MEDIUM',
            'source_document': first.get('source_document') or 'SecureGuide consolidated'}


def ready_rows(conn):
    return conn.execute("SELECT * FROM staging_artifacts WHERE ready_for_promotion=1 ORDER BY id").fetchall()


# ------------------------------- validate ----------------------------------
def cmd_validate(args):
    conn = connect(args.db); valid = C.load_valid(conn)
    rows = ready_rows(conn)
    bad = 0
    print(f"validating {len(rows)} ready item(s)...")
    for r in rows:
        blockers = C.promotion_blockers(r, valid)
        print(("  OK   " if not blockers else "  FAIL ") + r['id'] + (f"  -> {blockers}" if blockers else ""))
        if blockers:
            bad += 1
    if bad:
        print(f"VALIDATION FAILED: {bad} item(s) not promotable."); sys.exit(1)
    print("All ready items are promotable.")


# --------------------------------- plan ------------------------------------
def build_plan(conn, valid, batch_id):
    items, excluded, conflicts = [], [], []
    for r in conn.execute(
            "SELECT * FROM staging_artifacts "
            "WHERE ready_for_promotion=1 OR final_review_status IS NOT NULL ORDER BY id"):
        if r['ready_for_promotion'] != 1:
            excluded.append({'staging_id': r['id'], 'reason': f"not ready ({r['final_review_status']})"})
            continue
        blockers = C.promotion_blockers(r, valid)
        if blockers:
            excluded.append({'staging_id': r['id'], 'reason': 'blockers', 'blockers': blockers})
            continue
        fid = final_id(r)
        maps = json.loads(r['proposed_mappings_json']) if r['proposed_mappings_json'] else []
        existing = conn.execute("SELECT id, promoted_from FROM security_artifacts WHERE id=?", (fid,)).fetchone() \
            if _has_col(conn, 'security_artifacts', 'promoted_from') else conn.execute("SELECT id FROM security_artifacts WHERE id=?", (fid,)).fetchone()
        prev = r['promoted_artifact_id']
        if existing:
            if prev == fid:
                action = 'SKIP'  # already promoted from this staging row (idempotent)
            else:
                action = 'CONFLICT'
                conflicts.append({'staging_id': r['id'], 'final_artifact_id': fid,
                                  'reason': 'target id already exists from a different source'})
        else:
            action = 'INSERT'
        mappings = [{'framework': m.get('source_document'), 'version': m.get('source_version') or '1',
                     'reference': m.get('source_section') or m.get('raw_id'),
                     'mapping_strength': m.get('mapping_strength'), 'rationale': m.get('rationale')} for m in maps]
        tags = json.loads(r['proposed_tags_json']) if r['proposed_tags_json'] else []
        rels = json.loads(r['proposed_relationships_json']) if r['proposed_relationships_json'] else []

        def jc(col):  # enrichment JSON collection (col may be absent on pre-007 rows)
            v = r[col] if col in r.keys() else None
            return json.loads(v) if v else ([] if not col.endswith('verification_json') else {})
        items.append({'staging_id': r['id'], 'final_artifact_id': fid, 'action': action,
                      'source_staging_hash': r['content_hash'], 'type': r['proposed_type'],
                      'sub_domain': r['proposed_sub_domain'], 'equivalence_group': r['canonical_group_id'],
                      'mappings': mappings, 'tags': tags, 'relationships': rels,
                      'actions': jc('proposed_actions_json'), 'variants': jc('proposed_variants_json'),
                      'objectives': jc('proposed_security_objectives_json'), 'csf': jc('proposed_csf_functions_json'),
                      'purposes': jc('proposed_control_purposes_json'), 'impl_types': jc('proposed_implementation_types_json'),
                      'maturity': jc('proposed_maturity_requirements_json'), 'verification': jc('proposed_verification_json'),
                      'threats': jc('proposed_threats_json'), 'platforms': jc('proposed_platforms_json'),
                      'provenance': (json.loads(r['proposed_legacy_provenance_json'])
                                     if ('proposed_legacy_provenance_json' in r.keys() and r['proposed_legacy_provenance_json'])
                                     else None)})
    counts = {'insert': sum(1 for i in items if i['action'] == 'INSERT'),
              'skip': sum(1 for i in items if i['action'] == 'SKIP'),
              'conflict': sum(1 for i in items if i['action'] == 'CONFLICT')}
    plan = {'batch_id': batch_id, 'items': items, 'excluded': excluded, 'conflicts': conflicts, 'counts': counts}
    plan['plan_checksum'] = hashlib.sha256(
        json.dumps({k: plan[k] for k in ('batch_id', 'items')}, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    return plan


def _has_col(conn, table, col):
    return any(r[1] == col for r in conn.execute(f"PRAGMA table_info({table})"))


def cmd_plan(args):
    conn = connect(args.db); valid = C.load_valid(conn)
    plan = build_plan(conn, valid, args.batch)
    os.makedirs(PLAN_DIR, exist_ok=True)
    path = args.out or os.path.join(PLAN_DIR, f"plan-{args.batch}.json")
    io.open(path, 'w', encoding='utf-8').write(json.dumps(plan, ensure_ascii=False, indent=2))
    conn.execute("INSERT OR REPLACE INTO promotion_batches (id, plan_hash, status, item_count, notes) VALUES (?,?,?,?,?)",
                 (args.batch, plan['plan_checksum'], 'PLANNED', len(plan['items']), f"plan file: {os.path.basename(path)}"))
    conn.execute("INSERT INTO promotion_audit_log (batch_id, event, detail) VALUES (?,?,?)",
                 (args.batch, 'PLAN', f"{plan['counts']} checksum={plan['plan_checksum'][:12]}"))
    conn.commit()
    print(f"PLAN {args.batch}: {plan['counts']}  conflicts={len(plan['conflicts'])}  excluded={len(plan['excluded'])}")
    print(f"checksum: {plan['plan_checksum']}")
    print(f"written: {path}")
    if plan['conflicts']:
        print("CONFLICTS present — resolve before apply:", plan['conflicts'])


# --------------------------------- apply -----------------------------------
CATALOG_COLS = ('id', 'source_catalog_id', 'title_en', 'title_ar', 'description_en', 'description_ar',
                'definition_short_en', 'definition_short_ar', 'definition_full_en', 'definition_full_ar',
                'objective_en', 'objective_ar', 'canonical_statement', 'type', 'abstraction_level',
                'primary_domain', 'sub_domain', 'source', 'source_type', 'obligation_level',
                'requirement_type', 'granularity_level', 'control_nature', 'control_function', 'testability',
                'priority', 'priority_weight', 'review_frequency',
                'evidence_required', 'evidence_required_ar', 'verification_method_note', 'verification_method_note_ar',
                'scoring_weight', 'risk_reduction', 'effort_level', 'tier',
                'classification_confidence', 'classification_rationale', 'ai_review_status',
                'requires_human_review', 'publication_status', 'source_document', 'is_active')


def cmd_apply(args):
    conn = connect(args.db); valid = C.load_valid(conn)
    plan = json.load(io.open(args.plan, encoding='utf-8'))
    batch = plan['batch_id']
    brow = conn.execute("SELECT * FROM promotion_batches WHERE id=?", (batch,)).fetchone()
    if not brow:
        print(f"batch {batch} not found (run plan first)."); sys.exit(1)
    if brow['status'] == 'ROLLED_BACK':
        print(f"batch {batch} was rolled back; create a new plan."); sys.exit(1)

    # optimistic staleness check: staging content must match the plan
    for it in plan['items']:
        r = conn.execute("SELECT * FROM staging_artifacts WHERE id=?", (it['staging_id'],)).fetchone()
        if not r:
            print(f"STALE: staging {it['staging_id']} missing."); sys.exit(1)
        if C.content_hash(r) != it['source_staging_hash']:
            conn.execute("INSERT INTO promotion_audit_log (batch_id,event,detail) VALUES (?,?,?)",
                         (batch, 'REJECT', f"stale plan: {it['staging_id']} changed"))
            conn.commit()
            print(f"STALE PLAN: staging {it['staging_id']} changed since plan. Aborting (nothing written)."); sys.exit(1)

    inserted = skipped = 0
    try:
        conn.execute("BEGIN")
        for it in plan['items']:
            fid = it['final_artifact_id']
            r = conn.execute("SELECT * FROM staging_artifacts WHERE id=?", (it['staging_id'],)).fetchone()
            # re-evaluate existence at apply time for idempotency
            if conn.execute("SELECT 1 FROM security_artifacts WHERE id=?", (fid,)).fetchone():
                if r['promoted_artifact_id'] == fid:
                    skipped += 1
                    conn.execute("INSERT INTO promotion_audit_log (batch_id,event,detail) VALUES (?,?,?)",
                                 (batch, 'APPLY_SKIP', f"{it['staging_id']} already promoted -> {fid}"))
                    continue
                raise RuntimeError(f"conflict: {fid} exists but not from {it['staging_id']}")
            # final blocker guard inside the transaction
            blk = C.promotion_blockers(r, valid)
            if blk:
                raise RuntimeError(f"{it['staging_id']} blockers at apply: {blk}")
            maps = json.loads(r['proposed_mappings_json']) if r['proposed_mappings_json'] else []
            d = derive_catalog_fields(conn, r, maps)
            def sg(k):  # safe staging get (enrichment cols may be absent on pre-007 rows)
                return r[k] if k in r.keys() else None
            review_evidenced = (
                r['final_review_status'] in ('APPROVED', 'SPLIT_AND_APPROVED')
                and bool(r['approved_by']) and bool(r['approved_at'])
            )
            needs_review = bool(r['requires_human_review']) or (
                r['classification_confidence'] is not None
                and r['classification_confidence'] <= 0.70
            )
            ai_review_status = (
                'AIR-HUMAN-APPROVED' if review_evidenced
                else ('AIR-HUMAN-REVIEW' if needs_review else 'AIR-AUTO-ACCEPTED')
            )
            vals = {
                'id': fid, 'source_catalog_id': d['source_catalog_id'], 'title_en': r['title_en'],
                'title_ar': sg('title_ar'),
                'description_en': r['definition_short_en'], 'description_ar': sg('definition_short_ar'),
                'definition_short_en': r['definition_short_en'], 'definition_short_ar': sg('definition_short_ar'),
                'definition_full_en': r['definition_full_en'], 'definition_full_ar': sg('definition_full_ar'),
                'objective_en': r['objective_en'], 'objective_ar': sg('objective_ar'),
                'canonical_statement': r['canonical_statement'], 'type': r['proposed_type'],
                'abstraction_level': r['proposed_abstraction_level'], 'primary_domain': r['proposed_primary_domain'],
                'sub_domain': r['proposed_sub_domain'], 'source': d['source'], 'source_type': d['source_type'],
                'obligation_level': r['proposed_obligation_level'],
                'requirement_type': r['proposed_requirement_type'],  # NULL for non-ART-REQ (schema-structural N/A)
                'granularity_level': d['granularity_level'],
                # SADP §2.2: control_* / requirement_type are type-conditional — the frozen
                # schema CHECKs bind them to NULL when structurally N/A (NULL == the *-NA
                # fallback, enforced structurally). Real values still come from staging.
                'control_nature': r['proposed_control_nature'],
                'control_function': r['proposed_control_function'], 'testability': r['proposed_testability'],
                'priority': (sg('proposed_priority') or 'PRI-MEDIUM'),
                'priority_weight': PRIORITY_WEIGHT.get(sg('proposed_priority') or 'PRI-MEDIUM', 4),
                'review_frequency': 'AD-HOC',   # intrinsic baseline (no operational schedule in the catalog)
                'evidence_required': sg('evidence_en'), 'evidence_required_ar': sg('evidence_ar'),
                'verification_method_note': sg('verification_method_note'),
                'verification_method_note_ar': sg('verification_method_note_ar'),
                'scoring_weight': sg('proposed_scoring_weight'), 'risk_reduction': sg('proposed_risk_reduction'),
                'effort_level': sg('proposed_effort_level'), 'tier': sg('proposed_tier'),
                'classification_confidence': r['classification_confidence'],
                'classification_rationale': r['classification_rationale'],
                'ai_review_status': ai_review_status,
                'requires_human_review': int(needs_review and not review_evidenced),
                'publication_status': 'APPROVED',
                'source_document': d['source_document'], 'is_active': 1,
            }
            cols = ','.join(CATALOG_COLS)
            conn.execute(f"INSERT INTO security_artifacts ({cols}) VALUES ({','.join('?' for _ in CATALOG_COLS)})",
                         [vals[c] for c in CATALOG_COLS])
            nmap = 0
            for m in it['mappings']:
                conn.execute("INSERT INTO framework_mappings (artifact_id,framework,version,reference,mapping_strength,rationale) VALUES (?,?,?,?,?,?)",
                             (fid, m['framework'], m['version'], m['reference'], m['mapping_strength'], m['rationale']))
                nmap += 1
            ntag = 0
            for tag in it.get('tags', []):
                conn.execute(
                    "INSERT INTO artifact_tags (artifact_id, tag_type, tag_value) VALUES (?,?,?)",
                    (fid, tag['tag_type'], tag['tag_value'])
                )
                ntag += 1
            nrel = 0
            for rel in it['relationships']:
                conn.execute("INSERT INTO artifact_relationships (source_id,target_id,relation_type,resolution_status,resolution_note) VALUES (?,?,?,?,?)",
                             (fid, rel['target_id'], rel['relation_type'], rel.get('resolution_status'), rel.get('resolution_note'))); nrel += 1
            # ---- rich content-enrichment collections (007), same transaction ----
            for a in it.get('actions', []):
                conn.execute("INSERT INTO artifact_actions (artifact_id,kind,seq,text_en,text_ar) VALUES (?,?,?,?,?)",
                             (fid, a.get('kind', 'ACTION'), a['seq'], a['text_en'], a.get('text_ar')))
            for v in it.get('variants', []):
                conn.execute("INSERT INTO artifact_variants (artifact_id,platform,title_en,title_ar,sort_order) VALUES (?,?,?,?,?)",
                             (fid, v['platform'], v.get('title_en'), v.get('title_ar'), v.get('sort_order', 0)))
            # plain INSERT (not OR IGNORE): bad codes are rejected upstream by
            # promotion_blockers; any residual violation must abort the batch,
            # never silently vanish.
            for o in it.get('objectives', []):
                conn.execute("INSERT INTO artifact_security_objectives (artifact_id,objective_code,strength) VALUES (?,?,?)",
                             (fid, o['objective_code'], o['strength']))
            for cf in it.get('csf', []):
                conn.execute("INSERT INTO artifact_csf_functions (artifact_id,csf_code,strength) VALUES (?,?,?)",
                             (fid, cf['csf_code'], cf['strength']))
            for p in it.get('purposes', []):
                conn.execute("INSERT INTO artifact_control_purposes (artifact_id,purpose_code) VALUES (?,?)",
                             (fid, p['purpose_code'] if isinstance(p, dict) else p))
            for im in it.get('impl_types', []):
                conn.execute("INSERT INTO artifact_implementation_types (artifact_id,impl_type_code) VALUES (?,?)",
                             (fid, im['impl_type_code'] if isinstance(im, dict) else im))
            for mr in it.get('maturity', []):
                conn.execute("INSERT INTO artifact_maturity_requirements (artifact_id,tier_code,objective_en,objective_ar,scope_en,scope_ar,verification_en,verification_ar) VALUES (?,?,?,?,?,?,?,?)",
                             (fid, mr['tier_code'], mr.get('objective_en'), mr.get('objective_ar'), mr.get('scope_en'), mr.get('scope_ar'), mr.get('verification_en'), mr.get('verification_ar')))
            verif = it.get('verification') or {}
            for et in verif.get('evidence_types', []):
                conn.execute("INSERT INTO artifact_verification_evidence_types (artifact_id,evidence_type) VALUES (?,?)", (fid, et))
            for st in verif.get('testing_steps', []):
                conn.execute("INSERT INTO artifact_actions (artifact_id,kind,seq,text_en,text_ar) VALUES (?,'VERIFICATION',?,?,?)",
                             (fid, st['seq'], st['text_en'], st.get('text_ar')))
            # ---- SADP dimensions: threats (§2.4/§3.1) + platforms + legacy provenance ----
            threats = [t.get('threat_code') if isinstance(t, dict) else t for t in it.get('threats', [])]
            threats = [t for t in dict.fromkeys(threats) if t]     # dedup, keep order
            if not threats:
                threats = ['THR-NA']                               # §2.2: threat always populated
            for tc in threats:
                conn.execute("INSERT INTO artifact_threats (artifact_id,threat_code) VALUES (?,?)", (fid, tc))
            for p in it.get('platforms', []):
                pc = p.get('platform_code') if isinstance(p, dict) else p
                conn.execute("INSERT OR IGNORE INTO artifact_platforms (artifact_id,platform_code) VALUES (?,?)", (fid, pc))
            prov = it.get('provenance')
            if prov:
                # Historical payloads used source-branded keys.  The forward
                # migration keeps the JSON value but the active API resolves
                # it generically and writes only neutral schema names.
                def legacy_value(suffix):
                    return prov.get(f'legacy_{suffix}') or next(
                        (value for key, value in prov.items() if key.endswith(f'_{suffix}')),
                        None,
                    )
                conn.execute("INSERT INTO catalog_legacy_provenance (artifact_id,legacy_id,legacy_domain,legacy_sub) VALUES (?,?,?,?)",
                             (fid, legacy_value('id'), legacy_value('domain'), legacy_value('sub')))
                for a in dict.fromkeys(prov.get('assets') or []):
                    conn.execute("INSERT OR IGNORE INTO catalog_legacy_assets (artifact_id,asset_ref) VALUES (?,?)", (fid, a))
            conn.execute("UPDATE staging_artifacts SET promoted_artifact_id=? WHERE id=?", (fid, it['staging_id']))
            conn.execute("""INSERT OR REPLACE INTO promotion_batch_items
                (batch_id,staging_id,final_artifact_id,source_staging_hash,action,mappings_created,tags_created,relationships_created)
                VALUES (?,?,?,?,?,?,?,?)""",
                (batch, it['staging_id'], fid, it['source_staging_hash'], 'INSERT', nmap, ntag, nrel))
            conn.execute("INSERT INTO promotion_audit_log (batch_id,event,detail) VALUES (?,?,?)",
                         (batch, 'APPLY', f"{it['staging_id']} -> {fid} (+{nmap} mappings)"))
            inserted += 1
        conn.execute("UPDATE promotion_batches SET status='COMPLETED', applied_at=datetime('now'), item_count=? WHERE id=?",
                     (len(plan['items']), batch))
        conn.execute("COMMIT")
    except Exception as e:
        conn.execute("ROLLBACK")
        conn.execute("UPDATE promotion_batches SET status='FAILED' WHERE id=?", (batch,))
        conn.execute("INSERT INTO promotion_audit_log (batch_id,event,detail) VALUES (?,?,?)", (batch, 'ERROR', str(e)))
        conn.commit()
        print(f"APPLY FAILED (transaction rolled back, nothing written): {e}"); sys.exit(1)
    conn.commit()
    print(f"APPLIED batch {batch}: inserted={inserted} skipped={skipped}")
    print(f"security_artifacts now: {conn.execute('SELECT COUNT(*) FROM security_artifacts').fetchone()[0]}")


# ------------------------------- rollback ----------------------------------
def cmd_rollback(args):
    conn = connect(args.db)
    batch = args.batch
    items = conn.execute("SELECT * FROM promotion_batch_items WHERE batch_id=? AND action='INSERT'", (batch,)).fetchall()
    if not items:
        print(f"no INSERT items for batch {batch}."); sys.exit(1)
    # refuse if downstream references exist (unless --force)
    if not args.force:
        blocked = []
        for it in items:
            fid = it['final_artifact_id']
            refs = conn.execute("SELECT COUNT(*) FROM profile_artifacts WHERE artifact_id=?", (fid,)).fetchone()[0]
            refs += conn.execute("SELECT COUNT(*) FROM artifact_relationships WHERE source_id=? OR target_id=?", (fid, fid)).fetchone()[0]
            refs += conn.execute("SELECT COUNT(*) FROM template_items WHERE artifact_id=?", (fid,)).fetchone()[0]
            if refs:
                blocked.append((fid, refs))
        if blocked:
            print(f"ROLLBACK REFUSED: downstream references exist {blocked}. Use --force to override (documented).")
            sys.exit(1)
    try:
        conn.execute("BEGIN")
        for it in items:
            fid = it['final_artifact_id']
            conn.execute("DELETE FROM framework_mappings WHERE artifact_id=?", (fid,))
            conn.execute("DELETE FROM artifact_tags WHERE artifact_id=?", (fid,))
            conn.execute("DELETE FROM artifact_relationships WHERE source_id=? OR target_id=?", (fid, fid))
            for t in ('artifact_actions', 'artifact_variants', 'artifact_security_objectives',
                      'artifact_csf_functions', 'artifact_control_purposes', 'artifact_implementation_types',
                      'artifact_maturity_requirements', 'artifact_verification_evidence_types',
                      'artifact_threats', 'artifact_platforms', 'catalog_legacy_provenance', 'catalog_legacy_assets'):
                conn.execute(f"DELETE FROM {t} WHERE artifact_id=?", (fid,))
            conn.execute("DELETE FROM security_artifacts WHERE id=?", (fid,))
            conn.execute("UPDATE staging_artifacts SET promoted_artifact_id=NULL WHERE id=?", (it['staging_id'],))
        conn.execute("UPDATE promotion_batches SET status='ROLLED_BACK', rolled_back_at=datetime('now') WHERE id=?", (batch,))
        conn.execute("INSERT INTO promotion_audit_log (batch_id,event,detail) VALUES (?,?,?)",
                     (batch, 'ROLLBACK', f"reverted {len(items)} artifact(s)"))
        conn.execute("COMMIT")
    except Exception as e:
        conn.execute("ROLLBACK"); conn.commit()
        print(f"ROLLBACK FAILED: {e}"); sys.exit(1)
    conn.commit()
    print(f"ROLLED BACK batch {batch}: reverted {len(items)} artifact(s).")
    print(f"security_artifacts now: {conn.execute('SELECT COUNT(*) FROM security_artifacts').fetchone()[0]}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    for name in ('validate', 'plan', 'apply', 'rollback'):
        p = sub.add_parser(name)
        p.add_argument('--db', default=os.path.join(ROOT, 'pilot.db'))
        if name == 'plan':
            p.add_argument('--batch', default='PROMO-BATCH-1')
            p.add_argument('--out')
        if name == 'apply':
            p.add_argument('--plan', required=True)
        if name == 'rollback':
            p.add_argument('--batch', required=True)
            p.add_argument('--force', action='store_true')
    args = ap.parse_args()
    {'validate': cmd_validate, 'plan': cmd_plan, 'apply': cmd_apply, 'rollback': cmd_rollback}[args.cmd](args)


if __name__ == '__main__':
    main()
