"""Inbound-only aliases. Canonical storage always uses USACM/SDT values."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from .models import ClassificationContext


ARTIFACT_TYPES = {
    "ART-REQ", "ART-OBJ", "ART-PRI", "ART-POL", "ART-STD", "ART-CTR",
    "ART-CTE", "ART-PRO", "ART-PRC", "ART-PRG", "ART-PLN", "ART-TSK",
    "ART-CFG", "ART-RUL", "ART-EVD", "ART-MET", "ART-EXC", "ART-RSK",
    "ART-AST", "ART-THR", "ART-VUL", "ART-OWN",
}
CONTROL_NATURES = {"NAT-ORG", "NAT-HUM", "NAT-PHY", "NAT-TEC"}
CONTROL_FUNCTIONS = {
    "FUN-PRE", "FUN-DET", "FUN-COR", "FUN-REC", "FUN-DRR", "FUN-COM"
}
PRIMARY_DOMAINS = {f"SD-{index:02d}" for index in range(1, 9)}
OBLIGATION_LEVELS = {"OBL-MND", "OBL-CON", "OBL-REC", "OBL-OPT"}


DIRECT_ALIASES = {
    "artifact_type": {
        "ART-ROL": ("ART-OWN", 0.95, "Legacy role alias normalized to ART-OWN"),
    },
    "control_nature": {
        "NAT-GOV": ("NAT-ORG", 0.92, "Governance execution normalized to organizational nature"),
    },
    "control_function": {
        "FUN-PRV": ("FUN-PRE", 0.97, "Preventive alias normalized to FUN-PRE"),
        "FUN-DETERR": ("FUN-DRR", 0.75, "Deterrence approximated as deterrent/damage-reduction function"),
    },
    "obligation_level": {
        "MANDATORY": ("OBL-MND", 0.98, "Friendly obligation label normalized"),
        "CONDITIONAL": ("OBL-CON", 0.98, "Friendly obligation label normalized"),
        "RECOMMENDED": ("OBL-REC", 0.98, "Friendly obligation label normalized"),
        "OPTIONAL": ("OBL-OPT", 0.98, "Friendly obligation label normalized"),
    },
}

# These values convey useful intent but do not have a safe one-to-one USACM
# mapping. They are omitted from matching and explicitly route the result to
# review; they are never written as canonical values.
AMBIGUOUS_ALIASES = {
    "control_nature": {
        "NAT-OPS": "Operational can be organizational or technical; choose with context",
        "NAT-LEG": "Legal is an obligation source/requirement type, not control nature",
        "NAT-TPR": "Third-party is context/domain, not a canonical control nature",
    },
    "control_function": {
        "FUN-DIR": "Directive intent is derived from artifact type; no USACM function maps directly",
        "FUN-COMP": "Compliance is domain/obligation context, not a canonical control function",
    },
    "obligation_level": {
        "PROHIBITED": "USACM obligation level has no prohibited value; model the prohibition in the requirement text",
    },
}


class ClassificationValueError(ValueError):
    pass


def _normalize(
    field_name: str,
    value: str | None,
    allowed: set[str],
) -> tuple[str | None, list[dict[str, Any]], list[str], float]:
    if value is None:
        return None, [], [], 1.0
    value = value.strip().upper()
    if value in allowed:
        return value, [], [], 1.0
    direct = DIRECT_ALIASES.get(field_name, {}).get(value)
    if direct:
        canonical, quality, reason = direct
        return canonical, [{
            "field": field_name,
            "inputValue": value,
            "canonicalValue": canonical,
            "normalizationType": "DIRECT_ALIAS",
            "reason": reason,
            "quality": quality,
        }], [], quality
    ambiguous = AMBIGUOUS_ALIASES.get(field_name, {}).get(value)
    if ambiguous:
        return None, [{
            "field": field_name,
            "inputValue": value,
            "canonicalValue": None,
            "normalizationType": "AMBIGUOUS_ALIAS",
            "reason": ambiguous,
            "quality": 0.55,
        }], [f"{field_name}:{value} requires human review: {ambiguous}"], 0.55
    raise ClassificationValueError(f"invalid {field_name}: {value}")


def normalize_context(
    context: ClassificationContext,
) -> tuple[ClassificationContext, list[dict[str, Any]], list[str], float]:
    events: list[dict[str, Any]] = []
    reasons: list[str] = []
    qualities: list[float] = []
    values: dict[str, str | None] = {}
    specs = (
        ("artifact_type", context.artifact_type, ARTIFACT_TYPES),
        ("control_nature", context.control_nature, CONTROL_NATURES),
        ("control_function", context.control_function, CONTROL_FUNCTIONS),
        ("primary_domain", context.primary_domain, PRIMARY_DOMAINS),
        ("obligation_level", context.obligation_level, OBLIGATION_LEVELS),
    )
    for field_name, value, allowed in specs:
        normalized, item_events, item_reasons, quality = _normalize(
            field_name, value, allowed
        )
        values[field_name] = normalized
        events.extend(item_events)
        reasons.extend(item_reasons)
        qualities.append(quality)
    normalized_context = replace(context, **values)
    return normalized_context, events, reasons, min(qualities or [1.0])
