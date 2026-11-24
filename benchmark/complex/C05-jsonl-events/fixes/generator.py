# label: correct
# pattern: a defaultdict and a generator
import json
import sys
from collections import defaultdict


def main(src, dst):
    totals = defaultdict(int)
    with open(src) as f:
        for e in (json.loads(line) for line in f if line.strip()):
            if e.get("status") == "paid":
                totals[e["user"]["country"]] += e["amount"]
    with open(dst, "w") as out:
        out.writelines(json.dumps({"country": c, "revenue": round(v, 2)}) + "\n" for c, v in sorted(totals.items()))


main(*sys.argv[1:3])
