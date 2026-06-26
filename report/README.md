# Báo cáo Phase 1 — Disease-Diagnosis-RAG-System

Thư mục `report/` chứa mã nguồn LaTeX của báo cáo Phase 1 (nhóm Med_Pharm_Bio_Nexus).

## Biên dịch
- **Overleaf:** import toàn bộ thư mục, đặt `main.tex` làm tài liệu chính, compiler **pdfLaTeX**, chạy 2 lần (có bibtex).
- **Local:** `latexmk -pdf -shell-escape main.tex` trong `report/`.

## Cấu trúc
- `main.tex` — tài liệu chính (preamble, \input các section, phụ lục + bảng đóng góp).
- `sections/` — các mục sec01..sec14.
- `ai_conquer2026.cls` — lớp tài liệu (KHÔNG sửa).
- `Figures/` — hình ảnh.

Xem `../TEAM.md` để biết phân công & đóng góp.
