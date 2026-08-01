import json
from scripts._promote_common import enrichment_blockers

def test_valid_tags():
    row = {'proposed_tags_json': json.dumps([
        {'tag_type': 'Technology', 'tag_value': 'Cloud'},
        {'tag_type': 'Context', 'tag_value': 'Production'}
    ])}
    blockers = enrichment_blockers(row)
    assert not blockers, f"Should have no blockers, got {blockers}"

def test_invalid_tag_type():
    row = {'proposed_tags_json': json.dumps([
        {'tag_type': 'Technology', 'tag_value': 'Cloud'},
        {'tag_type': 'InvalidType', 'tag_value': 'Value'}
    ])}
    blockers = enrichment_blockers(row)
    assert any("invalid tag_type 'InvalidType'" in b for b in blockers)

def test_duplicate_tags():
    row = {'proposed_tags_json': json.dumps([
        {'tag_type': 'Technology', 'tag_value': 'Cloud'},
        {'tag_type': 'Technology', 'tag_value': 'Cloud'}
    ])}
    blockers = enrichment_blockers(row)
    assert any("duplicate tag 'Technology:Cloud'" in b for b in blockers)

def test_missing_fields():
    row = {'proposed_tags_json': json.dumps([
        {'tag_type': 'Technology'}
    ])}
    blockers = enrichment_blockers(row)
    assert any("tag missing tag_type or tag_value" in b for b in blockers)

def test_malformed_json():
    row = {'proposed_tags_json': '{"not": "array"}'}
    blockers = enrichment_blockers(row)
    assert any("proposed_tags_json must be a JSON array" in b for b in blockers)
