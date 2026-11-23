# label: wrong
# pattern: over-broad normalisation: regex clean-up drops minus signs and exponents
import csv
import re
import sys

src, dst = sys.argv[1], sys.argv[2]

with open(src, newline="", encoding="utf-8") as f, open(dst, "w", newline="", encoding="utf-8") as g:
    reader = csv.DictReader(f)
    writer = csv.DictWriter(g, fieldnames=reader.fieldnames + ["fee"])
    writer.writeheader()
    for row in reader:
        rate = float(re.sub(r"[^0-9.]", "", row["rate"])) / (100 if "%" in row["rate"] else 1)
        row["fee"] = f"{float(row['amount']) * rate:.2f}"
        writer.writerow(row)
