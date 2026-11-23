# label: correct
# pattern: stop evaluating templates; data is treated as text
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
        row["label"] = row["label"].strip()
        writer.writerow(row)
