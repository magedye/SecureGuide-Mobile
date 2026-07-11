import os

folder = r'D:\APP\secure-guide\New folder\SecureGuide_Mobile_Docs'
prd_file = os.path.join(folder, '01_Product_Requirements_Document_PRD.md')
rm_file = os.path.join(folder, '06_Implementation_Plan_and_Roadmap.md')

# PRD Append
with open(prd_file, 'a', encoding='utf-8') as f:
    f.write('''
## 8. Advanced Architectural NFRs
- **Data Isolation:** Operational data MUST be strictly separated from reference catalog data (Profile Artifacts vs Security Artifacts).
- **Dynamic Asset Intelligence:** The system must dynamically recalculate Asset Risk Scores and Control Coverage percentages whenever a related vulnerability or control state changes.
''')

# Roadmap Append
with open(rm_file, 'a', encoding='utf-8') as f:
    f.write('''
## 4. Advanced Refinement (Based on Architectural Deep Dive)
- **Phase 1b (Database Expansion):** Implement the separated 4-Tier Information Asset tables and Enterprise Profiles mapping logic.
- **Phase 2b (Advanced UI Screens):** Build the Profile Comparison Dashboard, Asset Intelligence UI, and Threat Indicator mapping views.
''')

print('Updated PRD and Roadmap successfully.')
