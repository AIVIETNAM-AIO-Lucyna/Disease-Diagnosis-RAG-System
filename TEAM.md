# Phân công & Đóng góp — Nhóm Med_Pharm_Bio_Nexus

> Dự án **Disease-Diagnosis-RAG-System** (DDXPlus). Tài liệu này ghi nhận đóng góp theo chuẩn **CRediT** (Contributor Roles Taxonomy), **dựa trên bằng chứng kiểm chứng được**: lịch sử commit/PR trên GitHub, biểu mẫu & nhật ký trên Notion, biên bản họp nhóm. Mục tiêu: minh bạch, khách quan, công bằng. Phạm vi: **Phase 1**.

## 1. Nguyên tắc ghi nhận

- **Dựa trên dữ liệu, không dựa trên cảm tính.** Mỗi đóng góp truy được về commit/PR/issue hoặc trang Notion.
- **Tách hai trục độc lập:** (A) *Thực hiện kỹ thuật* và (B) *Viết & biên tập báo cáo*. Một người có thể mạnh ở trục này, hạn chế ở trục kia — cả hai đều được ghi nhận riêng để công bằng.
- **Tôn trọng & trung lập.** Bảng chỉ nêu *việc đã làm*, không đánh giá thái độ hay phán xét cá nhân.

## 2. Vai trò tổng hợp báo cáo (Report Integrator)

Qua biểu quyết nội bộ, nhóm thống nhất:

- **Report Integrator (chính):** Nguyễn Văn Thương — tổng hợp, biên tập, đảm bảo tính nhất quán của báo cáo.
- **Backup Integrator:** các thành viên đã chọn "sẵn sàng làm Integrator phụ/backup".
- Mỗi thành viên chịu trách nhiệm **mục được giao** và **deadline nộp phần** trên Jira/Notion.

## 3. Bảng đóng góp (CRediT — Phase 1)

| Thành viên | Vai trò | (A) Đóng góp thực hiện — có dẫn chứng | (B) Viết & biên tập báo cáo |
|---|---|---|---|
| **Nguyễn Văn Thương** | AI Engineer (Model) / Quản lý nhóm | Rà soát y khoa 49 bệnh; chuẩn hoá ICD-10 + audit (`scripts/build_icd10_reference.py`, `data/kb/icd10_audit.*`); thiết kế & chạy harness đánh giá offline Python thuần (EXP-01/EXP-02, n=132.448); PR #6 (regenerate KB), PR #8 (eval harness); điều phối nhóm | **Chủ trì viết & tổng hợp** (Report Integrator) |
| **Nguyễn Minh Tú** | AI Engineer (Pipeline) | Pipeline RAG; ingest & index OpenSearch (PR #9, #12 — batch ingestion, `keyword_text`, embeddings); re-ranker cross-encoder (PR #10); chạy eval live OpenSearch (mẫu 5k seed 13; full 132k) | Đóng góp nội dung pipeline & kết quả live |
| **Nguyễn Thị Diễm Hương** | QA / Reviewer | Thiết kế & đo chỉ số QA: Tier-1.5 (ICD-10 chapter/block Hit@1), MSR (severity ≤ 2), NDCG@5, bootstrap CI | Viết mục Kết quả/QA; review & hiệu đính |
| **Vương Đình Minh Trí** | Tech Leader | Kiến trúc & DevOps; mapping ingest OpenSearch; tech-lead review các PR | Đóng góp nội dung kiến trúc/DevOps |
| **Hoàng Phước Nguyên** | AI Engineer (Data) | KB v1: 49 thẻ bệnh, ICD-10 làm ID, severity 1–5; hàm chuẩn hoá triệu chứng dùng chung KB/query; khử trùng eval set (test 101, validate 75); nhánh `feat/ddxplus-kb` | Cung cấp tư liệu KB cho mục Dữ liệu; *không tham gia trực tiếp khâu viết báo cáo* |

## 4. Ghi chú minh bạch

- Bảng phản ánh **đóng góp Phase 1**; sẽ cập nhật ở các phase sau.
- Lịch sử Git (PR #1–#12) và Notion (Experiment & Logs, các biểu mẫu) là **nguồn tham chiếu gốc**; mọi thành viên có thể đối chiếu.
- Trục (A) và (B) được tách để đảm bảo **công bằng hai chiều**: ghi nhận đầy đủ phần kỹ thuật kể cả khi một thành viên không tham gia khâu viết, và ngược lại.
- Mọi điều chỉnh về phân công/ghi nhận nên thảo luận trong buổi **retro nội bộ**, không chỉnh trực tiếp gây tranh cãi trên tài liệu công khai.
