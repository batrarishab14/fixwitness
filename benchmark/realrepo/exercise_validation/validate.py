"""Run fixwitness.exercise.assess on real study candidates: the real changed model SQL (raw, not compiled)
and the real integration-test seeds (first 200 rows, as the study uses)."""
import csv, subprocess, sys, io, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
from fixwitness.exercise import assess, profile_inputs

def git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True).stdout

def models_text(repo, commit, rels):
    return "\n".join(git(repo, "show", f"{commit}:{r}") for r in rels)

def seeds(repo, commit):
    names = [n for n in git(repo, "ls-tree", "-r", "--name-only", commit, "integration_tests/seeds").split() if n.endswith(".csv")]
    out = []
    for n in names:
        text = git(repo, "show", f"{commit}:{n}")
        lines = text.splitlines()[:201]
        out.append(("\n".join(lines) + "\n").encode())
    return out

def run(repo, commit, parent):
    changed = [p for p in git(repo, "diff", "--name-only", parent, commit, "--", "models").split() if p.endswith(".sql")]
    if not changed:
        return {"note": "no .sql model changed"}
    before = "\n".join(git(repo, "show", f"{parent}:{p}") for p in changed)
    after = "\n".join(git(repo, "show", f"{commit}:{p}") for p in changed)
    whole = "\n".join(git(repo, "show", f"{c}:{p}") for c in (parent, commit)
                      for p in git(repo, "ls-tree", "-r", "--name-only", c, "models").split() if p.endswith(".sql"))
    prof = profile_inputs(seeds(repo, commit))
    r = assess(before, after, whole, prof)
    r["changed"] = changed
    return r

if __name__ == "__main__":
    repo, commit, parent = sys.argv[1:4]
    r = run(repo, commit, parent)
    print(json.dumps({k: v for k, v in r.items()}, indent=1)[:3000])
