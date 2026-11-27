# label: wrong
# pattern: each amount rounded before summing instead of the total
import json
import sys

totals = {}
with open(sys.argv[1]) as f:
    for line in f:
        if not line.strip():
            continue
        e = json.loads(line)
        if e.get("status") != "paid":
            continue
        c = e["user"]["country"]
        totals[c] = totals.get(c, 0) + round(e["amount"], 2)
with open(sys.argv[2], "w") as out:
    for c in sorted(totals):
        out.write(json.dumps({"country": c, "revenue": round(totals[c], 2)}) + "\n")
