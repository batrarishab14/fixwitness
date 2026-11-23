import csv
import sys

src, dst = sys.argv[1], sys.argv[2]

with open(src, newline="", encoding="utf-8") as f, open(dst, "w", newline="", encoding="utf-8") as g:
    reader = csv.DictReader(f)
    writer = csv.DictWriter(g, fieldnames=reader.fieldnames + ["per_unit"])
    writer.writeheader()
    for row in reader:
        row["per_unit"] = int(int(row["total_cents"]) / int(row["units"]))
        writer.writerow(row)
