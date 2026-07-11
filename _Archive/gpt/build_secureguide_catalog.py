#!/usr/bin/env python3
"""Build the SecureGuide raw catalog from official, locally downloaded sources."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import openpyxl


ROOT = Path(__file__).resolve().parent
COLLECTION_DATE = "2026-07-10"

SOURCES = {
    "csf": Path("/tmp/CSF_2_0.xlsx"),
    "nist53": Path("/tmp/NIST_SP-800-53_rev5_catalog.json"),
    "asvs": Path("/tmp/OWASP_ASVS_5.0.0_en.csv"),
    "nca": Path("/tmp/ECC_2_2024_EN_raw.txt"),
    "mitre": Path("/tmp/enterprise-attack.json"),
}

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "before", "by", "can",
    "for", "from", "has", "have", "if", "in", "include", "including", "into", "is",
    "it", "its", "may", "must", "not", "of", "on", "only", "or", "other", "shall",
    "should", "such", "that", "the", "their", "there", "these", "this", "to", "use",
    "used", "using", "when", "where", "which", "with", "within", "without", "verify",
    "organization", "organizational", "entity", "system", "systems", "security",
    "cybersecurity", "information", "control", "controls", "application", "applications",
}

ENTITY_LEXICONS = {
    "technologies": {
        "Active Directory": r"\bactive directory\b",
        "API": r"\bapi(?:s)?\b",
        "Cloud": r"\bcloud\b",
        "Container": r"\bcontainers?\b",
        "Cryptography": r"\bcryptograph(?:y|ic)\b|\bencrypt(?:ion|ed)?\b",
        "Database": r"\bdatabases?\b",
        "DNS": r"\bdns\b|domain name system",
        "Firewall": r"\bfirewalls?\b",
        "HTTP": r"\bhttps?\b",
        "JavaScript": r"\bjavascript\b",
        "Kerberos": r"\bkerberos\b",
        "Kubernetes": r"\bkubernetes\b",
        "Linux": r"\blinux\b",
        "macOS": r"\bmacos\b|\bmac os\b",
        "PowerShell": r"\bpowershell\b",
        "SSH": r"\bssh\b|secure shell",
        "TLS": r"\btls\b|transport layer security",
        "VPN": r"\bvpn\b|virtual private network",
        "Windows": r"\bwindows\b",
        "XML": r"\bxml\b",
    },
    "roles": {
        "Administrator": r"\badministrators?\b",
        "Adversary": r"\badversar(?:y|ies)\b|\battackers?\b",
        "Auditor": r"\bauditors?\b|\baudit personnel\b",
        "Authorized Official": r"\bauthorized official\b",
        "Developer": r"\bdevelopers?\b",
        "Personnel": r"\bpersonnel\b|\bemployees?\b",
        "Supplier": r"\bsuppliers?\b|\bvendors?\b|\bthird part(?:y|ies)\b",
        "System Owner": r"\bsystem owners?\b",
        "User": r"\busers?\b",
    },
    "systems": {
        "Application": r"\bapplications?\b",
        "Cloud Environment": r"\bcloud environments?\b|\bcloud services?\b",
        "Database": r"\bdatabases?\b",
        "Endpoint": r"\bendpoints?\b|\bworkstations?\b",
        "Information System": r"\binformation systems?\b",
        "Mobile Device": r"\bmobile devices?\b",
        "Network": r"\bnetworks?\b",
        "Operating System": r"\boperating systems?\b",
        "Server": r"\bservers?\b",
    },
    "threats": {
        "Brute Force": r"\bbrute force\b",
        "Credential Theft": r"\bcredential (?:theft|dumping|stealing)\b",
        "Data Breach": r"\bdata breaches?\b",
        "Denial of Service": r"\bdenial[- ]of[- ]service\b|\bdos attacks?\b",
        "Exfiltration": r"\bexfiltrat(?:e|ion|ing)\b",
        "Injection": r"\binjection attacks?\b|\bsql injection\b",
        "Malware": r"\bmalware\b|\bmalicious code\b",
        "Phishing": r"\bphishing\b",
        "Ransomware": r"\bransomware\b",
        "Unauthorized Access": r"\bunauthorized access\b",
    },
    "assets": {
        "Account": r"\baccounts?\b",
        "Configuration": r"\bconfigurations?\b",
        "Credentials": r"\bcredentials?\b|\bpasswords?\b",
        "Cryptographic Key": r"\bcryptographic keys?\b|\bencryption keys?\b",
        "Data": r"\bdata\b",
        "Hardware": r"\bhardware\b",
        "Logs": r"\blogs?\b|\baudit records?\b",
        "Personal Data": r"\bpersonal data\b|personally identifiable information|\bpii\b",
        "Secrets": r"\bsecrets?\b",
        "Software": r"\bsoftware\b",
        "Source Code": r"\bsource code\b",
    },
}


def normalize_space(text: str | None) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def keywords(text: str, limit: int = 8) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", text.lower())
    counts = Counter(w for w in words if w not in STOPWORDS and not w.isdigit())
    first_pos = {word: words.index(word) for word in counts}
    return [word for word, _ in sorted(counts.items(), key=lambda x: (-x[1], first_pos[x[0]], x[0]))[:limit]]


def extract_entities(text: str) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for group, lexicon in ENTITY_LEXICONS.items():
        result[group] = [label for label, pattern in lexicon.items() if re.search(pattern, text, re.I)]
    return result


def first_sentence(text: str, limit: int = 420) -> str:
    clean = normalize_space(text)
    if not clean:
        return ""
    match = re.search(r"(?<=[.!?])\s+", clean)
    candidate = clean[: match.start() + 1] if match else clean
    return candidate if len(candidate) <= limit else candidate[: limit - 1].rstrip() + "â€¦"


def raw_artifact(
    *, source_document: str, source_type: str, source_version: str,
    source_section: str, source_url: str, issuing_authority: str,
    publication_date: str, language: str, raw_text_en: str | None,
    raw_text_ar: str | None, original_heading: str | None,
    context_paragraph: str | None, title_draft: str,
    description_draft: str | None = None, notes: str,
    confidence: float, priority: str = "HIGH", review: bool = False,
    ambiguous: bool = False, ambiguity_reason: str | None = None,
    extra_entities: dict[str, list[str]] | None = None,
) -> dict:
    text_for_extraction = " ".join(x for x in [original_heading, raw_text_en, raw_text_ar, context_paragraph] if x)
    entities = extract_entities(text_for_extraction)
    if extra_entities:
        for key, values in extra_entities.items():
            entities[key] = list(dict.fromkeys(entities.get(key, []) + [v for v in values if v]))
    complete = bool(source_document and source_section and source_url and issuing_authority and (raw_text_en or raw_text_ar))
    return {
        "raw_artifact_id": None,
        "source_metadata": {
            "source_document": source_document,
            "source_type": source_type,
            "source_version": source_version,
            "source_section": source_section,
            "source_url": source_url,
            "issuing_authority": issuing_authority,
            "publication_date": publication_date,
            "language": language,
        },
        "original_content": {
            "raw_text_en": raw_text_en,
            "raw_text_ar": raw_text_ar,
            "original_heading": original_heading,
            "context_paragraph": context_paragraph,
        },
        "extracted_elements": {
            "title_draft": title_draft,
            "description_draft": description_draft if description_draft is not None else first_sentence(raw_text_en or raw_text_ar or ""),
            "keywords": keywords(text_for_extraction),
            "entities_mentioned": entities,
        },
        "collection_metadata": {
            "collection_date": COLLECTION_DATE,
            "collection_method": "AI_EXTRACTION",
            "collector": "SecureGuide Extraction Engine v1.0",
            "confidence_in_extraction": confidence,
            "extraction_notes": notes,
        },
        "classification_status": {
            "usacm_type_assigned": None,
            "sdt_domain_assigned": None,
            "sdt_subdomain_assigned": None,
            "requires_classification": True,
            "classification_priority": priority,
            "duplicate_candidates": [],
        },
        "quality_flags": {
            "is_complete": complete,
            "has_source_trace": bool(source_url and source_section),
            "needs_human_review": review or not complete,
            "is_ambiguous": ambiguous,
            "ambiguity_reason": ambiguity_reason,
        },
    }


def extract_csf() -> list[dict]:
    workbook = openpyxl.load_workbook(SOURCES["csf"], read_only=True, data_only=True)
    sheet = workbook["CSF 2.0"]
    function = None
    category = None
    out = []
    for row in sheet.iter_rows(min_row=3, values_only=True):
        if row[0]:
            function = str(row[0]).strip()
        if row[1]:
            category = str(row[1]).strip()
        if not row[2]:
            continue
        cell = str(row[2]).strip()
        match = re.match(r"([A-Z]{2}\.[A-Z]{2}-\d+):\s*(.*)", cell, re.S)
        if not match or "[Withdrawn:" in cell:
            continue
        sid, outcome = match.groups()
        context = "\n".join(x for x in [function, category] if x)
        out.append(raw_artifact(
            source_document="The NIST Cybersecurity Framework (CSF) 2.0",
            source_type="FRAMEWORK", source_version="2.0", source_section=f"Subcategory {sid}",
            source_url="https://csrc.nist.gov/extensions/nudp/services/json/csf/download?olirids=",
            issuing_authority="National Institute of Standards and Technology (NIST)",
            publication_date="2024-02-26", language="EN", raw_text_en=outcome,
            raw_text_ar=None, original_heading=cell, context_paragraph=context,
            title_draft=f"{sid} â€” {outcome}", notes="Extracted from the official CSF 2.0 Reference Tool XLSX export; active subcategory only.",
            confidence=0.99,
        ))
    return out


def prop_value(item: dict, name: str, *, prefer_unclassed: bool = False) -> str | None:
    props = [p for p in item.get("props", []) if p.get("name") == name]
    if prefer_unclassed:
        for prop in props:
            if "class" not in prop:
                return prop.get("value")
    return props[0].get("value") if props else None


def render_part(part: dict, include_root_label: bool = False) -> str:
    lines = []
    label = prop_value(part, "label", prefer_unclassed=True)
    prose = part.get("prose")
    if prose:
        prefix = f"{label} " if label and include_root_label else ""
        lines.append(prefix + prose.strip())
    for child in part.get("parts", []):
        rendered = render_part(child, include_root_label=True)
        if rendered:
            lines.append(rendered)
    return "\n".join(lines)


def extract_nist53() -> list[dict]:
    catalog = json.loads(SOURCES["nist53"].read_text(encoding="utf-8"))["catalog"]
    out = []

    def walk(node: dict, family: str | None = None) -> None:
        for control in node.get("controls", []):
            label = prop_value(control, "label", prefer_unclassed=True) or control["id"].upper()
            status = prop_value(control, "status")
            statement_parts = [p for p in control.get("parts", []) if p.get("name") == "statement"]
            guidance_parts = [p for p in control.get("parts", []) if p.get("name") == "guidance"]
            statement = "\n".join(filter(None, (render_part(p) for p in statement_parts)))
            guidance = "\n".join(filter(None, (render_part(p) for p in guidance_parts)))
            heading = f"{label}: {control['title']}"
            raw_text = statement or heading
            status_note = f" Source status: {status}." if status else ""
            out.append(raw_artifact(
                source_document="NIST SP 800-53 Rev. 5 â€” Security and Privacy Controls for Information Systems and Organizations",
                source_type="STANDARD", source_version="Release 5.2.0", source_section=f"Control {label} ({family or 'Unspecified family'})",
                source_url="https://github.com/usnistgov/oscal-content/blob/main/nist.gov/SP800-53/rev5/json/NIST_SP-800-53_rev5_catalog.json",
                issuing_authority="National Institute of Standards and Technology (NIST)", publication_date="2025-08-26",
                language="EN", raw_text_en=raw_text, raw_text_ar=None, original_heading=heading,
                context_paragraph=guidance or (f"Control family: {family}" if family else None),
                title_draft=heading, notes="Extracted from the official NIST OSCAL catalog. Organization-defined parameters remain in native OSCAL insert notation." + status_note,
                confidence=0.99, review=status == "withdrawn",
            ))
            walk(control, family)
        for group in node.get("groups", []):
            walk(group, group.get("title") or family)

    walk(catalog)
    return out


def extract_asvs() -> list[dict]:
    out = []
    with SOURCES["asvs"].open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            rid = row["req_id"].strip()
            text = row["req_description"].strip()
            section = f"{row['section_id'].strip()} {row['section_name'].strip()}"
            chapter = f"{row['chapter_id'].strip()} {row['chapter_name'].strip()}"
            out.append(raw_artifact(
                source_document="OWASP Application Security Verification Standard 5.0.0",
                source_type="GUIDELINE", source_version="5.0.0", source_section=f"Requirement {rid} ({section})",
                source_url="https://raw.githubusercontent.com/OWASP/ASVS/v5.0.0/5.0/docs_en/OWASP_Application_Security_Verification_Standard_5.0.0_en.csv",
                issuing_authority="OWASP Foundation", publication_date="2025-05-30", language="EN",
                raw_text_en=text, raw_text_ar=None, original_heading=f"{rid}: {section}", context_paragraph=chapter,
                title_draft=f"{rid} â€” {row['section_name'].strip()}",
                notes=f"Extracted verbatim from the official ASVS 5.0.0 English CSV. Verification level: L{row['L'].strip()}.",
                confidence=0.99,
            ))
    return out


def clean_nca_line(line: str) -> str | None:
    text = line.replace("\f", "").strip()
    if not text or re.search(r"[\u0600-\u06ff]", text):
        return None
    if re.fullmatch(r"\d+", text):
        return None
    if text in {"-", "Controls", "Objective"}:
        return None
    if "Document classification:" in text or "TLP: White" in text:
        return None
    if text == "Essential Cybersecurity Controls":
        return None
    return text


def extract_nca() -> list[dict]:
    lines = SOURCES["nca"].read_text(encoding="utf-8").splitlines()
    appendix_start = next(i for i, line in enumerate(lines) if i > 1200 and line.strip().startswith("Appendix (A)"))
    control_markers = []
    seen = set()
    for i, line in enumerate(lines[:appendix_start]):
        match = re.match(r"^\s*(\d+-\d+-\d+)(?:\s+(.*))?$", line)
        if match and match.group(1) not in seen:
            seen.add(match.group(1))
            control_markers.append((i, match.group(1), (match.group(2) or "").strip()))

    subdomains = []
    for i, line in enumerate(lines[:appendix_start]):
        match = re.match(r"^\s*(\d+[-.]\d+)\s+(.+?)\s*$", line)
        if match and not re.fullmatch(r"\d+[.-]\d+[.-]\d+", match.group(1)):
            subdomains.append((i, match.group(1).replace(".", "-"), match.group(2).strip()))

    out = []
    for pos, (start, cid, same_line) in enumerate(control_markers):
        prefix = "-".join(cid.split("-")[:2])
        prior_subdomains = [s for s in subdomains if s[0] < start and s[1] == prefix]
        sub_start, _, sub_name = prior_subdomains[-1] if prior_subdomains else (start, prefix, "")
        next_control = control_markers[pos + 1][0] if pos + 1 < len(control_markers) else appendix_start
        next_subdomain = min((s[0] for s in subdomains if start < s[0] < next_control), default=next_control)
        end = min(next_control, next_subdomain, appendix_start)
        content_lines = []
        if same_line:
            content_lines.append(same_line)
        content_lines.extend(x for x in (clean_nca_line(line) for line in lines[start + 1:end]) if x)
        raw_text = normalize_space(" ".join(content_lines))

        objective = None
        segment = lines[sub_start:start]
        try:
            obj_index = next(i for i, line in enumerate(segment) if line.strip().startswith("Objective"))
            ctl_index = next(i for i, line in enumerate(segment[obj_index + 1:], obj_index + 1) if line.strip() == "Controls")
            objective_lines = []
            first = segment[obj_index].strip()[len("Objective"):].strip()
            if first:
                objective_lines.append(first)
            objective_lines.extend(x for x in (clean_nca_line(line) for line in segment[obj_index + 1:ctl_index]) if x)
            objective = normalize_space(" ".join(objective_lines)) or None
        except StopIteration:
            objective = None

        heading = f"{cid}: {sub_name}" if sub_name else cid
        out.append(raw_artifact(
            source_document="Essential Cybersecurity Controls (ECC 2-2024)", source_type="STANDARD",
            source_version="ECC 2-2024", source_section=f"Control {cid} ({sub_name or prefix})",
            source_url="https://cdn.nca.gov.sa/api/files/public/upload/86e09090-44e4-481f-bc28-355673607654_ECC--2024-EN.pdf",
            issuing_authority="National Cybersecurity Authority (Saudi Arabia)", publication_date="2024-09-19",
            language="EN", raw_text_en=raw_text, raw_text_ar=None, original_heading=heading,
            context_paragraph=objective, title_draft=heading,
            notes="Extracted from the official English ECC 2-2024 PDF text layer. Line breaks were normalized; source wording was not paraphrased.",
            confidence=0.91, review=True,
        ))
    return out


def extract_mitre() -> list[dict]:
    bundle = json.loads(SOURCES["mitre"].read_text(encoding="utf-8"))
    out = []
    for item in bundle["objects"]:
        if item.get("type") != "attack-pattern":
            continue
        ref = next((r for r in item.get("external_references", []) if r.get("source_name") == "mitre-attack" and r.get("external_id")), None)
        external_id = ref["external_id"] if ref else item["id"]
        source_url = (ref or {}).get("url") or "https://attack.mitre.org/"
        platforms = item.get("x_mitre_platforms", [])
        tactics = [p.get("phase_name", "").replace("-", " ").title() for p in item.get("kill_chain_phases", []) if p.get("phase_name")]
        context_parts = []
        if tactics:
            context_parts.append("Tactics: " + ", ".join(tactics))
        if platforms:
            context_parts.append("Platforms: " + ", ".join(platforms))
        flags = [name for name, active in (("revoked", item.get("revoked")), ("deprecated", item.get("x_mitre_deprecated"))) if active]
        extra = {
            "technologies": platforms,
            "systems": platforms,
            "threats": [item["name"]],
        }
        out.append(raw_artifact(
            source_document="MITRE ATT&CK Enterprise", source_type="THREAT_INTEL", source_version="19.1",
            source_section=f"Technique {external_id}", source_url=source_url,
            issuing_authority="The MITRE Corporation", publication_date="2026-05-12", language="EN",
            raw_text_en=item["description"], raw_text_ar=None, original_heading=f"{external_id}: {item['name']}",
            context_paragraph="\n".join(context_parts) or None, title_draft=f"{external_id} â€” {item['name']}",
            notes="Extracted from the official MITRE ATT&CK STIX 2.1 Enterprise bundle." + (" Source flags: " + ", ".join(flags) + "." if flags else ""),
            confidence=0.99, priority="MEDIUM", review=bool(flags), extra_entities=extra,
        ))
    return out


def assign_ids_and_candidates(artifacts: list[dict]) -> None:
    for index, artifact in enumerate(artifacts, 1):
        artifact["raw_artifact_id"] = f"RAW-{index:06d}"

    by_title: dict[str, list[str]] = defaultdict(list)
    for artifact in artifacts:
        title = artifact["original_content"]["original_heading"] or artifact["extracted_elements"]["title_draft"]
        normalized = re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()
        if normalized:
            by_title[normalized].append(artifact["raw_artifact_id"])
    for artifact in artifacts:
        title = artifact["original_content"]["original_heading"] or artifact["extracted_elements"]["title_draft"]
        normalized = re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()
        artifact["classification_status"]["duplicate_candidates"] = [
            rid for rid in by_title.get(normalized, []) if rid != artifact["raw_artifact_id"]
        ]


def statistics(items: list[dict]) -> dict:
    return {
        "by_source": dict(Counter(a["source_metadata"]["source_document"] for a in items)),
        "by_source_type": dict(Counter(a["source_metadata"]["source_type"] for a in items)),
        "by_language": dict(Counter(a["source_metadata"]["language"] for a in items)),
    }


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_artifacts(artifacts: list[dict]) -> dict:
    ids = [a["raw_artifact_id"] for a in artifacts]
    source_locators = [
        (a["source_metadata"]["source_document"], a["source_metadata"]["source_section"])
        for a in artifacts
    ]
    required_top = {"raw_artifact_id", "source_metadata", "original_content", "extracted_elements", "collection_metadata", "classification_status", "quality_flags"}
    schema_ok = all(set(a) == required_top for a in artifacts)
    no_classification = all(
        a["classification_status"][key] is None
        for a in artifacts
        for key in ("usacm_type_assigned", "sdt_domain_assigned", "sdt_subdomain_assigned")
    )
    return {
        "total_artifacts": len(artifacts),
        "unique_ids": len(set(ids)),
        "unique_source_locators": len(set(source_locators)),
        "duplicate_source_locators": len(source_locators) - len(set(source_locators)),
        "ids_are_sequential": ids == [f"RAW-{i:06d}" for i in range(1, len(ids) + 1)],
        "exact_top_level_schema": schema_ok,
        "no_usacm_or_sdt_assignments": no_classification,
        "complete_records": sum(a["quality_flags"]["is_complete"] for a in artifacts),
        "source_traced_records": sum(a["quality_flags"]["has_source_trace"] for a in artifacts),
        "human_review_records": sum(a["quality_flags"]["needs_human_review"] for a in artifacts),
        "ambiguous_records": sum(a["quality_flags"]["is_ambiguous"] for a in artifacts),
        "records_with_extracted_elements": sum(
            bool(a["extracted_elements"]["title_draft"] and a["extracted_elements"]["description_draft"] and a["extracted_elements"]["keywords"])
            for a in artifacts
        ),
        "source_counts": statistics(artifacts)["by_source"],
    }


def main() -> None:
    for name, path in SOURCES.items():
        if not path.exists():
            raise SystemExit(f"Missing source {name}: {path}")

    groups = {
        "NIST CSF 2.0": extract_csf(),
        "NIST SP 800-53 Rev.5 Release 5.2.0": extract_nist53(),
        "OWASP ASVS 5.0.0": extract_asvs(),
        "NCA ECC 2-2024": extract_nca(),
        "MITRE ATT&CK Enterprise 19.1": extract_mitre(),
    }
    expected = {
        "NIST CSF 2.0": 106,
        "NIST SP 800-53 Rev.5 Release 5.2.0": 1196,
        "OWASP ASVS 5.0.0": 345,
        "NCA ECC 2-2024": 108,
        "MITRE ATT&CK Enterprise 19.1": 858,
    }
    actual = {name: len(items) for name, items in groups.items()}
    if actual != expected:
        raise SystemExit(f"Source count mismatch: expected={expected} actual={actual}")

    artifacts = [item for items in groups.values() for item in items]
    assign_ids_and_candidates(artifacts)
    if len(artifacts) != 2613:
        raise SystemExit(f"Expected 2613 artifacts, got {len(artifacts)}")

    phase_slices = [(0, 500), (500, 1000), (1000, 1500), (1500, len(artifacts))]
    output_paths = []
    for phase_number, (start, end) in enumerate(phase_slices, 1):
        items = artifacts[start:end]
        covered = list(dict.fromkeys(a["source_metadata"]["source_document"] for a in items))
        next_sources = [] if phase_number == 4 else list(dict.fromkeys(a["source_metadata"]["source_document"] for a in artifacts[end:]))
        payload = {
            "extraction_metadata": {
                "extraction_date": COLLECTION_DATE,
                "extraction_engine": "SecureGuide Raw Extraction Engine v1.0",
                "phase": phase_number,
                "total_artifacts": len(items),
                "sources_covered": covered,
                "next_phase_sources": next_sources,
            },
            "artifacts": items,
            "statistics": statistics(items),
        }
        path = ROOT / f"secureguide_raw_catalog_phase_{phase_number}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        output_paths.append(path)

    validation = validate_artifacts(artifacts)
    validation["phase_files"] = [
        {"file": path.name, "bytes": path.stat().st_size, "sha256": sha256(path)} for path in output_paths
    ]
    validation["source_files"] = {
        name: {"path": str(path), "bytes": path.stat().st_size, "sha256": sha256(path)}
        for name, path in SOURCES.items()
    }
    validation_path = ROOT / "secureguide_raw_catalog_validation_report.json"
    validation_path.write_text(json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    coverage = {
        "report_date": COLLECTION_DATE,
        "delivered_artifacts": len(artifacts),
        "fully_or_partially_covered_sources": 5,
        "requested_sources": 15,
        "coverage": [
            {"source": "NIST Cybersecurity Framework (CSF) 2.0", "status": "EXTRACTED", "version_used": "2.0", "artifacts": 106, "note": "All 106 active subcategories extracted; 79 withdrawn compatibility rows in the export were not treated as current CSF 2.0 subcategories."},
            {"source": "ISO/IEC 27002:2022", "status": "BLOCKED_BY_COPYRIGHT", "version_used": None, "artifacts": 0, "note": "ISO states that reproduction requires written permission. A licensed copy and redistribution authorization are required for verbatim bulk extraction."},
            {"source": "CIS Controls v8.1", "status": "ACCESS_AND_LICENSE_REVIEW_REQUIRED", "version_used": "8.1", "artifacts": 0, "note": "Official bulk download is form-gated. Verbatim redistribution rights were not established in this run."},
            {"source": "PCI DSS", "status": "LICENSE_REVIEW_REQUIRED", "version_used": "4.0.1", "artifacts": 0, "note": "The current official version is 4.0.1. The standard is publicly downloadable but copyrighted; bulk republication rights were not established."},
            {"source": "NIST SP 800-53 Rev.5", "status": "EXTRACTED", "version_used": "Release 5.2.0", "artifacts": 1196, "note": "All control and control-enhancement records in the official OSCAL catalog were retained, including withdrawn records."},
            {"source": "NCA ECC", "status": "EXTRACTED_UPDATED_VERSION", "version_used": "ECC 2-2024", "artifacts": 108, "note": "The current ECC 2-2024 replaced the requested ECC-1:2018 source."},
            {"source": "MITRE ATT&CK", "status": "EXTRACTED_UPDATED_VERSION", "version_used": "Enterprise 19.1", "artifacts": 858, "note": "All attack-pattern records were retained, including revoked and deprecated records; requested v14 is obsolete."},
            {"source": "OWASP Top 10 + ASVS", "status": "PARTIALLY_EXTRACTED", "version_used": "ASVS 5.0.0", "artifacts": 345, "note": "All ASVS 5.0.0 requirements were extracted. OWASP Top 10 was not separately ingested in this run."},
            {"source": "COBIT 2019", "status": "PROPRIETARY_SOURCE_REQUIRED", "version_used": None, "artifacts": 0, "note": "A licensed ISACA source and redistribution authorization are required for verbatim bulk extraction."},
            {"source": "ITIL 4", "status": "PROPRIETARY_SOURCE_REQUIRED", "version_used": None, "artifacts": 0, "note": "A licensed official source and redistribution authorization are required for verbatim bulk extraction."},
            {"source": "CIS Benchmarks", "status": "ACCESS_AND_LICENSE_REVIEW_REQUIRED", "version_used": None, "artifacts": 0, "note": "Benchmark downloads and reuse are governed by CIS access and license terms."},
            {"source": "Microsoft Security Baselines", "status": "NOT_INGESTED", "version_used": None, "artifacts": 0, "note": "Requires a dedicated parser for the current Security Compliance Toolkit packages."},
            {"source": "NIST SP 800-171", "status": "REQUESTED_VERSION_SUPERSEDED", "version_used": "Rev.3 identified", "artifacts": 0, "note": "Rev.3 superseded the requested Rev.2 in May 2024. It should be ingested as a separate current-source batch."},
            {"source": "GDPR", "status": "NOT_INGESTED", "version_used": None, "artifacts": 0, "note": "Requires a dedicated EUR-Lex article/paragraph parser and legal consolidation-date capture."},
            {"source": "HIPAA Security Rule", "status": "NOT_INGESTED", "version_used": None, "artifacts": 0, "note": "Requires a dedicated eCFR subsection parser and effective-date capture."},
        ],
        "success_criteria": {
            "minimum_2000_artifacts": True,
            "all_15_sources_covered": False,
            "all_records_source_traced": validation["source_traced_records"] == len(artifacts),
            "all_records_complete": validation["complete_records"] == len(artifacts),
            "no_usacm_or_sdt_classification": validation["no_usacm_or_sdt_assignments"],
        },
    }
    coverage_path = ROOT / "secureguide_source_coverage_report.json"
    coverage_path.write_text(json.dumps(coverage, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()