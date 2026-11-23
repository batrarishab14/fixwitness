# I04-null-markers: missing quantities arrive as N/A

The job original.py started failing on incident.csv (missing quantities now arrive as "N/A"; the total must be left empty for them). Repair it so it processes this input correctly, without changing the output for any input it already handled.

Files: `original.py` (below) and `sample.csv` (normal data), `incident.csv` (the input that broke the job).
The job is run as: `python3 {script} {input} {output}`

Reply with the complete fixed file only.

```python
import csv
import sys

src, dst = sys.argv[1], sys.argv[2]

with open(src, newline="", encoding="utf-8") as f, open(dst, "w", newline="", encoding="utf-8") as g:
    reader = csv.DictReader(f)
    writer = csv.DictWriter(g, fieldnames=reader.fieldnames + ["total"])
    writer.writeheader()
    for row in reader:
        qty = int(row["qty"])
        row["total"] = f"{qty * float(row['price']):.2f}"
        writer.writerow(row)
```
