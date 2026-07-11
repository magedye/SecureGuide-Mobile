import json
import re

usacm_path = r'D:\APP\secure-guide\New folder\reference\usacm_v2.2.1.md'
sdt_path = r'D:\APP\secure-guide\New folder\reference\sdt_v2.2.1.md'
out_usacm = r'D:\APP\secure-guide\New folder\reference\usacm_codes.json'
out_sdt = r'D:\APP\secure-guide\New folder\reference\sdt_domains.json'

# Extract USACM Types
usacm_types = []
with open(usacm_path, 'r', encoding='utf-8') as f:
    content = f.read()
    # Looks like | ART-REQ | Requirement |
    matches = re.findall(r'\|\s*(ART-[A-Z]+)\s*\|\s*([^|]+?)\s*\|', content)
    for m in matches:
        code = m[0].strip()
        name = m[1].strip()
        if code not in [x['code'] for x in usacm_types]:
            usacm_types.append({"code": code, "name": name})

with open(out_usacm, 'w', encoding='utf-8') as f:
    json.dump(usacm_types, f, indent=2, ensure_ascii=False)

# Extract SDT Domains and Subdomains
sdt_list = []
with open(sdt_path, 'r', encoding='utf-8') as f:
    content = f.read()
    
    # Domains: ## SD-01: Governance, Risk & Compliance
    domains = re.findall(r'##\s*(SD-0\d):\s*(.+)', content)
    
    # Subdomains: | SD-01.01 | Cybersecurity Strategy & Governance |
    subdomains = re.findall(r'\|\s*(SD-0\d\.\d\d)\s*\|\s*([^|]+?)\s*\|', content)
    
    for d in domains:
        d_code = d[0].strip()
        d_name = d[1].strip()
        subs = []
        for s in subdomains:
            if s[0].replace('.', '-') == d_code or s[0].startswith(d_code.replace('-', '.')) or s[0].startswith(d_code):
                subs.append({"code": s[0], "name": s[1].strip()})
        # Try again with exactly matching the first 5 chars
        if not subs:
            prefix = d_code.replace('-', '-') # wait, code is SD-01, sub is SD-01.01
            for s in subdomains:
                if s[0].startswith(d_code):
                    subs.append({"code": s[0], "name": s[1].strip()})
                
        sdt_list.append({
            "code": d_code,
            "name": d_name,
            "sub_domains": subs
        })

with open(out_sdt, 'w', encoding='utf-8') as f:
    json.dump(sdt_list, f, indent=2, ensure_ascii=False)

print(f"Extracted {len(usacm_types)} USACM types.")
print(f"Extracted {len(sdt_list)} SDT Domains and {len(subdomains)} Subdomains.")
