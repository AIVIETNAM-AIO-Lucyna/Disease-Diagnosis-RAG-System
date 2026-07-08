# Báo cáo QA — Phase 1 (Nguyễn Thị Diễm Hương)

Tài liệu này gồm: (1) các chỉ số QA đã tính từ dữ liệu thật, (2) các điểm cần
xử lý trong báo cáo, (3) checklist rà soát cuối. Mọi con số đều truy nguồn được.

---

## 1. Chỉ số QA đã tính (số liệu thật, đã đối chiếu)

Nguồn: `experiments/exp02/results/exp02_per_disease.csv` (per-disease BM25) +
`data/kb/icd10_audit.csv` (severity). Phép tính Hit@1/MRR tái lập **khớp tuyệt
đối** với Bảng 1 sec07 (98.47% / 98.78%; 0.9921 / 0.9937) → dữ liệu nhất quán.

### MSR — Missed-Severe Ratio (severity ≤ 2; n_severe = 36,774)

| Biến thể BM25 | Ca nặng bỏ sót | MSR | Hit@1 |
|---|---|---|---|
| keyword_text | 576 | **1.57%** | 98.47% |
| keyword_text+description | 439 | **1.19%** | 98.78% |

`description` giảm bỏ sót bệnh nặng ~24% tương đối. **Toàn bộ** ca bỏ sót tập
trung ở nhóm tim mạch: Unstable angina (294 ca), Myocarditis (100), Stable angina
(43) — đây là phát hiện đáng đưa vào Thảo luận/Hạn chế.

### Bootstrap 95% CI cho Hit@1 (B=1000, seed=42, n=132,448)

| Biến thể | Hit@1 | CI 95% |
|---|---|---|
| keyword_text | 98.47% | [98.40%, 98.54%] |
| keyword_text+description | 98.78% | [98.72%, 98.84%] |

Hai khoảng **không giao nhau** → lợi ích của `description` có ý nghĩa thống kê.

### Chưa tính được từ dữ liệu hiện có (cần per-case)

- **NDCG@5** và **ICD-10 chapter/block Hit@1**: cần file xuất *bệnh dự đoán ở
  mỗi ca* (top-k per case), file summary hiện chỉ có tổng hợp per-disease. Đã ghi
  công thức sẵn trong `tab_qa_filled.tex`; xin Tú/Thương xuất per-case từ
  `eval_retrieval.py` là tính được ngay.

---

## 2. Điểm cần xử lý trong báo cáo (ưu tiên giảm dần)

1. **Lệch cỡ mẫu live.** sec07 mục đối chiếu dùng "mẫu 5.000, seed 13", nhưng
   `live_eval_latest.json` là full run n=132,448 (26/06). → Chốt bản nào là số
   cuối; điền `tab:livefull` từ file full và chỉnh câu chữ mục đối chiếu.
2. **Số live full khác số 5k** (BM25 98.65 vs 98.88; Hybrid 92.30 vs 92.50;
   Dense 79.54). Khác do cỡ mẫu — phải ghi rõ kẻo bị coi là mâu thuẫn.
3. **Dense live (79.54%) < Dense offline (83.11%)** do query-embed legacy. Đã
   chú thích trong sec08 (C); đảm bảo sec07 cũng nói rõ.
4. **Dòng "+Reranker (A4)"** trong tab:livefull: xác nhận có số chưa, hay để Phase 2.

---

## 3. Checklist rà soát cuối (2 ngày cuối)

### Số liệu
- [ ] tab:livefull điền xong, kèm ngày chạy + seed + Δ vs offline.
- [ ] Δ description trùng khít sec07/sec08: +1.17 / +0.78 / +0.31.
- [ ] Mọi con số kèm n và làm tròn 2 chữ số thập phân.
- [ ] Phép trừ "điểm %" đúng (98.78−91.95=6.83; 98.78−84.28=14.50).

### Thuật ngữ
- [ ] bge-small-en-v1.5 (embed) vs bge-reranker-base (rerank) không lẫn.
- [ ] Severity "1–5, 1 nặng nhất" nhất quán; MSR dùng ≤2.
- [ ] "Hybrid-RRF" có gạch nối toàn báo cáo.
- [ ] ICD-10 không còn "J17" sót (đã sửa → J18).

### LaTeX
- [ ] Không có `??`: tab:offline, tab:livevsoffline, tab:livefull, tab:qa,
      tab:msr, fig:bar đều resolve.
- [ ] `\cite{ddxplus2022}` resolve (kiểm tra .bib).
- [ ] Caption mỗi bảng ghi nguồn + n.

### Thể thức & chính tả
- [ ] Dấu số: ngăn nghìn `132{,}448`, thập phân `98.78`.
- [ ] "điểm %" (hiệu số) vs "%" đúng chỗ.
- [ ] Disclaimer "không phải công cụ chẩn đoán lâm sàng" có mặt.
- [ ] Chính tả tiếng Việt; tên thành viên viết hoa nhất quán.
- [ ] Hình OpenSearch Dashboards (sec06) đã được bổ sung.

---
**Mốc:** push sec08 + tab:qa trước 28/06; QA toàn báo cáo 2 ngày cuối, ưu tiên
mục 2.1 (lệch cỡ mẫu) trước.
