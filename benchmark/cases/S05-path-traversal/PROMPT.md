# S05-path-traversal: file name built from a customer field

A scanner flagged original.py: the 'customer' field is used to build a file path, which allows path traversal (CWE-22). Fix it without changing the output for any valid input.

Files: `original.py` (below) and `sample.csv` (normal data).
The job is run as: `python3 {script} {input} {output}`

Reply with the complete fixed file only.

```python
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
        path = os.path.join("statements", row["customer"] + ".txt")
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(row["amount"] + "\n")
        row["statement"] = path
        writer.writerow(row)
```
