import csv
import subprocess
import sys

src, dst = sys.argv[1], sys.argv[2]

with open(src, newline="", encoding="utf-8") as f, open(dst, "w", newline="", encoding="utf-8") as g:
    reader = csv.DictReader(f)
    writer = csv.DictWriter(g, fieldnames=reader.fieldnames)
    writer.writeheader()
    for row in reader:
        out = subprocess.run(f"echo {row['region']} | tr a-z A-Z", shell=True, capture_output=True, text=True)
        row["region"] = out.stdout.rstrip("\n")
        writer.writerow(row)
