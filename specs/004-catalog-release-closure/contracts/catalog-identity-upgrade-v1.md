# Contract: Catalog Identity Upgrade v1

## Public naming

Current code, configuration, public documentation, workbook sheets, source catalog IDs, raw IDs, staging IDs, and newly built canonical IDs MUST use SecureGuide-neutral names. The former product token is permitted only in immutable historical migrations, archived material, explicit alias values, and source-evidence payloads whose mutation would break provenance.

## Identifier migration

1. A release candidate MUST contain one alias for every changed canonical artifact ID.
2. Alias targets MUST exist and MUST NOT point to another alias.
3. Source and raw IDs MUST be rewritten deterministically in newly built catalogs while preserved historical values remain queryable through provenance/alias fields.
4. Installed upgrades MUST remap every foreign key in both reference and profile data in one transaction.
5. A missing or ambiguous mapping MUST fail closed and roll back.

## Compatibility surface

The mobile runtime MAY accept an old artifact ID as an input lookup key, but MUST return/store the current ID. New exports MUST emit current IDs and MAY include the historical ID only in the dedicated alias/provenance sheets.

## Verification

- Active-name scan returns no unapproved former-token occurrence.
- Historical exception scan contains only allowlisted files/fields.
- Alias coverage equals the number of changed canonical IDs.
- Upgrade fixture with operational profile rows preserves row values after remapping.

