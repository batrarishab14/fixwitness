# label: wrong
# pattern: e.get('status') replaced by e['status'] (a record without the key now fails)
import json
import sys

totals = {}
with open(sys.argv[1]) as f:
    for line in f:
        if not line.strip():
            continue
        e = json.loads(line)
        if e["status"] != "paid":
            continue
        c = e["user"]["country"]
        totals[c] = totals.get(c, 0) + e["amount"]
with open(sys.argv[2], "w") as out:
    for c in sorted(totals):
        out.write(json.dumps({"country": c, "revenue": round(totals[c], 2)}) + "\n")
