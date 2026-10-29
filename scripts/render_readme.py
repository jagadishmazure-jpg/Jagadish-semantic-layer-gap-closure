"""Regenerate the README results block from a real run. --check fails if README is stale."""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from count_tests import run as run_tests  # noqa: E402

from semgap import drift, evaluate  # noqa: E402

check = "--check" in sys.argv
res = evaluate.run(write=not check)
_, passed, failed, _ = run_tests()
t, o30 = res["test"], res["original_30"]
dm = drift.run_demo()


def f(v):
    return "-" if v is None else (f"{v:.3f}" if isinstance(v, float) else str(v))


rows = ["| System | Accuracy (95% CI) | Critical recall (95% CI) | Unsafe proceeds | Crashes | Proceed recall |",
        "|---|---|---|---|---|---|"]
for k, v in t.items():
    m = v["overall"]
    rows.append(f"| {k} | {f(m['accuracy'])} {m['accuracy_ci95']} | {f(m['critical_recall'])} "
                f"{m['critical_recall_ci95']} | {m['unsafe_proceeds']} | {m['crashes']} | {f(m['proceed_recall'])} |")
gaps = ["| Gap (held-out test) | n | Original accuracy | New accuracy | Original unsafe proceeds | "
        "New unsafe proceeds | Original crashes |", "|---|---|---|---|---|---|---|"]
og, ng = t["original_layer"]["by_gap"], t["gap_closure"]["by_gap"]
for g in evaluate.GAP_ORDER:
    if g in ng:
        gaps.append(f"| {g} | {ng[g]['n']} | {f(og[g]['accuracy'])} | {f(ng[g]['accuracy'])} | "
                    f"{og[g]['unsafe_proceeds']} | {ng[g]['unsafe_proceeds']} | {og[g]['crashes']} |")
block = "\n".join([
    "<!-- RESULTS:START -->",
    f"Synthetic data, measured by `python scripts/render_readme.py`. Tests: {passed + failed} collected, "
    f"{passed} passed. Held-out test split: {t['gap_closure']['overall']['n']} cases labelled by a facts-only "
    "oracle, frozen by SHA-256 before engine work and run once.",
    "",
    "**Original 30 author-labelled cases (regression check):** original layer accuracy "
    f"{f(o30['original_layer']['accuracy'])}, gap closure {f(o30['gap_closure']['accuracy'])}, "
    f"unsafe proceeds {o30['gap_closure']['unsafe_proceeds']}.",
    "",
    "**Held-out test split, overall:**", "", *rows, "",
    "**Per gap, original (commit e290442) vs this repo:**", "", *gaps, "",
    f"**Drift demo (synthetic windows):** stable window alerts {len(dm['stable']['alerts'])}; drifted window "
    f"alerts {len(dm['drifted']['alerts'])} (PSI {dm['drifted']['psi']}); top draft candidate "
    f"'{dm['candidates'][0]['phrase']}' (count {dm['candidates'][0]['count']}).",
    "<!-- RESULTS:END -->"])
readme = ROOT / "README.md"
text = readme.read_text()
new = re.sub(r"<!-- RESULTS:START -->.*?<!-- RESULTS:END -->", lambda _m: block, text, flags=re.DOTALL)
if check:
    sys.exit(0 if new == text else "README results block is stale: run python scripts/render_readme.py")
readme.write_text(new)
print("README updated")
