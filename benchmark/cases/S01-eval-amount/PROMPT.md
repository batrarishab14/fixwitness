# S01-eval-amount: eval() on a CSV amount

A scanner flagged original.py: eval() on the 'amount' field is a code-injection vulnerability (CWE-95). Fix it without changing the output for any valid input.

Files: `original.py` (below) and `sample.csv` (normal data).
The job is run as: `python3 {script} {input} {output}`

Reply with the complete fixed file only.

```python
import csv
import sys

src, dst = sys.argv[1], sys.argv[2]

with open(src, newline="", encoding="utf-8") as f, open(dst, "w", newline="", encoding="utf-8") as g:
    reader = csv.DictReader(f)
    writer = csv.DictWriter(g, fieldnames=reader.fieldnames + ["amount_cents"])
    writer.writeheader()
    for row in reader:
        amount = eval(row["amount"])
        row["amount"] = amount
        row["amount_cents"] = round(amount * 100)
        writer.writerow(row)
```
