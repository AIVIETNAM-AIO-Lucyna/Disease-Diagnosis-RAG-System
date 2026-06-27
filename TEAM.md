# Phân công & Đóng góp — Nhóm Med_Pharm_Bio_Nexus

> Dự án **Disease-Diagnosis-RAG-System** (DDXPlus). Tài liệu này ghi nhận đóng góp theo chuẩn **CRediT** (Contributor Roles Taxonomy), **dựa trên bằng chứng kiểm chứng được**: lịch sử commit/PR trên GitHub, biểu mẫu & nhật ký trên Notion, biên bản họp nhóm. Mục tiêu: minh bạch, khách quan, công bằng. Phạm vi: **Phase 1**.

## 1. Nguyên tắc ghi nhận

- **Dựa trên dữ liệu, không dựa trên cảm tính.** Mỗi đóng góp truy được về commit/PR/issue hoặc trang Notion.
- **Tách hai trục độc lập:** (A) _Thực hiện kỹ thuật_ và (B) _Viết & biên tập báo cáo_. Một người có thể mạnh ở trục này, hạn chế ở trục kia — cả hai đều được ghi nhận riêng để công bằng.
- **Tôn trọng & trung lập.** Bảng chỉ nêu _việc đã làm_, không đánh giá thái độ hay phán xét cá nhân.

## 2. Vai trò tổng hợp báo cáo (Report Integrator)

Qua biểu quyết nội bộ, nhóm thống nhất:

- **Report Integrator (chính):** Nguyễn Văn Thương — tổng hợp, biên tập, đảm bảo tính nhất quán của báo cáo.
- **Backup Integrator:** các thành viên đã chọn "sẵn sàng làm Integrator phụ/backup".
- Mỗi thành viên chịu trách nhiệm **mục được giao** và **deadline nộp phần** trên Jira/Notion.

## 3. Bảng đóng góp (CRediT — Phase 1)

| Thành viên                | Vai trò                            | (A) Đóng góp thực hiện — có dẫn chứng                                                                                                                                                                                                                                             | (B) Viết & biên tập báo cáo                                                       |
| ------------------------- | ---------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| **Nguyễn Văn Thương**     | AI Engineer (Model) / Quản lý nhóm | Rà soát y khoa 49 bệnh; chuẩn hoá ICD-10 + audit (`scripts/build_icd10_reference.py`, `data/kb/icd10_audit.*`); thiết kế & chạy harness đánh giá offline Python thuần (EXP-01/EXP-02, n=132.448); PR #6 (regenerate KB), PR #8 (eval harness); điều phối nhóm                     | **Chủ trì viết & tổng hợp** (Report Integrator)                                   |
| **Nguyễn Minh Tú**        | AI Engineer (Pipeline)             | Pipeline RAG; ingest & index OpenSearch (PR #9, #12 — batch ingestion, `keyword_text`, embeddings); re-ranker cross-encoder (PR #10); **chạy eval live OpenSearch đầy đủ (n=132.448, 26/06/2026, commit b8e905a)**; chỉ ra khác biệt prefix BGE giữa offline/production cho dense | Đóng góp nội dung pipeline & kết quả live                                         |
| **Nguyễn Thị Diễm Hương** | QA / Reviewer                      | Thiết kế & đo chỉ số QA: Tier-1.5 (ICD-10 chapter/block Hit@1), MSR (severity ≤ 2), NDCG@5, bootstrap CI                                                                                                                                                                          | Viết mục Ablation/QA; review & hiệu đính toàn báo cáo                             |
| **Vương Đình Minh Trí**   | Tech Leader                        | Kiến trúc & DevOps; mapping ingest OpenSearch; tech-lead review các PR                                                                                                                                                                                                            | Đóng góp nội dung kiến trúc/DevOps                                                |
| **Hoàng Phước Nguyên**    | AI Engineer (Data)                 | KB v1: 49 thẻ bệnh, ICD-10 làm ID, severity 1–5; hàm chuẩn hoá triệu chứng dùng chung KB/query; khử trùng eval set (test 101, validate 75); nhánh `feat/ddxplus-kb`                                                                                                               | Cung cấp tư liệu KB cho mục Dữ liệu; _không tham gia trực tiếp khâu viết báo cáo_ |

## 4. Phân công viết báo cáo Phase 1 (gộp theo người phụ trách)

Báo cáo được chia thành các file `report/sections/secNN_*.tex`; mỗi người viết phần của mình (Overleaf hoặc công cụ bất kỳ), commit lên GitHub; CI (`latex.yml`) tự build `main.pdf`. Không sửa file `.cls`.

| Người phụ trách           | Cụm nội dung (section)                                                                                                                                                                                                      | Deadline nội bộ        |
| ------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------- |
| **Nguyễn Văn Thương**     | sec01 Tóm tắt, sec02 Giới thiệu, sec03 Phát biểu bài toán, sec04 Related work, sec09 Thảo luận, sec10 Hạn chế, sec11 Phase 2, sec12 Team & vận hành, sec14 Kết luận; phần Dữ liệu/KB trong sec05/sec06 (chấp bút hộ Nguyên) | 28/06                  |
| **Nguyễn Minh Tú**        | sec05 Phương pháp (kiến trúc RAG, pipeline truy hồi, re-ranking), sec06 Thí nghiệm (thiết lập & chạy eval), sec07 Kết quả (số liệu live OpenSearch — xác nhận số chốt)                                                      | 28/06                  |
| **Vương Đình Minh Trí**   | sec05 (bổ sung kiến trúc hệ thống & ingest), sec13 Tái lập & triển khai (môi trường, cấu hình, DevOps)                                                                                                                      | 28/06                  |
| **Nguyễn Thị Diễm Hương** | sec08 Ablation; QA toàn báo cáo (soát số liệu, thuật ngữ, chính tả, trích dẫn); điền Bảng QA (NDCG@5, Tier-1.5, MSR, CI)                                                                                                    | Viết 28/06; QA 29/06   |
| **Hoàng Phước Nguyên**    | Cung cấp & xác nhận tư liệu KB cho phần Dữ liệu (sec05/sec06); không trực tiếp chấp bút                                                                                                                                     | Xác nhận tư liệu 28/06 |

**Mốc chung:** push phần viết trước **28/06**; QA & ráp tổng (Integrator) **29/06**; rà soát lần cuối & nộp **30/06**.

## 5. Ghi chú minh bạch

- Bảng phản ánh **đóng góp Phase 1**; sẽ cập nhật ở các phase sau.
- Lịch sử Git (PR #1–#14) và Notion (Experiment & Logs, các biểu mẫu) là **nguồn tham chiếu gốc**; mọi thành viên có thể đối chiếu.
- Trục (A) và (B) được tách để đảm bảo **công bằng hai chiều**: ghi nhận đầy đủ phần kỹ thuật kể cả khi một thành viên không tham gia khâu viết, và ngược lại.
- Mọi điều chỉnh về phân công/ghi nhận nên thảo luận trong buổi **retro nội bộ**, không chỉnh trực tiếp gây tranh cãi trên tài liệu công khai.
