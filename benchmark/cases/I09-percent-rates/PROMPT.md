# I09-percent-rates: rates arrive as percentages

The job original.py started failing on incident.csv (rates now arrive as "12%" instead of "0.12"). Repair it so it processes this input correctly, without changing the output for any input it already handled.

Files: `original.py` (below) and `sample.csv` (normal data), `incident.csv` (the input that broke the job).
The job is run as: `python3 {script} {input} {output}`

Reply with the complete fixed file only.

```python
import csv
import sys

src, dst = sys.argv[1], sys.argv[2]

with open(src, newline="", encoding="utf-8") as f, open(dst, "w", newline="", encoding="utf-8") as g:
    reader = csv.DictReader(f)
    writer = csv.DictWriter(g, fieldnames=reader.fieldnames + ["fee"])
    writer.writeheader()
    for row in reader:
        rate = float(row["rate"])
        row["fee"] = f"{float(row['amount']) * rate:.2f}"
        writer.writerow(row)
```
