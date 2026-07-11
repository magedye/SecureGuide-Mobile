# AI Prompts and Intake Pipeline
**Project:** SecureGuide Mobile (Enterprise Reference Platform)
**Version:** 3.0

## 1. The Intake Pipeline
The Intake Pipeline is responsible for converting raw, unstructured PDF/HTML framework documents into the highly structured, SQLite-ready JSON format demanded by USACM v2.2.1.

### 1.1. Pipeline Stages
1. **Extraction (Raw Parsing):** Extracting verbatim text from source documents without alteration.
2. **Classification (USACM Assignment):** Using an LLM to assign exactly one `type` (e.g., ART-OBJ, ART-REQ, ART-CTR) and one `primary_domain` (SD-01 to SD-08) to each extracted entity.
3. **Relationship Mapping:** Linking child entities to parent entities (e.g., ART-CTR -> ART-REQ).
4. **Validation (JSON Schema):** Enforcing the JSON schema constraints before allowing import into the mobile SQLite database.

## 2. SDT v2.2.1 Tie-Breaker Rules
When the AI encounters ambiguity during the Classification stage, it must apply these rules:
- **Rule 1 (Policy vs. Procedure):** If it states "what" must be done at a high level, it is `ART-POL`. If it states "how" step-by-step, it is `ART-PRC`.
- **Rule 2 (Objective vs. Requirement):** If it states a broad goal ("Ensure availability"), it is `ART-OBJ`. If it states a specific condition to meet that goal ("Backups must be maintained"), it is `ART-REQ`.
- **Rule 3 (Requirement vs. Control):** If it mandates a condition, it is `ART-REQ`. If it describes a specific technical or administrative mechanism to satisfy that condition ("Use AES-256"), it is `ART-CTR`.

## 3. Standardized AI System Prompt (For Master Catalog Generation)
```markdown
You are a highly analytical Cybersecurity Data Architect specializing in the USACM v2.2.1 framework.
Your task is to classify raw security statements into the strict USACM taxonomy.

**Rules:**
1. Every entity MUST have a `type` from the allowed USACM list (22 codes): [ART-REQ, ART-OBJ, ART-PRI, ART-POL, ART-STD, ART-CTR, ART-CTE, ART-PRO, ART-PRC, ART-PRG, ART-PLN, ART-TSK, ART-CFG, ART-RUL, ART-EVD, ART-MET, ART-EXC, ART-RSK, ART-AST, ART-THR, ART-VUL, ART-OWN].
2. Every entity MUST have a `primary_domain` from SD-01 to SD-08 based on the SDT v2.2.1 mapping.
3. Apply the SDT v2.2.1 Tie-Breaker rules strictly. If an entity sounds like a control but is phrased as a broad goal, classify as ART-OBJ.
4. Output MUST be valid JSON adhering to the provided schema. No markdown formatting outside the JSON block.
```

## 4. Mobile App AI Features (Future Phase)
The mobile app's "AI Settings" (in the Settings Page) will allow users to connect to enterprise-hosted LLMs to automatically map their specific `enterprise_assets` to appropriate `threat_indicators` based on natural language queries (e.g., "We just installed a new Apache web server, what indicators should we watch?").

