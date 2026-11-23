# label: wrong
# pattern: key change: casefold() turns 'Straße' into 'strasse', breaking joins on existing keys
import csv
import sys

src, dst = sys.argv[1], sys.argv[2]

with open(src, newline="", encoding="utf-8") as f, open(dst, "w", newline="", encoding="utf-8") as g:
    reader = csv.DictReader(f)
    writer = csv.DictWriter(g, fieldnames=reader.fieldnames + ["city_key"])
    writer.writeheader()
    for row in reader:
        row["city_key"] = row["city"].strip().casefold()
        writer.writerow(row)
