# label: correct
# pattern: alternative fix: keep only the last path component
import csv
import os
import sys

src, dst = sys.argv[1], sys.argv[2]
os.makedirs("statements", exist_ok=True)

with open(src, newline="", encoding="utf-8") as f, open(dst, "w", newline="", encoding="utf-8") as g:
    reader = csv.DictReader(f)
    writer = csv.DictWriter(g, fieldnames=reader.fieldnames + ["statement"])
    writer.writeheader()
    for row in reader:
        path = os.path.join("statements", os.path.basename(row["customer"]) + ".txt")
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(row["amount"] + "\n")
        row["statement"] = path
        writer.writerow(row)
