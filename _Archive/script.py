import os
import re

folder = r'D:\APP\secure-guide\New folder'
docs_folder = os.path.join(folder, 'SecureGuide_Mobile_Docs')

def extract_sql(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    # Find all SQL blocks
    sql_blocks = re.findall(r'`sql\s+(.*?)\s+`', content, re.DOTALL)
    return '\n'.join([f'`sql\n{block.strip()}\n`\n' for block in sql_blocks])

info_assets_sql = extract_sql(os.path.join(folder, 'Information Assets Module.md'))
profile_sql = extract_sql(os.path.join(folder, 'profile based.md'))

new_db_schema = f'''# Database Schema and Models
**Project:** SecureGuide Mobile (Enterprise Reference Platform)
**Version:** 3.0

## 1. Core Principles
- **Offline-First SQLite:** All data is stored locally.
- **Strict Normalization:** USACM CHECK constraints enforce data integrity at the database level.
- **Reference vs. Operational Data Separation:** Global frameworks are immutable (Master Catalog); profile-specific data is operational (Enterprise Profiles).

## 2. Advanced Schema Definitions

The database is divided into four main logical modules, adapted from the advanced architectural studies.

### 2.1. Master Catalog Module (Reference Data)
Contains the immutable data imported from standard frameworks (NIST, ISO, etc.). Operational fields have been strictly removed to ensure the catalog remains a pure reference.

{profile_sql.split('CREATE TABLE IF NOT EXISTS enterprise_profiles')[0].strip()}

### 2.2. Enterprise Profiles Module (Operational Data)
Manages institutional contexts and their implementation states. This is the core of the separation logic, where a profile tracks its own \implementation_status\ for the referenced artifacts.

`sql
CREATE TABLE IF NOT EXISTS enterprise_profiles {profile_sql.split('CREATE TABLE IF NOT EXISTS enterprise_profiles')[1].split('CREATE TABLE IF NOT EXISTS artifact_tags')[0].strip()}
`

### 2.3. Information Assets Module (4-Tier Architecture)
Maps the enterprise's physical, logical, and human assets, linking them dynamically to controls, vulnerabilities, and monitoring tools to generate real-time coverage and risk scores.

{info_assets_sql}

### 2.4. Core Relationship Tables (USACM Standards)
`sql
CREATE TABLE IF NOT EXISTS artifact_tags {profile_sql.split('CREATE TABLE IF NOT EXISTS artifact_tags')[1].strip()}
`

## 3. Key USACM Constraints
The SQLite schema implements strict \CHECK\ constraints based on USACM v2.2.1 and SDT v2.2.1:
- \	ype\ MUST be one of: \ART-OBJ\, \ART-REQ\, \ART-CTR\, \ART-GDL\, etc.
- \primary_domain\ MUST be between \SD-01\ and \SD-08\.
- \implementation_status\ MUST be mapped to the profile, not the root artifact, ensuring contextual isolation.

These constraints ensure that the application layer (the 8 Engines) always receives perfectly formatted data, eliminating defensive programming overhead in the UI.
'''

with open(os.path.join(docs_folder, '03_Database_Schema_and_Models.md'), 'w', encoding='utf-8') as f:
    f.write(new_db_schema)

print('Updated 03_Database_Schema_and_Models.md successfully.')
