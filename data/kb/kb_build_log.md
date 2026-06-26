# KB build log — DDXPlus Design A (49 docs)

- conditions source: `release_conditions.json` (49 conditions)
- evidences source: `release_evidences.json` (223 evidences)

## ICD-10 normalization
- codes normalized (case/whitespace changed): 16
  - `g44.009`->`G44.009`, `a15`->`A15`, `a98.4`->`A98.4`, `f41`->`F41`, `j40`->`J40`, `j44.1`->`J44.1`, `i26`->`I26`, `j06.9`->`J06.9`, `j11.1`->`J11.1`, `j17, j18`->`J17, J18`, `j01`->`J01`, `j32`->`J32`, `j21`->`J21`, `c34`->`C34`, `d86`->`D86`, `c25`->`C25`
- duplicate ICD-10 after normalization: none

## Validation
- document count: 49 (expected 49) -> OK
- doc_id uniqueness: 49/49 -> OK
- severity int in 1..5: OK
- embedding dims present: {0} (expected {384} after --embed, {0} otherwise)
- precautions field: omitted (not in DDXPlus mapping) -> OK
- separate icd10_id field: omitted (doc_id = ICD-10) -> OK

## Symptom normalization spot-check (raw question -> phrase)
- `Do you feel pain somewhere?`  ->  **pain present**
- `Do you have pain somewhere, related to your reason for consulting?`  ->  **pain related to consultation**
- `Does the pain radiate to another location?`  ->  **pain radiation**
- `Characterize your pain:`  ->  **pain character**
- `How fast did the pain appear?`  ->  **pain onset speed**
- `How intense is the pain?`  ->  **pain intensity**
- `How precisely is the pain located?`  ->  **pain location**
- `Are you experiencing shortness of breath or difficulty breathing in a significant way?`  ->  **shortness of breath or difficulty breathing in a significant way**
- `Do you have pain that is increased when you breathe in deeply?`  ->  **pain that is increased when you breathe in deeply**
- `Do you have symptoms that are increased with physical exertion but alleviated with rest?`  ->  **symptoms that are increased with physical exertion but alleviated with rest**
- `Do you have chest pain even at rest?`  ->  **chest pain even at rest**
- `Do you have swelling in one or more areas of your body?`  ->  **swelling in one or more areas of your body**
- `Do you smoke cigarettes?`  ->  **smoke cigarettes**
- `Have any of your family members ever had a pneumothorax?`  ->  **family members ever had a pneumothorax**
- `Have you ever had a spontaneous pneumothorax?`  ->  **spontaneous pneumothorax**
- `Do you have a chronic obstructive pulmonary disease (COPD)?`  ->  **chronic obstructive pulmonary disease**
- `Have you traveled out of the country in the last 4 weeks?`  ->  **recent international travel**
- `Do you feel that your eyes produce excessive tears?`  ->  **your eyes produce excessive tears**
- `Do you have nasal congestion or a clear runny nose?`  ->  **nasal congestion / runny nose**
- `Did you previously, or do you currently, have any weakness/paralysis in one or more of your limbs or in your face?`  ->  **weakness/paralysis in one or more of your limbs or in your face**
- `Have any of your family members been diagnosed with cluster headaches?`  ->  **family members been diagnosed with cluster headaches**
- `Do you drink alcohol excessively or do you have an addiction to alcohol?`  ->  **drink alcohol excessively**
- `Do you take medication that dilates your blood vessels?`  ->  **take medication that dilates your blood vessels**
- `Have you recently thrown up blood or something resembling coffee beans?`  ->  **thrown up blood or something resembling coffee beans**

## Patient/eval-set duplicate rows (Insight #1c)
- 101 exact-duplicate rows (~0.075%) live in the PATIENT/eval CSVs, NOT in this KB.
- The KB is built from `release_conditions.json` (49 unique conditions), so KB has no dup risk.
- Recommendation (pending @Phuoc Nguyen sign-off): DROP exact dups on the eval/query set
  before computing Hit@1 / MRR, to avoid double-counting a single measurement. Log dropped ids.
