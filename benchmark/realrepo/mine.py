"""List the candidate commits for the real-repository study from each package's CHANGELOG.

Each release in a Fivetran dbt package's CHANGELOG names its pull request and sorts its changes
under headings ("Bug Fixes", "Under the Hood", "Feature Updates", "Schema/Data Change", ...). The
pull request is one commit on the main line (squash-merged "... (#N)" or a merge commit "Merge pull
request #N"), so each release maps to one commit and its first parent. This script writes every release whose commit changes SQL in models/ or macros/, with its
headings and its text, for labelling by the rule in PROTOCOL.md. It does not run fixwitness.

    python benchmark/realrepo/mine.py CLONES_DIR > benchmark/realrepo/candidates_raw.csv
"""

from __future__ import annotations

import csv
import re
import subprocess
import sys
from pathlib import Path

BUG = re.compile(r"bug|fix", re.I)
QUIET = re.compile(r"under the hood|documentation|contributors|dependency|tests? update|quickstart|readme", re.I)


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True).stdout


def releases(text: str):
    blocks = re.split(r"^# (?=\S)", text, flags=re.M)
    for b in blocks[1:]:
        head, _, body = b.partition("\n")
        prs = sorted({int(n) for n in re.findall(r"\bPR #(\d+)", body[:600])} |
                     {int(n) for n in re.findall(r"/pull/(\d+)\)", body[:600])})
        sections = [s.strip().strip(":").strip() for s in re.findall(r"^##\s+(.+)$", body, flags=re.M)]
        yield head.strip(), prs, sections, body


def kind(sections: list[str]) -> str:
    names = [re.sub(r"[^\w/ ]", "", s).strip() for s in sections]
    bug = any(BUG.search(s) for s in names)
    other = [s for s in names if not BUG.search(s) and not QUIET.search(s)]
    if bug and not other:
        return "bugfix"
    if bug:
        return "bugfix+other"
    if not other:
        return "quiet"
    return "feature"


def main(root: Path) -> None:
    out = csv.writer(sys.stdout, lineterminator="\n")
    out.writerow(["package", "release", "pr", "commit", "parent", "date", "kind", "sections", "sql_files", "text"])
    for repo in sorted(p for p in root.iterdir() if (p / "CHANGELOG.md").is_file()):
        log = git(repo, "log", "--first-parent", "--format=%H\t%P\t%ad\t%s", "--date=short").splitlines()
        by_pr = {}
        for line in log:
            h, parents, date, subject = line.split("\t", 3)
            nums = re.findall(r"\(#(\d+)\)\s*$", subject) or re.findall(r"^Merge pull request #(\d+)\b", subject)
            for n in nums:  # squash-merged "... (#N)", or a merge commit "Merge pull request #N from ..."
                by_pr.setdefault(int(n), (h, parents.split()[0] if parents else "", date))
        for head, prs, sections, body in releases((repo / "CHANGELOG.md").read_text(encoding="utf-8")):
            if len(prs) != 1 or prs[0] not in by_pr:
                continue  # several pull requests in one release, or one not squash-merged: not one commit
            h, parent, date = by_pr[prs[0]]
            if not parent:
                continue
            files = git(repo, "diff", "--name-only", parent, h).split()
            sql = [f for f in files if f.endswith(".sql") and f.split("/")[0] in ("models", "macros")]
            if not sql:
                continue
            text = re.sub(r"\s+", " ", body).strip()[:1200]
            out.writerow([repo.name, head, prs[0], h[:12], parent[:12], date, kind(sections),
                          " | ".join(sections), len(sql), text])


if __name__ == "__main__":
    main(Path(sys.argv[1]))
