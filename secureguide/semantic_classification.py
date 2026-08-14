"""Deterministic semantic classification for recovered catalog records.

The classifier deliberately ignores legacy proposed type, abstraction, and
domain fields.  Those fields were populated from a source-family default and
are retained only as historical evidence in the recovered raw document.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from collections.abc import Iterable
from typing import Any


CLASSIFIER_VERSION = "secureguide-semantic-rules-1.2.0"

MARKDOWN_LINK = re.compile(r"\[([^\]]+)\]\((https?://[^)]+)\)", re.IGNORECASE)
CITATION = re.compile(r"\s*\(Citation:[^)]+\)", re.IGNORECASE)
HTML_TAG = re.compile(r"</?[^>]+>")

TYPE_LEVEL = {
    "ART-REQ": "ABS-GOV", "ART-OBJ": "ABS-GOV", "ART-PRI": "ABS-GOV",
    "ART-POL": "ABS-POL", "ART-STD": "ABS-POL", "ART-CTR": "ABS-CTR",
    "ART-CTE": "ABS-CTR", "ART-PRO": "ABS-PRO", "ART-PRC": "ABS-PRO",
    "ART-PRG": "ABS-PRO", "ART-PLN": "ABS-PRO", "ART-TSK": "ABS-PRO",
    "ART-CFG": "ABS-TEC", "ART-RUL": "ABS-TEC", "ART-EVD": "ABS-EVM",
    "ART-MET": "ABS-EVM", "ART-EXC": "ABS-RIS", "ART-RSK": "ABS-RIS",
    "ART-AST": "ABS-RIS", "ART-THR": "ABS-RIS", "ART-VUL": "ABS-RIS",
    "ART-OWN": "ABS-GOV",
}

STOP_WORDS = frozenset(
    "a an and are as at be by for from in is it its may must of on only or shall "
    "that the their this to with within".split()
)

# Ordered only for deterministic tie-breaking.  Selection uses a semantic score;
# it is not inferred from source family or from the chosen artifact type.
SUBDOMAIN_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("SD-01.01", ("cybersecurity strategy", "security governance", "organizational leadership", "governance structure", "roles and responsibilities")),
    ("SD-01.02", ("security policy", "cybersecurity policy", "security standard", "exception", "waiver")),
    ("SD-01.03", ("risk assessment", "risk management", "risk appetite", "risk register", "risk treatment")),
    ("SD-01.04", ("compliance", "regulatory", "audit", "assurance", "independent review")),
    ("SD-01.05", ("security program", "cybersecurity program", "metric", "kpi", "performance measure")),
    ("SD-02.01", ("asset inventory", "enterprise asset", "hardware inventory", "asset owner", "asset lifecycle")),
    ("SD-02.02", ("software inventory", "software license", "unsupported software", "software lifecycle")),
    ("SD-02.03", ("data classification", "information classification", "data owner", "data inventory")),
    ("SD-02.04", ("encryption", "cryptographic", "data at rest", "data in transit", "data in use", "key management")),
    ("SD-02.05", ("privacy", "personal data", "data retention", "data disposal", "data deletion")),
    ("SD-03.01", ("identity lifecycle", "user account lifecycle", "provisioning", "deprovisioning", "account termination")),
    ("SD-03.02", ("authentication", "password", "passphrase", "credential", "mfa", "multi factor", "passkey", "login", "session cookie")),
    ("SD-03.03", ("authorization", "access control", "permissions", "least privilege", "logical access", "account access")),
    ("SD-03.04", ("privileged access", "administrator account", "admin account", "pam", "elevated privilege", "root account")),
    ("SD-03.05", ("remote access", "external access", "vpn", "remote desktop", "third party access")),
    ("SD-04.01", ("network security", "network traffic", "firewall", "wireless", "wi fi", "wifi", "router", "dns", "network segmentation")),
    ("SD-04.02", ("endpoint", "server", "operating system", "workstation", "mobile device", "device hardening", "anti malware", "malware protection")),
    ("SD-04.03", ("secure configuration", "configuration baseline", "hardening", "default setting", "security setting", "configuration management")),
    ("SD-04.04", ("cloud", "virtual machine", "container", "kubernetes", "virtualization", "cloud workload")),
    ("SD-04.05", ("email", "browser", "web filtering", "messaging", "social media", "digital communication")),
    ("SD-05.01", ("secure development", "sdlc", "application security requirement", "software development", "application governance")),
    ("SD-05.02", ("application security testing", "api security testing", "sast", "dast", "code review", "verify that")),
    ("SD-05.03", ("software supply chain", "third party component", "dependency", "source code", "package integrity")),
    ("SD-05.04", ("change management", "release management", "change approval", "production change")),
    ("SD-05.05", ("database security", "critical application", "database access", "database activity")),
    ("SD-06.01", ("audit log", "logging", "security monitoring", "log collection", "log management")),
    ("SD-06.02", ("threat detection", "security alert", "anomaly detection", "intrusion detection", "detect malicious")),
    ("SD-06.03", ("vulnerability", "security patch", "patch management", "vulnerability scan", "remediation")),
    ("SD-06.04", ("penetration test", "red team", "security assessment", "security test", "maturity assessment")),
    ("SD-06.05", ("threat intelligence", "indicator of compromise", "ioc", "threat feed", "threat hunting")),
    ("SD-07.01", ("security incident", "incident response", "incident management", "containment", "eradication")),
    ("SD-07.02", ("digital forensic", "forensic evidence", "chain of custody", "evidence preservation")),
    ("SD-07.03", ("backup", "restore", "recovery copy", "backup integrity")),
    ("SD-07.04", ("business continuity", "disaster recovery", "resilience", "availability plan", "recovery objective")),
    ("SD-07.05", ("crisis management", "crisis communication", "public communication", "stakeholder communication")),
    ("SD-08.01", ("security awareness", "cybersecurity awareness", "security training", "phishing awareness", "security culture")),
    ("SD-08.02", ("human resources", "employee lifecycle", "background check", "personnel security", "staff termination")),
    ("SD-08.03", ("supplier", "third party", "vendor", "outsourcing", "supply relationship")),
    ("SD-08.04", ("physical security", "physical access", "environmental", "secure area", "visitor", "document security")),
    ("SD-08.05", ("acceptable use", "professional conduct", "user behavior", "personal device use")),
)

SECTION_FALLBACKS = {
    "credentials_passwords": "SD-03.02", "authentication_access": "SD-03.02",
    "account_recovery_sessions": "SD-03.02", "device_access_data": "SD-03.03",
    "device_hardening_updates": "SD-04.02", "software_malware_protection": "SD-04.02",
    "application_permissions_integrity": "SD-05.03", "email_security": "SD-04.05",
    "browser_security_privacy": "SD-04.05", "wifi_router_security": "SD-04.01",
    "secure_connectivity": "SD-03.05", "data_protection_privacy": "SD-02.05",
    "backup_cloud_recovery": "SD-07.03", "physical_device_document_security": "SD-08.04",
    "phishing_social_engineering": "SD-08.01", "financial_accounts_payments": "SD-03.02",
    "financial_fraud_identity": "SD-03.02", "travel_public_spaces": "SD-08.04",
    "iot_device_network_security": "SD-04.01", "smart_home_privacy_access": "SD-02.05",
    "security_habits_verification": "SD-08.05", "incident_preparedness_detection": "SD-07.01",
    "incident_response_containment": "SD-07.01", "evidence_recovery_review": "SD-07.02",
    "messaging_sharing": "SD-04.05",
}

PREFIX_FALLBACKS = {
    "GRC-GOV": "SD-01.01", "GRC-POLICY": "SD-01.02", "GRC-EXCEPT": "SD-01.02",
    "GRC-RISK": "SD-01.03", "GRC-COMP": "SD-01.04", "GRC-AWARE": "SD-08.01",
    "GRC-TPR": "SD-08.03", "GRC-CHANGE": "SD-05.04", "IAM-ID": "SD-03.01",
    "IAM-LIFE": "SD-03.01", "IAM-AUTH": "SD-03.02", "IAM-AUTHZ": "SD-03.03",
    "IAM-PAM": "SD-03.04", "IAM-REVIEW": "SD-03.03", "IPS-NET": "SD-04.01",
    "IPS-END": "SD-04.02", "IPS-SRV": "SD-04.02", "IPS-CFG": "SD-04.03",
    "IPS-CLOUD": "SD-04.04", "IPS-EMAIL": "SD-04.05", "IPS-VULN": "SD-06.03",
    "IPS-ASSET": "SD-02.01", "IPS-MOB": "SD-04.02", "IPS-COMPUTE": "SD-04.02",
    "IPS-EP": "SD-04.02", "APP-SDLC": "SD-05.01", "APP-API": "SD-05.02",
    "APP-WEB": "SD-05.02", "APP-SUPPLY": "SD-05.03", "APP-MOB": "SD-05.01",
    "APP-AI": "SD-05.01", "DPP-CLASS": "SD-02.03", "DPP-DAT": "SD-02.04",
    "DPP-CRYPTO": "SD-02.04", "DPP-PRIV": "SD-02.05", "DPP-DLP": "SD-02.04",
    "DMR-LOG": "SD-06.01", "DMR-MON": "SD-06.01", "DMR-DET": "SD-06.02",
    "DMR-AUTO": "SD-06.02", "DMR-TI": "SD-06.05", "DMR-HUNT": "SD-06.05",
    "DMR-IR": "SD-07.01", "DMR-FOR": "SD-07.02", "RCR-INC": "SD-07.01",
    "RCR-BKP": "SD-07.03", "RCR-BCP": "SD-07.04", "RCR-DR": "SD-07.04",
    "RCR-HA": "SD-07.04", "RCR-TEST": "SD-07.04", "RCR-CRISIS": "SD-07.05",
    "RCR-RANSOM": "SD-07.01",
}


def normalize_text(value: str | None) -> str:
    value = unicodedata.normalize("NFKC", value or "").lower()
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def semantic_tokens(value: str | None) -> set[str]:
    return {
        token for token in normalize_text(value).split()
        if token not in STOP_WORDS and len(token) > 1
    }


def text_hash(title: str, description: str) -> str:
    material = f"{unicodedata.normalize('NFC', title).strip()}\n{unicodedata.normalize('NFC', description).strip()}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def canonical_text(value: str) -> str:
    """Remove source markup while preserving its readable meaning."""

    value = MARKDOWN_LINK.sub(lambda match: match.group(1), value)
    value = CITATION.sub("", value)
    value = HTML_TAG.sub("", value)
    return re.sub(r"\s+", " ", value).strip()


def external_references(value: str) -> list[dict[str, str]]:
    """Extract source URLs before canonical prose is cleaned."""

    seen: set[tuple[str, str]] = set()
    result: list[dict[str, str]] = []
    for title, url in MARKDOWN_LINK.findall(value):
        signature = (title.strip(), url.strip())
        if signature in seen:
            continue
        seen.add(signature)
        result.append({"type": "ARTICLE", "title": signature[0], "url": signature[1]})
    return result


def _contains(text: str, phrases: Iterable[str]) -> bool:
    return any(phrase in text for phrase in phrases)


def _classify_type(title: str, description: str) -> tuple[str, float, str, list[str]]:
    text = normalize_text(f"{title} {description}")
    title_text = normalize_text(title)
    raw_title = unicodedata.normalize("NFKC", title or "").strip()
    if re.match(r"^t\d{4}(?:\s\d{3})?\b", title_text) or text.startswith(
        ("adversaries ", "an adversary ", "attackers ")
    ):
        return "ART-THR", 0.94, "The statement describes adversary behavior or a threat technique.", ["ART-CTR"]
    if _contains(text, ("security metric", "key performance indicator", " kpi ", "mean time to", "percentage of", "rate of")):
        return "ART-MET", 0.82, "The item itself is a measurable security metric or KPI.", ["ART-CTR"]
    if _contains(text, ("vulnerability is", "vulnerability that", "weakness allows", "weakness in")) and not _contains(text, ("scan", "assess", "manage", "remediate")):
        return "ART-VUL", 0.82, "The item describes a vulnerability or weakness itself.", ["ART-THR", "ART-CTR"]
    if re.match(r"^(GV|ID|PR|DE|RS|RC)\.[A-Z]{2}-\d+\b", raw_title, re.IGNORECASE):
        return "ART-OBJ", 0.78, "The statement is a framework outcome rather than an implementation mechanism.", ["ART-REQ", "ART-CTR"]
    if "render stored pan unreadable" in title_text:
        return "ART-REQ", 0.84, "The statement requires a data-protection outcome rather than describing a process artifact.", ["ART-CTR", "ART-PRO"]
    has_requirement_language = (
        description.strip().lower().startswith("verify that")
        or bool(re.search(r"\b(shall|must|required)\b", text))
    )
    named_artifact = bool(re.search(
        r"\b(policy|standard|program|plan|process|procedure|playbook)\s*$",
        raw_title,
        re.IGNORECASE,
    ))
    if has_requirement_language and not named_artifact:
        return "ART-REQ", 0.84, "The statement requires an outcome; referenced artifact nouns do not change its type.", ["ART-CTR", "ART-POL", "ART-PLN", "ART-PRO"]
    if "policy" in text and _contains(text, ("policy shall", "policy must", "policy is", "policy be identified", "policy be established", "policy be defined", "develop a policy", "establish a policy")):
        return "ART-POL", 0.86, "The item is the governing policy artifact or requires that policy artifact to exist.", ["ART-REQ"]
    if _contains(text, ("security standard", "configuration standard", "standard shall", "standard must", "establish a standard", "define a standard", "security baseline")):
        return "ART-STD", 0.84, "The item is a normative standard or baseline artifact.", ["ART-REQ", "ART-CFG"]
    if _contains(text, ("security principle", "guiding principle", "principle of")):
        return "ART-PRI", 0.82, "The item expresses a governing security principle.", ["ART-OBJ"]
    if "program" in text and _contains(text, ("establish", "develop", "maintain", "implement", "security program", "cybersecurity program", "awareness program")):
        return "ART-PRG", 0.82, "The item defines or operates a coordinated security program.", ["ART-PRO", "ART-REQ"]
    if "plan" in text and _contains(text, ("develop", "establish", "maintain", "implement", "response plan", "recovery plan", "action plan")):
        return "ART-PLN", 0.82, "The item is a security plan or requires a plan artifact.", ["ART-REQ", "ART-PRC"]
    if _contains(text, ("procedure", "playbook", "step by step", "testing steps")):
        return "ART-PRC", 0.80, "The item defines an executable procedure or playbook.", ["ART-PRO", "ART-REQ"]
    if _contains(text, ("establish and maintain a process", "management process", "lifecycle process", "process shall be", "process must be")):
        return "ART-PRO", 0.80, "The item defines a repeatable security process.", ["ART-PRC", "ART-REQ"]
    configuration_signals = (
        "configure ", "enable ", "disable ", "set ", "turn off ", "enforce tls",
        "minimum password", "pin length", "timeout", "cipher suite", "security setting",
        "automatic updates", "firewall rule", "directory listing", "default account",
    )
    if title_text.startswith(configuration_signals) or description.strip().lower().startswith(configuration_signals) or _contains(text, ("tls 1 2", "tls 1 3", "ssl v", "configuration value")):
        return "ART-CFG", 0.84, "The item specifies a concrete technical setting or hardening value.", ["ART-CTR"]
    if _contains(text, (" shall ", " must ", " is required to ", " are required to ", "requirements for")):
        return "ART-REQ", 0.79, "The statement imposes a required outcome or obligation.", ["ART-CTR"]
    if _contains(text, ("responsible and accountable", "roles and responsibilities")) and not _contains(text, ("assign", "document", "approve")):
        return "ART-OWN", 0.72, "The item primarily identifies security ownership or accountability.", ["ART-REQ"]
    return "ART-CTR", 0.74, "The imperative or safeguard statement reduces security risk without defining another artifact kind.", ["ART-REQ", "ART-CFG"]


def _domain_from_semantics(title: str, description: str, section: str | None) -> tuple[str, str, float]:
    text = normalize_text(f"{title} {description}")
    scored: list[tuple[int, int, str, str]] = []
    for order, (code, phrases) in enumerate(SUBDOMAIN_RULES):
        matched = [phrase for phrase in phrases if phrase in text]
        if matched:
            score = sum(2 + phrase.count(" ") for phrase in matched)
            scored.append((score, -order, code, ", ".join(matched[:3])))
    if scored:
        score, _, code, evidence = max(scored)
        return code[:5], code, min(0.90, 0.72 + score * 0.025)
    if section in SECTION_FALLBACKS:
        code = SECTION_FALLBACKS[section]
        return code[:5], code, 0.66
    section_upper = (section or "").upper()
    for prefix in sorted(PREFIX_FALLBACKS, key=len, reverse=True):
        if section_upper.startswith(prefix):
            code = PREFIX_FALLBACKS[prefix]
            return code[:5], code, 0.62
    # Every recovered row has a meaningful section.  Reaching this branch is a
    # deliberate fail-loud condition rather than a universal domain default.
    raise ValueError(f"no defensible SDT signal for section {section!r}")


def _jaccard(left: set[str], right: set[str]) -> float:
    return len(left & right) / len(left | right) if left or right else 0.0


def _reference_match(
    title: str, description: str, reference: list[dict[str, Any]] | None
) -> tuple[float, dict[str, Any] | None]:
    if not reference:
        return 0.0, None
    tokens = semantic_tokens(f"{title} {description}")
    best_score = 0.0
    best: dict[str, Any] | None = None
    for item in reference:
        score = _jaccard(
            tokens,
            item.get("_semantic_tokens")
            or semantic_tokens(
                f"{item.get('title_en', '')} {item.get('definition_short_en', '')}"
            ),
        )
        if score > best_score:
            best_score, best = score, item
    return best_score, best


def _requirement_type(source_refs: Iterable[str]) -> str:
    refs = " ".join(source_refs).upper()
    if any(value in refs for value in ("ECC", "NIST", "CIS", "ASVS", "PCI", "ISO")):
        return "RQT-STD"
    return "RQT-INT"


def _control_fields(text: str) -> tuple[str, str, str]:
    normalized = normalize_text(text)
    if _contains(normalized, ("awareness", "training", "employee behavior", "phishing simulation")):
        nature = "NAT-HUM"
    elif _contains(normalized, ("physical", "visitor", "secure area", "paper document")):
        nature = "NAT-PHY"
    elif _contains(normalized, ("configure", "software", "system", "network", "firewall", "encrypt", "scan", "monitor", "device", "application", "credential")):
        nature = "NAT-TEC"
    else:
        nature = "NAT-ORG"
    if _contains(normalized, ("recover", "restore", "backup")):
        function = "FUN-REC"
    elif _contains(normalized, ("remediate", "remove", "eradicate", "correct")):
        function = "FUN-COR"
    elif _contains(normalized, ("detect", "monitor", "log", "audit", "scan", "review", "alert")):
        function = "FUN-DET"
    else:
        function = "FUN-PRE"
    if _contains(normalized, ("configure", "scan", "log", "automatic", "software", "firewall", "encrypt", "system setting")):
        testability = "TST-AUTO"
    elif _contains(normalized, ("policy", "document", "procedure", "plan", "audit")):
        testability = "TST-DOC"
    else:
        testability = "TST-MAN"
    return nature, function, testability


def classify_record(
    record: dict[str, Any], *, reference: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    """Classify one recovered record from its own semantic text."""

    extracted = record.get("extracted_elements") or {}
    title = str(extracted.get("title_draft") or "").strip()
    source_description = str(extracted.get("description_draft") or "").strip()
    description = canonical_text(source_description)
    section = (record.get("source_metadata") or {}).get("source_section")
    original = (record.get("recovery_provenance") or {}).get("original_raw_record") or {}
    source_refs = original.get("source_refs") or []

    artifact_type, type_confidence, type_reason, alternatives = _classify_type(title, description)
    primary_domain, sub_domain, domain_confidence = _domain_from_semantics(title, description, section)

    match_score, match = _reference_match(title, description, reference)
    safe_reference_types = {
        "ART-REQ", "ART-OBJ", "ART-PRI", "ART-POL", "ART-STD", "ART-CTR",
        "ART-CTE", "ART-PRO", "ART-PRC", "ART-PRG", "ART-PLN", "ART-TSK",
        "ART-CFG", "ART-RUL", "ART-MET",
    }
    if (
        match_score >= 0.55
        and match is not None
        and (
            artifact_type == match.get("proposed_type")
            or (
                artifact_type in {"ART-CTR", "ART-REQ"}
                and match.get("proposed_type") in safe_reference_types
            )
        )
    ):
        artifact_type = str(match["proposed_type"])
        primary_domain = str(match["proposed_primary_domain"])
        sub_domain = str(match["proposed_sub_domain"])
        type_confidence = min(float(match.get("classification_confidence") or 0.78), 0.90)
        domain_confidence = max(domain_confidence, min(0.90, 0.65 + match_score * 0.3))
        type_reason = (
            f"A conservative semantic reference match ({match_score:.3f}) supports "
            f"{artifact_type} and {sub_domain}; {type_reason}"
        )

    confidence = round(min(type_confidence, domain_confidence), 2)
    requires_review = confidence <= 0.70
    result: dict[str, Any] = {
        "title_en": title,
        "definition_short_en": description,
        "external_references": external_references(source_description),
        "semantic_text_sha256": text_hash(title, description),
        "proposed_type": artifact_type,
        "proposed_abstraction_level": TYPE_LEVEL[artifact_type],
        "proposed_primary_domain": primary_domain,
        "proposed_sub_domain": sub_domain,
        "proposed_obligation_level": "OBL-MND" if any(
            marker in normalize_text(description) for marker in ("shall", "must", "required")
        ) else "OBL-REC",
        "proposed_requirement_type": None,
        "proposed_control_nature": None,
        "proposed_control_function": None,
        "proposed_testability": None,
        "proposed_priority": ((record.get("recovery_provenance") or {}).get("staging_evidence") or {}).get("proposed_priority") or "PRI-MEDIUM",
        "classification_confidence": confidence,
        "classification_rationale": (
            f"Semantic classification from this record's title and statement: {type_reason} "
            f"The SDT domain was selected from item-level terminology; source section was used "
            f"only as a low-confidence tie-breaker when the text had no unique domain phrase."
        ),
        "ai_review_status": "AIR-HUMAN-REVIEW" if requires_review else "AIR-AUTO-ACCEPTED",
        "requires_human_review": requires_review,
        "rejected_alternatives": alternatives,
        "classification_method": CLASSIFIER_VERSION,
    }
    if artifact_type == "ART-REQ":
        result["proposed_requirement_type"] = _requirement_type(source_refs)
    if artifact_type in {"ART-CTR", "ART-CTE"}:
        nature, function, testability = _control_fields(f"{title} {description}")
        result["proposed_control_nature"] = nature
        result["proposed_control_function"] = function
        result["proposed_testability"] = testability
    return result
