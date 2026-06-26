# ICD-10 & Severity Reference — DDXPlus Knowledge Base

**Project:** Disease-Diagnosis-RAG-System — AIO 2026, Project 1
**Team:** Med / Pharm / Bio Nexus
**Author:** Nguyễn Văn Thương (Team Leader — Domain Expert)
**Generated:** 2026-06-12
**Source:** `release_conditions.json` (DDXPlus, CC-BY)

## Methodology

- ICD-10 codes are taken verbatim from the source, then trimmed and upper-cased.
- Chapters are assigned by official numeric ranges, not by leading letter.
- For the single multi-code condition, the canonical `doc_id` is pinned
  explicitly (see `CANONICAL_OVERRIDES`); all codes are retained.
- A condition is flagged severe when `severity <= 2` (1 = most severe).

## Summary

- Total conditions: **49**
- Severity distribution: sev 1 = 5 · sev 2 = 12 · sev 3 = 17 · sev 4 = 12 · sev 5 = 3
- Severe conditions (severity ≤ 2): **17**
- Multi-code conditions: **1**

## Reference table

| Disease | ICD-10 (raw) | Primary | Chapter | Range | Severity | Severe |
| --- | --- | --- | --- | --- | --- | --- |
| Acute COPD exacerbation / infection | j44.1 | J44.1 | X | J00–J99 | 3 |  |
| Acute dystonic reactions | G24.02 | G24.02 | VI | G00–G99 | 2 | ✅ |
| Acute laryngitis | J04.0 | J04.0 | X | J00–J99 | 4 |  |
| Acute otitis media | H66.90 | H66.90 | VIII | H60–H95 | 4 |  |
| Acute pulmonary edema | J81.0 | J81.0 | X | J00–J99 | 1 | ✅ |
| Acute rhinosinusitis | j01 | J01 | X | J00–J99 | 4 |  |
| Allergic sinusitis | J30 | J30 | X | J00–J99 | 4 |  |
| Anaphylaxis | T78.0 | T78.0 | XIX | S00–T88 | 1 | ✅ |
| Anemia | D64.9 | D64.9 | III | D50–D89 | 4 |  |
| Atrial fibrillation | I48.91 | I48.91 | IX | I00–I99 | 3 |  |
| Boerhaave | K22.3 | K22.3 | XI | K00–K95 | 2 | ✅ |
| Bronchiectasis | J47 | J47 | X | J00–J99 | 3 |  |
| Bronchiolitis | j21 | J21 | X | J00–J99 | 3 |  |
| Bronchitis | j40 | J40 | X | J00–J99 | 4 |  |
| Bronchospasm / acute asthma exacerbation | J45 | J45 | X | J00–J99 | 3 |  |
| Chagas | B57 | B57 | I | A00–B99 | 3 |  |
| Chronic rhinosinusitis | j32 | J32 | X | J00–J99 | 5 |  |
| Cluster headache | g44.009 | G44.009 | VI | G00–G99 | 3 |  |
| Croup | J05.0 | J05.0 | X | J00–J99 | 2 | ✅ |
| Ebola | a98.4 | A98.4 | I | A00–B99 | 1 | ✅ |
| Epiglottitis | J05.1 | J05.1 | X | J00–J99 | 2 | ✅ |
| GERD | K21 | K21 | XI | K00–K95 | 3 |  |
| Guillain-Barré syndrome | G61.0 | G61.0 | VI | G00–G99 | 2 | ✅ |
| HIV (initial infection) | B20 | B20 | I | A00–B99 | 3 |  |
| Influenza | j11.1 | J11.1 | X | J00–J99 | 3 |  |
| Inguinal hernia | K40 | K40 | XI | K00–K95 | 3 |  |
| Larygospasm | J38.5 | J38.5 | X | J00–J99 | 1 | ✅ |
| Localized edema | R60.0 | R60.0 | XVIII | R00–R99 | 4 |  |
| Myasthenia gravis | G70.0 | G70.0 | VI | G00–G99 | 3 |  |
| Myocarditis | I51.4 | I51.4 | IX | I00–I99 | 2 | ✅ |
| Pancreatic neoplasm | c25 | C25 | II | C00–D49 | 3 |  |
| Panic attack | f41 | F41 | V | F01–F99 | 5 |  |
| Pericarditis | I30 | I30 | IX | I00–I99 | 4 |  |
| Pneumonia | j17, j18 | J18 | X | J00–J99 | 3 |  |
| Possible NSTEMI / STEMI | I21 | I21 | IX | I00–I99 | 1 | ✅ |
| PSVT | I47.1 | I47.1 | IX | I00–I99 | 2 | ✅ |
| Pulmonary embolism | i26 | I26 | IX | I00–I99 | 2 | ✅ |
| Pulmonary neoplasm | c34 | C34 | II | C00–D49 | 3 |  |
| Sarcoidosis | d86 | D86 | III | D50–D89 | 4 |  |
| Scombroid food poisoning | T61.1 | T61.1 | XIX | S00–T88 | 2 | ✅ |
| SLE | M32 | M32 | XIII | M00–M99 | 4 |  |
| Spontaneous pneumothorax | J93 | J93 | X | J00–J99 | 2 | ✅ |
| Spontaneous rib fracture | S22.9 | S22.9 | XIX | S00–T88 | 3 |  |
| Stable angina | I20.9 | I20.9 | IX | I00–I99 | 2 | ✅ |
| Tuberculosis | a15 | A15 | I | A00–B99 | 3 |  |
| Unstable angina | I20.0 | I20.0 | IX | I00–I99 | 2 | ✅ |
| URTI | j06.9 | J06.9 | X | J00–J99 | 5 |  |
| Viral pharyngitis | J02.9 | J02.9 | X | J00–J99 | 4 |  |
| Whooping cough | A37 | A37 | I | A00–B99 | 4 |  |
