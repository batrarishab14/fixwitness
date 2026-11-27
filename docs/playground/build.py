"""Write standalone.html (a full HTML document for GitHub Pages) from index.html (the artifact source)."""
from pathlib import Path

here = Path(__file__).parent
src = (here / "index.html").read_text(encoding="utf-8")
head, _, body = src.partition("</style>")
(here / "standalone.html").write_text(
    "<!doctype html>\n<!-- Generated from index.html: python3 docs/playground/build.py -->\n"
    '<html lang="en"><head><meta charset="utf-8">'
    '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n'
    "<style>[hidden]{display:none!important}</style>\n" + head + "</style>\n</head><body>" + body + "</body></html>\n",
    encoding="utf-8")
