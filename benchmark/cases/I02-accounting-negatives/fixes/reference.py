# label: correct
# pattern: (x) means -x; everything else parsed as before
import csv
import sys

src, dst = sys.argv[1], sys.argv[2]
import re

PARENS = re.compile(r"\s*\(\s*([0-9.]+)\s*\)\s*")


def parse(s):
    m = PARENS.fullmatch(s)
    return -float(m.group(1)) if m else float(s)


with open(src, newline="", encoding="utf-8") as f, open(dst, "w", newline="", encoding="utf-8") as g:
    reader = csv.DictReader(f)
    writer = csv.DictWriter(g, fieldnames=reader.fieldnames + ["amount_cents"])
    writer.writeheader()
    for row in reader:
        amount = parse(row["amount"])
        row["amount_cents"] = round(amount * 100)
        writer.writerow(row)
