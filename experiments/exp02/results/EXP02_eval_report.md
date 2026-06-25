# EXP-02 — BM25 retrieval eval (DDXPlus validate)

- Corpus: 49 KB docs (kb_ddxplus_FIXED.json)
- Queries: 132448 patients (skipped empty queries: 0; total rows read: 132448)
- Query text = normalize_symptom_phrase(question_en) of patient EVIDENCES (same normalizer as build_kb)
- BM25 Okapi k1=1.5 b=0.75; tie-break deterministic

## Overall metrics

| BM25 field variant | Hit@1 | Hit@3 | Hit@5 | MRR | n |
|---|---|---|---|---|---|
| keyword_text | 98.47% | 99.95% | 99.99% | 0.9921 | 132448 |
| keyword_text+description | 98.78% | 99.96% | 100.00% | 0.9937 | 132448 |

## Per-disease Hit@1 / MRR (variant: keyword_text)

| Disease | Hit@1 | MRR | n | affected |
|---|---|---|---|---|
| Acute rhinosinusitis | 49.62% | 0.7481 | 1866 |  |
| Unstable angina | 84.32% | 0.9204 | 2748 |  |
| Myocarditis | 93.54% | 0.9651 | 1547 |  |
| Bronchitis | 96.87% | 0.9831 | 3543 |  |
| URTI | 97.78% | 0.9888 | 8656 |  |
| SLE | 97.97% | 0.9890 | 1579 |  |
| Stable angina | 98.25% | 0.9912 | 2340 |  |
| Cluster headache | 99.05% | 0.9936 | 2841 | ⚠️ |
| Viral pharyngitis | 98.96% | 0.9943 | 8246 |  |
| Inguinal hernia | 99.20% | 0.9945 | 2632 |  |
| Acute laryngitis | 99.21% | 0.9960 | 3407 |  |
| Pancreatic neoplasm | 99.88% | 0.9994 | 2582 |  |
| GERD | 99.91% | 0.9994 | 3426 | ⚠️ |
| Bronchospasm / acute asthma exacerbation | 99.91% | 0.9995 | 2209 |  |
| Bronchiectasis | 99.91% | 0.9996 | 2319 | ⚠️ |
| HIV (initial infection) | 99.92% | 0.9996 | 3852 |  |
| Anaphylaxis | 99.95% | 0.9997 | 3754 |  |
| Pulmonary embolism | 99.97% | 0.9998 | 3725 | ⚠️ |
| Possible NSTEMI / STEMI | 99.97% | 0.9998 | 2943 |  |
| Pneumonia | 99.97% | 0.9999 | 3484 |  |
| Anemia | 100.00% | 1.0000 | 6903 | ⚠️ |
| Panic attack | 100.00% | 1.0000 | 3237 | ⚠️ |
| Influenza | 100.00% | 1.0000 | 3590 |  |
| Boerhaave | 100.00% | 1.0000 | 2075 |  |
| Allergic sinusitis | 100.00% | 1.0000 | 2136 |  |
| Acute otitis media | 100.00% | 1.0000 | 3474 |  |
| Myasthenia gravis | 100.00% | 1.0000 | 2159 |  |
| Acute dystonic reactions | 100.00% | 1.0000 | 3281 |  |
| Pericarditis | 100.00% | 1.0000 | 3032 |  |
| Atrial fibrillation | 100.00% | 1.0000 | 2609 |  |
| Chronic rhinosinusitis | 100.00% | 1.0000 | 2717 |  |
| Spontaneous pneumothorax | 100.00% | 1.0000 | 1405 |  |
| Pulmonary neoplasm | 100.00% | 1.0000 | 1891 |  |
| Acute pulmonary edema | 100.00% | 1.0000 | 2500 |  |
| Scombroid food poisoning | 100.00% | 1.0000 | 2250 |  |
| PSVT | 100.00% | 1.0000 | 2376 |  |
| Acute COPD exacerbation / infection | 100.00% | 1.0000 | 2076 |  |
| Localized edema | 100.00% | 1.0000 | 3694 | ⚠️ |
| Guillain-Barré syndrome | 100.00% | 1.0000 | 2557 | ⚠️ |
| Larygospasm | 100.00% | 1.0000 | 668 |  |
| Sarcoidosis | 100.00% | 1.0000 | 3028 |  |
| Spontaneous rib fracture | 100.00% | 1.0000 | 782 |  |
| Chagas | 100.00% | 1.0000 | 1124 |  |
| Croup | 100.00% | 1.0000 | 267 |  |
| Epiglottitis | 100.00% | 1.0000 | 2248 |  |
| Tuberculosis | 100.00% | 1.0000 | 2007 | ⚠️ |
| Whooping cough | 100.00% | 1.0000 | 545 |  |
| Bronchiolitis | 100.00% | 1.0000 | 28 |  |
| Ebola | 100.00% | 1.0000 | 90 |  |