# .latexmkrc -- dieu khien trinh build latexmk (ke ca tren GitHub Actions / xu-cheng/latex-action).
# Bao cao dung biblatex voi backend=bibtex (khai bao trong ai_conquer2026.cls).
# File nay KHONG sua .cls; chi dam bao build chay DU so luot va chay bibtex.

$pdf_mode   = 1;   # dung pdflatex de tao PDF
$bibtex_use = 2;   # LUON chay bibtex (biblatex backend=bibtex) -> dung muc Tai lieu tham khao
$max_repeat = 7;   # cho phep rerun du nhieu luot de giai het tham chieu cheo (\ref het "??")
$force_mode = 1;   # tiep tuc qua canh bao, tranh latexmk thoat non-zero giua chung tren CI

# Tuy chon: don file phu sinh khi chay `latexmk -c`
$clean_ext .= ' bbl run.xml bcf';
