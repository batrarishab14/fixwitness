# label: correct
# pattern: read the file exactly as before; only if that fails, read it again with ';'
import csv
import io
import sys

src, dst = sys.argv[1], sys.argv[2]


def convert(text, delimiter):
    out = io.StringIO(newline="")
    writer = csv.writer(out)
    writer.writerow(["payment_id", "customer", "amount_cents"])
    for row in csv.DictReader(io.StringIO(text, newline=""), delimiter=delimiter):
        amount = float(row["amount"])
        writer.writerow([row["payment_id"], row["customer"], round(amount * 100)])
    return out.getvalue()


with open(src, newline="", encoding="utf-8") as f:
    text = f.read()
try:
    result = convert(text, ",")
except Exception:
    result = convert(text, ";")
with open(dst, "w", newline="", encoding="utf-8") as g:
    g.write(result)
