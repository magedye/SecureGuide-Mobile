import os
import re

folder = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
docs_folder = os.path.join(folder, 'SecureGuide_Mobile_Docs')
arch_file = os.path.join(docs_folder, '02_Technical_Architecture_TAD.md')

def get_file_content(filename):
    with open(os.path.join(folder, filename), 'r', encoding='utf-8') as f:
        return f.read()

concept_model = get_file_content('Comprehensive Concept Relationship Model for SecureGuide.md')

# Extract sections
hierarchy = concept_model.split('## ??? ?????: ??????? ?????? ???????? (Entity Hierarchy)')[1].split('## ??')[0].strip() if '## ??? ?????: ??????? ?????? ????????' in concept_model else ""
relationships = concept_model.split('## ?? ??????: ???? ???????? (Relationship Mapping)')[1].split('## ')[0].strip() if '## ?? ??????: ???? ????????' in concept_model else ""

injection_text = f'''

## 6. Comprehensive Concept Relationship Model (Incorporated)

### 6.1 Entity Hierarchy (USACM v2.2.1)
{hierarchy}

### 6.2 Relationship Mapping
{relationships}
'''

with open(arch_file, 'a', encoding='utf-8') as f:
    f.write(injection_text)

print('Updated 02_Technical_Architecture_TAD.md successfully.')
