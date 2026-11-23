# label: wrong
# pattern: semantic drift: Unicode-aware upper() and no whitespace collapsing
import csv
import subprocess
import sys

src, dst = sys.argv[1], sys.argv[2]

with open(src, newline="", encoding="utf-8") as f, open(dst, "w", newline="", encoding="utf-8") as g:
    reader = csv.DictReader(f)
    writer = csv.DictWriter(g, fieldnames=reader.fieldnames)
    writer.writeheader()
    for row in reader:
        row["region"] = row["region"].upper()
        writer.writerow(row)
