# S04-template-eval: home-made {{ }} templates evaluated with eval()

A scanner flagged original.py: '{{ }}' expressions inside the 'label' field are evaluated with eval() (template injection). Fix it without changing the output for any valid input.

Files: `original.py` (below) and `sample.csv` (normal data).
The job is run as: `python3 {script} {input} {output}`

Reply with the complete fixed file only.

```python
import csv
import re
import sys

src, dst = sys.argv[1], sys.argv[2]
EXPR = re.compile(r"\{\{(.*?)\}\}")

with open(src, newline="", encoding="utf-8") as f, open(dst, "w", newline="", encoding="utf-8") as g:
    reader = csv.DictReader(f)
    writer = csv.DictWriter(g, fieldnames=reader.fieldnames)
    writer.writeheader()
    for row in reader:
        row["label"] = EXPR.sub(lambda m: str(eval(m.group(1))), row["label"]).strip()
        writer.writerow(row)
```
