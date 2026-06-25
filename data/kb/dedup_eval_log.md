# Eval-set dedup log — DDXPlus (Insight #1c)

- source: `/sessions/loving-happy-noether/mnt/AIO-Project`
- duplicate definition: exact match on ALL columns (AGE, DIFFERENTIAL_DIAGNOSIS, SEX, PATHOLOGY, EVIDENCES, INITIAL_EVIDENCE)
- policy: keep first occurrence, drop the rest, log dropped row indices

## train: 1,025,602 rows (not an eval split — not deduped, identity cached for leakage check)

## validate
- original rows: 132,448
- exact duplicates dropped: 75
- rows after dedup: 132,373
- output: `release_validate_patients_dedup.csv`
- duplicate share: 0.0566%
- dropped rows by PATHOLOGY (which classes the dups fall on):
  - Larygospasm: 17 dropped / 668 in class (2.545% of class)
  - Allergic sinusitis: 13 dropped / 2,136 in class (0.609% of class)
  - Guillain-Barré syndrome: 7 dropped / 2,557 in class (0.274% of class)
  - Whooping cough: 7 dropped / 545 in class (1.284% of class)
  - Bronchospasm / acute asthma exacerbation: 6 dropped / 2,209 in class (0.272% of class)
  - Acute COPD exacerbation / infection: 6 dropped / 2,076 in class (0.289% of class)
  - Myasthenia gravis: 4 dropped / 2,159 in class (0.185% of class)
  - Atrial fibrillation: 4 dropped / 2,609 in class (0.153% of class)
  - Acute dystonic reactions: 3 dropped / 3,281 in class (0.091% of class)
  - Tuberculosis: 3 dropped / 2,007 in class (0.149% of class)
  - Bronchiectasis: 2 dropped / 2,319 in class (0.086% of class)
  - PSVT: 2 dropped / 2,376 in class (0.084% of class)
  - Croup: 1 dropped / 267 in class (0.375% of class)
- dropped row indices (first 50 of 75): [16765, 20977, 35121, 38135, 39328, 43061, 43189, 43224, 44186, 44463, 45313, 46152, 57880, 59279, 60640, 61019, 62272, 68164, 69329, 72928, 73145, 73480, 73668, 77646, 78911, 80696, 86698, 87700, 89700, 92722, 93035, 93901, 96286, 98562, 98586, 99120, 103239, 103348, 103593, 104914, 105087, 107775, 108128, 108279, 110099, 110310, 111752, 112359, 113148, 113583]

## test
- original rows: 134,529
- exact duplicates dropped: 101
- rows after dedup: 134,428
- output: `release_test_patients_dedup.csv`
- duplicate share: 0.0751%
- dropped rows by PATHOLOGY (which classes the dups fall on):
  - Larygospasm: 27 dropped / 785 in class (3.439% of class)
  - Allergic sinusitis: 16 dropped / 2,411 in class (0.664% of class)
  - Bronchospasm / acute asthma exacerbation: 15 dropped / 2,222 in class (0.675% of class)
  - Whooping cough: 10 dropped / 549 in class (1.821% of class)
  - Guillain-Barré syndrome: 9 dropped / 2,601 in class (0.346% of class)
  - Acute COPD exacerbation / infection: 6 dropped / 2,153 in class (0.279% of class)
  - Acute dystonic reactions: 4 dropped / 3,302 in class (0.121% of class)
  - Bronchiectasis: 4 dropped / 2,454 in class (0.163% of class)
  - PSVT: 3 dropped / 2,443 in class (0.123% of class)
  - Atrial fibrillation: 2 dropped / 2,831 in class (0.071% of class)
  - Myasthenia gravis: 2 dropped / 2,215 in class (0.090% of class)
  - Croup: 2 dropped / 344 in class (0.581% of class)
  - Pulmonary neoplasm: 1 dropped / 1,918 in class (0.052% of class)
- dropped row indices (first 50 of 101): [7639, 9954, 14114, 23336, 26745, 30040, 30047, 32735, 33034, 35383, 35715, 36918, 37752, 40132, 44081, 47241, 49326, 50819, 51885, 53014, 54706, 57046, 57497, 57506, 57683, 58245, 59682, 60194, 60302, 62606, 63316, 63359, 64955, 67713, 69919, 70551, 71707, 71848, 72107, 72634, 72741, 74469, 76765, 79306, 79334, 81414, 82264, 82333, 85382, 85791]

## Cross-split overlap (leakage check)
- key: (AGE, SEX, PATHOLOGY, EVIDENCES). Overlap here = same patient in two splits.

- train ∩ validate: 4,403 overlapping identities
- train ∩ test: 4,820 overlapping identities
- validate ∩ test: 502 overlapping identities

Note: within-split dup = double-counting one measurement (fixed above). Cross-split overlap, if large, is a leakage concern for any patient-trained component; for retrieval against a condition-built KB the risk is low, but the numbers above let the team confirm.
