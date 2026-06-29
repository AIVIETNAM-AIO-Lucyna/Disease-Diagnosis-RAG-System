# .latexmkrc -- dieu khien trinh build latexmk (ke ca tren GitHub Actions / xu-cheng/latex-action).
# Bao cao dung biblatex voi backend=bibtex (khai bao trong ai_conquer2026.cls).
# File nay KHONG sua .cls.

$pdf_mode   = 1;   # dung pdflatex de tao PDF
$bibtex_use = 2;   # LUON chay bibtex (biblatex backend=bibtex) -> dung muc Tai lieu tham khao
$max_repeat = 7;   # rerun du nhieu luot de giai het tham chieu cheo (\ref het "??")

# Luu y: KHONG dung $force_mode = 1, de loi that (vd ky tu hong) bao FAIL ngay,
# tranh che giau loi noi dung.

# Tuy chon: don file phu sinh khi chay `latexmk -c`
$clean_ext .= ' bbl run.xml bcf';
