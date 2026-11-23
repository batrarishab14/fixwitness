# label: correct
# pattern: no shell; reproduce echo's whitespace collapsing and tr's ASCII-only upper-casing
import string
import csv
import subprocess
import sys

src, dst = sys.argv[1], sys.argv[2]

with open(src, newline="", encoding="utf-8") as f, open(dst, "w", newline="", encoding="utf-8") as g:
    reader = csv.DictReader(f)
    writer = csv.DictWriter(g, fieldnames=reader.fieldnames)
    writer.writeheader()
    for row in reader:
        upper = str.maketrans(string.ascii_lowercase, string.ascii_uppercase)
        row["region"] = " ".join(row["region"].split()).translate(upper)
        writer.writerow(row)
