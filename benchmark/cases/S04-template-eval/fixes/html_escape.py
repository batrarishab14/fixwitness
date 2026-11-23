# label: wrong
# pattern: over-correction: HTML-escaping changes quotes and ampersands in plain text
import html
import csv
import re
import sys

src, dst = sys.argv[1], sys.argv[2]
EXPR = re.compile(r"\{\{(.*?)\}\}")

with open(src, newline="", encoding="utf-8") as f, open(dst, "w", newline="", encoding="utf-8") as g:
    reader = csv.DictReader(f)
    writer = csv.DictWriter(g, fieldnames=reader.fieldnames)
    writer.writeheader()
    for row in reader:
        row["label"] = html.escape(row["label"]).strip()
        writer.writerow(row)
