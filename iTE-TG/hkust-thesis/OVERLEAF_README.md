# Overleaf compilation

1. Upload the contents of this folder to a new Overleaf project.
2. Set `mythesis.tex` as the main document.
3. Set the compiler to XeLaTeX.
4. The included `hkustthesis.cls` uses BibTeX as the bibliography backend for
   compatibility with the present local build and Overleaf.

Before submission, check the `\hkustsetup` block in `mythesis.tex`, especially:

- degree (`phd` or `mphil`);
- official school/department/program wording;
- submission and defence dates;
- department head and examination committee.

The authorization and signature pages are commented out until these fields are
complete. Uncomment `\authorization` and `\signaturepage` afterwards.
