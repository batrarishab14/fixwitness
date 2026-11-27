"""Rebuild the OpenBB Yang-Zhang case from a clone of OpenBB (their code is AGPL, so it is not copied here).

    git clone https://github.com/OpenBB-finance/OpenBB && python build.py OpenBB OUTDIR
    fixwitness check --before OUTDIR/before.py --after OUTDIR/after.py --sample OUTDIR/sample.csv --no-attacks

before.py is `yang_zhang` at c6d097b27~1 (the bug), after.py at c6d097b27 (OpenBB PR #7807, the fix).
"""
import random
import re
import subprocess
import sys
from pathlib import Path

repo, out = sys.argv[1], Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
F = "openbb_platform/extensions/technical/openbb_technical/helpers.py"
HEAD = "import sys\nfrom typing import Optional\nfrom warnings import warn\nimport pandas as pd\nDataFrame = pd.DataFrame\n"
# window=2: fixwitness varies the first 3 rows of the sample, so a longer window would give no output at all.
TAIL = '''

if __name__ == "__main__":
    df = pd.read_csv(sys.argv[1])
    out = yang_zhang(df, window=2, clean=True)
    out.rename("yang_zhang").reset_index(drop=True).to_frame().to_csv(sys.argv[2], index=False)
'''
for name, rev in (("before.py", "c6d097b27~1"), ("after.py", "c6d097b27")):
    src = subprocess.check_output(["git", "-C", repo, "show", f"{rev}:{F}"], text=True)
    (out / name).write_text(HEAD + re.search(r"^def yang_zhang\(.*?(?=^def )", src, re.S | re.M).group(0) + TAIL)
random.seed(3)
p, rows = 100.0, ["open,high,low,close"]
for _ in range(20):
    o = p * (1 + random.uniform(-.01, .01)); c = o * (1 + random.uniform(-.02, .02))
    h = max(o, c) * (1 + random.uniform(0, .01)); l = min(o, c) * (1 - random.uniform(0, .01)); p = c
    rows.append(f"{o:.2f},{h:.2f},{l:.2f},{c:.2f}")
(out / "sample.csv").write_text("\n".join(rows) + "\n")
