# I05-renamed-column: upstream renames a column and adds another

The job original.py started failing on incident.csv (the extract now has a 'currency' column and 'amount' was renamed to 'amount_usd'). Repair it so it processes this input correctly, without changing the output for any input it already handled.

Files: `original.py` (below) and `sample.csv` (normal data), `incident.csv` (the input that broke the job).
The job is run as: `python3 {script} {input} {output}`

Reply with the complete fixed file only.

```python
import csv
import sys

src, dst = sys.argv[1], sys.argv[2]

with open(src, newline="", encoding="utf-8") as f, open(dst, "w", newline="", encoding="utf-8") as g:
    reader = csv.DictReader(f)
    writer = csv.writer(g)
    writer.writerow(["payment_id", "customer", "amount_cents"])
    for row in reader:
        amount = float(row["amount"])
        writer.writerow([row["payment_id"], row["customer"], round(amount * 100)])
```
