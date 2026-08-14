# -*- coding: utf-8 -*-
"""
batch_process.py — First-pass curation of a SAMPLE of raw artifacts.

Proves the pipeline end-to-end on a small, diverse sample (default 30):
    raw_artifacts -> staging_artifacts
      -> English canonical draft (title/definition, English-first)
      -> USACM type + SDT domain/sub-domain (heuristic first pass)
      -> confidence + rationale + quality_score
      -> curation_status / requires_human_review

This is a HEURISTIC first pass, NOT the final AI classifier: it uses source
classification hints when present, else keyword rules + SDT tie-breakers, and
routes anything at confidence <= 0.70 (or ambiguous) to human review. It never
writes security_artifacts and never invents enum values outside USACM/SDT.

Idempotent: staging id = STG-<raw_id>; existing rows are skipped unless --force.

Usage:
    python scripts/batch_process.py [--db PATH] [--limit 30] [--force]
"""
import argparse
import json
import os
import re
import sqlite3
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DEFAULT_DB = os.path.join(ROOT, 'secureguide.db')
THRESHOLD = 0.70  # confidence <= threshold -> human review (USACM-VAL-009)

VALID_TYPES = {'ART-REQ', 'ART-OBJ', 'ART-PRI', 'ART-POL', 'ART-STD', 'ART-CTR', 'ART-CTE',
               'ART-PRO', 'ART-PRC', 'ART-PRG', 'ART-PLN', 'ART-TSK', 'ART-CFG', 'ART-RUL',
               'ART-EVD', 'ART-MET', 'ART-EXC', 'ART-RSK', 'ART-AST', 'ART-THR', 'ART-VUL', 'ART-OWN'}

ABS_BY_TYPE = {
    'ART-POL': 'ABS-POL', 'ART-STD': 'ABS-POL', 'ART-CFG': 'ABS-TEC', 'ART-RUL': 'ABS-TEC',
    'ART-CTR': 'ABS-CTR', 'ART-CTE': 'ABS-CTR', 'ART-PRC': 'ABS-PRO', 'ART-PRO': 'ABS-PRO',
    'ART-PLN': 'ABS-PRO', 'ART-TSK': 'ABS-PRO', 'ART-REQ': 'ABS-GOV', 'ART-OBJ': 'ABS-GOV',
    'ART-PRI': 'ABS-GOV', 'ART-EVD': 'ABS-EVM', 'ART-MET': 'ABS-EVM', 'ART-RSK': 'ABS-RIS',
    'ART-THR': 'ABS-RIS', 'ART-VUL': 'ABS-RIS', 'ART-AST': 'ABS-TEC', 'ART-EXC': 'ABS-POL',
    'ART-PRG': 'ABS-GOV', 'ART-OWN': 'ABS-GOV',
}

# ordered (regex, type) — first match wins
TYPE_RULES = [
    (r'\b(cve-\d|vulnerabilit|weakness expos)', 'ART-VUL'),
    (r'\b(evidence|audit log|log record|attestation|audit trail|screenshot)\b', 'ART-EVD'),
    (r'\b(metric|kpi|percentage of|ratio of|number of)\b', 'ART-MET'),
    (r'\b(configure|configuration|disable|enable|set the|hardening|baseline|registry|gpo|parameter|must be set)\b', 'ART-CFG'),
    (r'\b(policy|policies)\b', 'ART-POL'),
    (r'\b(standard)\b', 'ART-STD'),
    (r'\b(procedure|runbook|step-by-step|playbook)\b', 'ART-PRC'),
    (r'\b(shall|must|require|ensure|establish and maintain|maintain an)\b', 'ART-REQ'),
]

# keyword -> SDT sub-domain (representative concepts). Order = priority.
DOMAIN_RULES = [
    (r'\b(asset inventor|inventory of (enterprise )?asset)', 'SD-02.01'),
    (r'\b(software inventor|license manage|authorized software)', 'SD-02.02'),
    (r'\b(data classification|data ownership|classify data)', 'SD-02.03'),
    (r'\b(encrypt|cryptograph|data protection|key management)', 'SD-02.04'),
    (r'\b(privacy|retention|data disposal|personal data)', 'SD-02.05'),
    (r'\b(privileged access|admin access|least privilege)', 'SD-03.04'),
    (r'\b(multi-factor|mfa|authenticat|credential|password)', 'SD-03.02'),
    (r'\b(authorization|access control|rbac|permission)', 'SD-03.03'),
    (r'\b(identity lifecycle|provisioning|joiner|mover|leaver|account manage)', 'SD-03.01'),
    (r'\b(remote access|vpn|external access)', 'SD-03.05'),
    (r'\b(firewall|network segment|network security|communications security)', 'SD-04.01'),
    (r'\b(endpoint|server security|malware|anti-virus|patch the endpoint)', 'SD-04.02'),
    (r'\b(harden|secure configuration|configuration standard|baseline config)', 'SD-04.03'),
    (r'\b(cloud|virtual platform|workload protection|container|kubernetes)', 'SD-04.04'),
    (r'\b(email|phishing|web filter|dns)', 'SD-04.05'),
    (r'\b(sdlc|secure development|application security governance)', 'SD-05.01'),
    (r'\b(api security|application testing|dast|sast|penetration test of the app)', 'SD-05.02'),
    (r'\b(software supply chain|dependency|component|open source)', 'SD-05.03'),
    (r'\b(change management|release management|deployment control)', 'SD-05.04'),
    (r'\b(database security|critical application)', 'SD-05.05'),
    (r'\b(logging|log manage|security monitoring|siem)', 'SD-06.01'),
    (r'\b(threat detection|alert|intrusion detect)', 'SD-06.02'),
    (r'\b(vulnerabilit|patch manage|remediat vuln)', 'SD-06.03'),
    (r'\b(security testing|assessment|penetration test|red team)', 'SD-06.04'),
    (r'\b(threat intelligence|indicator of compromise|ioc|ttp)', 'SD-06.05'),
    (r'\b(incident response|incident manage|security incident)', 'SD-07.01'),
    (r'\b(forensic|digital evidence)', 'SD-07.02'),
    (r'\b(backup|restore|recovery point)', 'SD-07.03'),
    (r'\b(business continuit|disaster recovery|bcp|dr plan)', 'SD-07.04'),
    (r'\b(crisis manage|emergency communication)', 'SD-07.05'),
    (r'\b(awareness|security training|security culture)', 'SD-08.01'),
    (r'\b(hr security|employee lifecycle|background check|onboarding)', 'SD-08.02'),
    (r'\b(supplier|third-party|third party|vendor risk|outsourc)', 'SD-08.03'),
    (r'\b(physical security|environmental|data center access)', 'SD-08.04'),
    (r'\b(acceptable use|professional conduct|code of conduct)', 'SD-08.05'),
    (r'\b(strategy|governance|steering committee|ciso)', 'SD-01.01'),
    (r'\b(policy framework|standards and exception|exception process)', 'SD-01.02'),
    (r'\b(risk manage|risk assessment|risk register|risk treatment)', 'SD-01.03'),
    (r'\b(compliance|audit|assurance|regulatory requirement)', 'SD-01.04'),
    (r'\b(program manage|security metric|maturity)', 'SD-01.05'),
]

STOP_TITLE = re.compile(r'^[\d\.\-\s]+$')


def first_sentence(text, max_words=35):
    if not text:
        return None
    text = re.sub(r'\s+', ' ', text).strip()
    m = re.split(r'(?<=[.!?])\s+', text)
    s = m[0] if m else text
    words = s.split()
    if len(words) > max_words:
        s = ' '.join(words[:max_words]).rstrip(',;:') + ' …'
    return s


def clip_words(text, max_words=180):
    if not text:
        return None
    text = re.sub(r'\s+', ' ', text).strip()
    words = text.split()
    return text if len(words) <= max_words else ' '.join(words[:max_words]) + ' …'


def make_title(title_draft, body):
    t = (title_draft or '').strip()
    if t and not STOP_TITLE.match(t) and len(t.split()) >= 2:
        return re.sub(r'\s+', ' ', t)[:120]
    # derive from body: first ~8 words
    fs = first_sentence(body, 12)
    return (fs or t or 'Untitled artifact')[:120]


def classify(raw):
    """Return dict of proposed fields + confidence + rationale + flags."""
    hint_type = raw['usacm_type_assigned']
    hint_dom = raw['sdt_domain_assigned']
    hint_sub = raw['sdt_subdomain_assigned']
    ctx = (raw['context_paragraph'] or '')
    text = ' '.join(filter(None, [raw['title_draft'], raw['description_draft'],
                                  raw['raw_text_en'], ctx])).lower()
    reasons = []
    conf = 0.45

    # ---- type ----
    ptype = None
    if hint_type in VALID_TYPES:
        ptype = hint_type
        conf += 0.20
        reasons.append(f"type {ptype} from source hint")
    else:
        # MITRE tactic/technique context -> threat
        if re.search(r'\btactic:|technique:|att&ck|ta0\d|t1\d{3}\b', text):
            ptype = 'ART-THR'
            reasons.append("type ART-THR from MITRE context")
            conf += 0.10
        else:
            for rx, t in TYPE_RULES:
                if re.search(rx, text):
                    ptype = t
                    reasons.append(f"type {t} from keyword rule")
                    conf += 0.10
                    break
    if ptype is None:
        reasons.append("type unresolved; deferred without a default")

    # ---- domain / sub-domain ----
    psub = None
    if hint_sub and re.match(r'^SD-0[1-8]\.0[1-5]$', hint_sub or ''):
        psub = hint_sub
        conf += 0.20
        reasons.append(f"sub-domain {psub} from source hint")
    else:
        for rx, sd in DOMAIN_RULES:
            if re.search(rx, text):
                psub = sd
                conf += 0.18
                reasons.append(f"sub-domain {sd} from keyword rule")
                break
    # tie-breaker: cloud IAM -> SD-03 (identity focus) not SD-04
    if psub and psub.startswith('SD-04') and re.search(r'\b(identity|iam|authenticat|privileged|credential)\b', text):
        psub = 'SD-03.03'
        reasons.append("tie-breaker: cloud identity -> SD-03")
    pdom = psub[:5] if psub else None
    if hint_dom and hint_dom.startswith('SD-0') and pdom and hint_dom != pdom:
        reasons.append(f"note: source domain hint {hint_dom} differs from {pdom}")

    # ---- ambiguity penalty ----
    if raw['is_ambiguous']:
        conf -= 0.20
        reasons.append("source flagged ambiguous")
    if pdom is None:
        conf -= 0.15
        reasons.append("no confident domain match")

    conf = max(0.05, min(0.99, round(conf, 2)))
    abs_level = ABS_BY_TYPE.get(ptype)
    st = (raw['source_type'] or '').upper()
    obligation = 'OBL-MND' if st in ('FRAMEWORK', 'STANDARD', 'REGULATION') else 'OBL-REC'

    needs_review = 1 if (ptype is None or conf <= THRESHOLD or pdom is None or raw['is_ambiguous']) else 0
    status = 'NEEDS_REVIEW' if needs_review else 'CLASSIFIED'
    return {
        'proposed_type': ptype, 'proposed_abstraction_level': abs_level,
        'proposed_primary_domain': pdom, 'proposed_sub_domain': psub,
        'proposed_obligation_level': obligation, 'confidence': conf,
        'rationale': "First-pass heuristic: " + "; ".join(reasons) + ".",
        'requires_human_review': needs_review, 'curation_status': status,
        'disposition': 'DEFERRED' if ptype is None else None,
    }


def quality_score(title, dshort, dfull, ptype, pdom, psub, rationale):
    q = 0
    q += 20 if title else 0
    q += 20 if dshort else 0
    q += 15 if dfull else 0
    q += 15 if ptype else 0
    q += 20 if (pdom and psub and psub[:5] == pdom) else 0
    q += 10 if rationale else 0
    return min(100, q)


def select_sample(conn, limit, offset):
    """Deterministic round-robin across catalogs. Re-selecting the same
    (limit, offset) yields the same sample; skip-existing makes re-runs no-ops.
    Advance through the backlog with --offset."""
    rows = conn.execute("""
        SELECT id FROM (
          SELECT id, ROW_NUMBER() OVER (PARTITION BY source_catalog_id ORDER BY id) rn, source_catalog_id
          FROM raw_artifacts
        ) ORDER BY rn, source_catalog_id LIMIT ? OFFSET ?""", (limit, offset)).fetchall()
    return [r[0] for r in rows]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', default=DEFAULT_DB)
    ap.add_argument('--limit', type=int, default=30)
    ap.add_argument('--offset', type=int, default=0, help='advance through the backlog')
    ap.add_argument('--force', action='store_true', help='re-stage even if a staging row exists')
    args = ap.parse_args()

    if not os.path.exists(args.db):
        print(f"DB not found: {args.db}. Run ingest_raw.py first.")
        sys.exit(1)
    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")

    ids = select_sample(conn, args.limit, args.offset)
    if not ids:
        print("No raw artifacts in that range (check --limit/--offset or run ingest_raw.py).")
        return

    batch_id = f"BATCH-{args.offset}-{args.offset + len(ids)}"
    conn.execute("INSERT OR IGNORE INTO curation_batches (id, name, status, item_count) VALUES (?,?,?,?)",
                 (batch_id, f"Sample of {len(ids)}", 'PROCESSING', len(ids)))

    processed = skipped = 0
    dist_type, dist_dom, classified, review = {}, {}, 0, 0
    conf_sum = qual_sum = 0
    for rid in ids:
        raw = conn.execute("SELECT * FROM raw_artifacts WHERE id=?", (rid,)).fetchone()
        sid = f"STG-{rid}"
        if not args.force and conn.execute("SELECT 1 FROM staging_artifacts WHERE id=?", (sid,)).fetchone():
            skipped += 1
            continue
        body = raw['description_draft'] or raw['raw_text_en']
        title = make_title(raw['title_draft'], body)
        dshort = first_sentence(raw['description_draft'] or raw['raw_text_en'], 35)
        dfull = clip_words(raw['raw_text_en'] or raw['description_draft'], 180)
        c = classify(raw)
        q = quality_score(title, dshort, dfull, c['proposed_type'],
                          c['proposed_primary_domain'], c['proposed_sub_domain'], c['rationale'])
        conn.execute("""
            INSERT INTO staging_artifacts
              (id, batch_id, raw_artifact_id, title_en, definition_short_en, definition_full_en,
               proposed_type, proposed_abstraction_level, proposed_primary_domain, proposed_sub_domain,
               proposed_obligation_level, classification_confidence, classification_rationale,
               requires_human_review, curation_status, quality_score)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET
               title_en=excluded.title_en, definition_short_en=excluded.definition_short_en,
               definition_full_en=excluded.definition_full_en, proposed_type=excluded.proposed_type,
               proposed_abstraction_level=excluded.proposed_abstraction_level,
               proposed_primary_domain=excluded.proposed_primary_domain,
               proposed_sub_domain=excluded.proposed_sub_domain,
               proposed_obligation_level=excluded.proposed_obligation_level,
               classification_confidence=excluded.classification_confidence,
               classification_rationale=excluded.classification_rationale,
               requires_human_review=excluded.requires_human_review,
               curation_status=excluded.curation_status, quality_score=excluded.quality_score,
               updated_at=datetime('now')""",
            (sid, batch_id, rid, title, dshort, dfull, c['proposed_type'],
             c['proposed_abstraction_level'], c['proposed_primary_domain'], c['proposed_sub_domain'],
             c['proposed_obligation_level'], c['confidence'], c['rationale'],
             c['requires_human_review'], c['curation_status'], q))
        processed += 1
        dist_type[c['proposed_type']] = dist_type.get(c['proposed_type'], 0) + 1
        d = c['proposed_primary_domain'] or '(none)'
        dist_dom[d] = dist_dom.get(d, 0) + 1
        classified += 1 if c['curation_status'] == 'CLASSIFIED' else 0
        review += c['requires_human_review']
        conf_sum += c['confidence']
        qual_sum += q
    conn.execute("UPDATE curation_batches SET status='COMPLETED', completed_at=datetime('now') WHERE id=?", (batch_id,))
    conn.commit()

    n = max(processed, 1)
    print("=" * 60)
    print(f"BATCH SAMPLE  (batch {batch_id})")
    print("=" * 60)
    print(f"processed / skipped(existing) : {processed} / {skipped}")
    print(f"CLASSIFIED / NEEDS_REVIEW      : {classified} / {review}")
    print(f"avg confidence / avg quality   : {conf_sum/n:.2f} / {qual_sum/n:.0f}")
    print(f"type distribution   : {dict(sorted(dist_type.items()))}")
    print(f"domain distribution : {dict(sorted(dist_dom.items()))}")
    print("-" * 60)
    print("sample rows (first 8):")
    for r in conn.execute("""SELECT title_en, proposed_type, proposed_sub_domain,
                                    classification_confidence AS conf, quality_score AS q, curation_status
                             FROM staging_artifacts WHERE batch_id=? ORDER BY conf DESC LIMIT 8""", (batch_id,)):
        title = (r['title_en'] or '')[:38]
        print(f"  {title:38} {r['proposed_type'] or '-':8} {str(r['proposed_sub_domain'] or '-'):9} "
              f"c={r['conf']:.2f} q={r['q']:>3} {r['curation_status']}")
    print("-" * 60)
    print("Review queue now populated. Inspect with:  SELECT * FROM v_review_queue;")
    print("security_artifacts remains untouched (promotion is a separate, later step).")


if __name__ == '__main__':
    main()
