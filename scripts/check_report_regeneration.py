#!/usr/bin/env python3
"""Prove that regenerating a report moved no result.

    python scripts/check_report_regeneration.py [--before-ref GIT_REF] [--markdown OUT.md]

"Before" is a git commit, not a copy somebody made: the reports and the result JSONs are
tracked, so `git show <ref>:<path>` is the record of what they were. The default ref is
the last commit before the 2026-09-21 generator fixes. Two result files are not tracked
(CSV is git-ignored); their SHA-256, taken before anything was regenerated, is recorded in
`UNTRACKED_SHA256` below.
Three checks per milestone, each of which can fail:

  A. RESULT FILES. Every leaf of every before-`summary.json` must exist in today's file
     with an IDENTICAL value (floats compared exactly, NaN == NaN). Keys may be ADDED;
     every added key is listed. A key may be RENAMED only if it is declared in `RENAMES`
     below with its reason, and its values must then be identical under the new name.
     A short list of `PRESENTATION_KEYS` (the list of figure files) is exempt and listed.
     Files that a report-only rebuild must not touch at all are compared by SHA-256.
  B. REPORT TABLES vs BEFORE. Every numeric token of every markdown table cell of the
     before-report must appear among the numeric tokens of today's report. Anything that
     does not is listed and must be explained in `EXPECTED_GONE` (a superseded cell that
     is still quoted elsewhere is checked to be quoted elsewhere).
  C. REPORT TABLES vs summary.json. Every numeric token in today's table cells must be
     the rendering of some number in today's result files (tried at the formats the
     generators use). Tokens that are not are listed as unexplained.

Evaluates nothing, imports nothing from `src/aether`, and writes nothing but its report.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BEFORE_REF = "eac22c7"      # "feat: M6 adaptive-fidelity study", HEAD before the fixes

UNTRACKED_SHA256 = {        # taken 2026-09-21 before any report was regenerated
    "M7/M7-UQ-20260920T233048Z/comparison.csv":
        "60a724616ece4db42f901f11937b8bc9f00c9561de7529b086351c6a7c3936fd",
    "M7/M7-ROBUST-20260920T211216Z/robust_front.csv":
        "293d492846976f9ad41a39ea1c04da6216bb714fbf0b2c6b386013667bdb3898",
}

RUNS = {
    "M5": {"run": "M5/M5-ABL-20260920T211134Z", "report": "M5_ai_ablation.md",
           "json": ["summary.json"], "frozen": ["config_snapshot.yaml"],
           # hand-written, embedded verbatim by the generator; its numbers are not in
           # summary.json by design and are attributed to it, not to the run
           "embedded": ["M5_qualitative_audit.md"]},
    "M6": {"run": "M6/M6-AF-20260920T211148Z", "report": "M6_adaptive_fidelity.md",
           "json": [], "frozen": ["summary.json", "config_snapshot.yaml", "counters.json"]},
    "M7": {"run": "M7/M7-UQ-20260920T233048Z", "report": "M7_uncertainty_robust.md",
           "json": ["summary.json"],
           "frozen": ["config_snapshot.yaml", "comparison.csv", "paired_difference.json"]},
    "M7-ROBUST": {"run": "M7/M7-ROBUST-20260920T211216Z", "report": None, "json": [],
                  "frozen": ["robust.json", "robust_front.csv", "config_snapshot.yaml"]},
}

# old key -> (new key, why). Values must be identical under the new name.
RENAMES = {
    "cfd_calls": ("surface_evaluations",
                  "NR-31: the count is of evaluations through the CFD-derived drag surface, "
                  "not of CFD solver runs"),
    "cfd_calls_mean": ("surface_evaluations_mean", "NR-31, same count, per-method mean"),
}
PRESENTATION_KEYS = {"figures"}     # list of figure files written; not a result

# numeric table tokens of the BEFORE report that are allowed to be absent from a table
# today, with the reason; each is still required to appear somewhere in today's report.
EXPECTED_GONE = {
    "M7": {
        "17": "projected throughput, was printed as 17 (3 s.f.); still printed, same format",
        "500": "n of the original mixed-draw robust cell; superseded in the table by the "
               "like-for-like cell and quoted in the sentence under it",
    },
}

# Text a row LABEL may gain without the row being a different row. NR-31 (cosmetic): the
# prospective surrogate table now marks heat flux as log10, as the static table always did.
ROW_LABEL_MARKERS = (" (log₁₀)",)

# table rows that are allowed to differ, keyed by a substring of the problem line
EXPECTED_ROW_CHANGES = {
    "M7": {
        "`measured throughput`": "NR-34 item 1: the row was a projection printed as a "
                                 "measurement; it is now the row 'PROJECTED throughput' with "
                                 "the same number, beside new ACHIEVED rows",
        "`achieved parallel efficiency`": "NR-34 item 1: same - now 'parallel efficiency "
                                          "ASSUMED for the projection', same number",
        "`**uncertainty**`": "NR-34 item 8: the robust cell (n = 500 mixed draws) is "
                             "superseded by the like-for-like cell; the original cell is "
                             "quoted in full in the sentence under the table",
    },
}

_NUM = re.compile(r"(?<![\w.])[-+−]?\d[\d,]*\.?\d*(?:[eE][-+]?\d+)?%?")
_FORMATS = (".0f", ".1f", ".2f", ".3f", ".4f", ".2g", ".3g", ".4g", ".1e", "+.4f", "+.3g",
            "+.4g", "+.2f", ",")


def _leaves(obj: Any, path: tuple = ()):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _leaves(v, (*path, str(k)))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _leaves(v, (*path, i))
    else:
        yield path, obj


def _same(a: Any, b: Any) -> bool:
    if isinstance(a, float) and isinstance(b, float) and math.isnan(a) and math.isnan(b):
        return True
    return type(a) is type(b) and a == b or (
        isinstance(a, int | float) and isinstance(b, int | float)
        and not isinstance(a, bool) and not isinstance(b, bool) and float(a) == float(b))


def _get(obj: Any, path: tuple):
    for key in path:
        if isinstance(obj, dict):
            if key not in obj:
                return KeyError
            obj = obj[key]
        elif isinstance(obj, list):
            if not isinstance(key, int) or key >= len(obj):
                return KeyError
            obj = obj[key]
        else:
            return KeyError
    return obj


def compare_json(before: Any, after: Any) -> dict[str, Any]:
    changed, missing, renamed, exempt = [], [], [], []
    n = 0
    for path, value in _leaves(before):
        if path and path[0] in PRESENTATION_KEYS:
            exempt.append(path)
            continue
        n += 1
        now = _get(after, path)
        if now is KeyError:
            new_path = tuple(RENAMES[k][0] if isinstance(k, str) and k in RENAMES else k
                             for k in path)
            now = _get(after, new_path) if new_path != path else KeyError
            if now is KeyError:
                missing.append(path)
                continue
            renamed.append((path, new_path))
        if not _same(value, now):
            changed.append((path, value, now))
    before_paths = {p for p, _ in _leaves(before)}
    renamed_to = {new for _, new in renamed}
    added = sorted({".".join(str(k) for k in p if not isinstance(k, int))
                    for p, _ in _leaves(after)
                    if p not in before_paths and p not in renamed_to
                    and not (p and p[0] in PRESENTATION_KEYS)})
    return {"n_leaves_before": n, "changed": changed, "missing": missing,
            "renamed": sorted({(next(k for k in reversed(a) if isinstance(k, str)),
                                next(k for k in reversed(b) if isinstance(k, str)))
                               for a, b in renamed}),
            "n_renamed_leaves": len(renamed), "added_key_paths": added,
            "n_exempt_leaves": len(exempt)}


def table_tokens(markdown: str) -> list[str]:
    """Numeric tokens of markdown TABLE cells (header and separator rows excluded)."""
    tokens: list[str] = []
    rows = markdown.splitlines()
    for i, line in enumerate(rows):
        if not line.lstrip().startswith("|") or set(line.strip()) <= set("|-: "):
            continue
        nxt = rows[i + 1].strip() if i + 1 < len(rows) else ""
        if nxt.startswith("|") and set(nxt) <= set("|-: "):
            continue                                        # a header row
        for cell in line.strip().strip("|").split("|"):
            tokens += [m.group(0).replace("−", "-").rstrip(",") for m in _NUM.finditer(cell)]
    return tokens


def table_rows(markdown: str) -> list[tuple[str, list[str]]]:
    """(first cell, numeric tokens of the whole row) for every table DATA row, in order."""
    out: list[tuple[str, list[str]]] = []
    rows = markdown.splitlines()
    for i, line in enumerate(rows):
        if not line.lstrip().startswith("|") or set(line.strip()) <= set("|-: "):
            continue
        nxt = rows[i + 1].strip() if i + 1 < len(rows) else ""
        if nxt.startswith("|") and set(nxt) <= set("|-: "):
            continue
        cells = line.strip().strip("|").split("|")
        key = cells[0].strip()
        for marker in ROW_LABEL_MARKERS:        # a unit marker added to a label (NR-31)
            key = key.replace(marker, "")
        out.append((key, table_tokens(line)))
    return out


def rows_preserved(before_md: str, after_md: str) -> tuple[int, list[str]]:
    """ROW-WISE: the k-th before-row with a given first cell must be matched by the k-th
    after-row with that first cell, and every numeric token of the before-row must be in
    it (as a multiset - a row may GAIN a column, it may not lose or change a number)."""
    from collections import Counter, defaultdict

    after: dict[str, list[list[str]]] = defaultdict(list)
    for key, tokens in table_rows(after_md):
        after[key].append(tokens)
    seen: Counter = Counter()
    problems: list[str] = []
    rows = table_rows(before_md)
    for key, tokens in rows:
        k = seen[key]
        seen[key] += 1
        if k >= len(after[key]):
            problems.append(f"row `{key}` (occurrence {k + 1}) has no counterpart")
            continue
        lost = Counter(tokens) - Counter(after[key][k])
        if lost:
            problems.append(f"row `{key}` (occurrence {k + 1}) lost {sorted(lost.elements())}")
    return len(rows), problems


def all_tokens(markdown: str) -> set[str]:
    return {m.group(0).replace("−", "-").rstrip(",") for m in _NUM.finditer(markdown)}


def renderings(values: list[float]) -> set[str]:
    out: set[str] = set()
    for v in values:
        if isinstance(v, bool) or not isinstance(v, int | float) or not math.isfinite(v):
            continue
        for scale, suffix in ((1.0, ""), (100.0, "%"), (1 / 60.0, ""), (1 / 3600.0, "")):
            for fmt in _FORMATS:
                try:
                    text = format(v * scale if fmt != "," else int(round(v * scale)), fmt)
                except (ValueError, OverflowError):
                    continue
                out.add(text + suffix)
                out.add(text.lstrip("+") + suffix)
                if suffix:                      # a share printed without its % sign
                    out.add(text)
        if float(v).is_integer():
            out.add(str(int(v)))
    return out


def _numeric_lists(obj: Any):
    if isinstance(obj, dict):
        for v in obj.values():
            yield from _numeric_lists(v)
    elif isinstance(obj, list):
        if obj and all(isinstance(v, int | float) and not isinstance(v, bool) for v in obj):
            yield obj
        for v in obj:
            yield from _numeric_lists(v)


def numbers_in(obj: Any) -> list[float]:
    """Every number in a result file, plus the two reductions the generators apply to a
    numeric list before printing it: its mean and its sum."""
    found = []
    for values in _numeric_lists(obj):
        finite = [float(v) for v in values if math.isfinite(v)]
        if finite:
            found += [sum(finite), sum(finite) / len(finite)]
    for _, value in _leaves(obj):
        if isinstance(value, int | float) and not isinstance(value, bool):
            found.append(value)
        elif isinstance(value, str):      # pre-rendered phrases, e.g. Wilson intervals
            found += [float(t.rstrip("%").replace(",", "")) for t in _NUM.findall(value)
                      if t.rstrip("%").replace(",", "").replace(".", "", 1)
                      .lstrip("+-").isdigit()]
    return found


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_show(ref: str, relative: str) -> bytes | None:
    done = subprocess.run(["git", "-C", str(ROOT), "show", f"{ref}:{relative}"],
                          capture_output=True, timeout=60)
    return done.stdout if done.returncode == 0 else None


def check(ref: str) -> tuple[list[str], bool]:
    lines: list[str] = []
    ok = True
    for name, spec in RUNS.items():
        run_now = ROOT / "results" / spec["run"]
        lines += [f"## {name} - `{spec['run'].split('/')[1]}`", ""]

        for fname in spec["frozen"]:
            now = sha((run_now / fname).read_bytes())
            old = git_show(ref, f"results/{spec['run']}/{fname}")
            expected = sha(old) if old is not None else UNTRACKED_SHA256.get(
                f"{spec['run']}/{fname}")
            if expected is None:
                ok = False
                lines.append(f"- `{fname}`: **no before-record** (not in `{ref}`, no "
                             "recorded hash)")
                continue
            ok &= now == expected
            lines.append(f"- `{fname}`: SHA-256 "
                         f"{'IDENTICAL' if now == expected else '**CHANGED**'} to "
                         + (f"`{ref}`" if old is not None else "the recorded hash")
                         + f" (`{now[:16]}`)")
        result_numbers: list[float] = []
        for fname in [*spec["json"], *[f for f in spec["frozen"] if f.endswith(".json")]]:
            result_numbers += numbers_in(json.loads((run_now / fname).read_text()))
        for fname in spec["json"]:
            old = git_show(ref, f"results/{spec['run']}/{fname}")
            if old is None:
                ok = False
                lines.append(f"- `{fname}`: **not in `{ref}`**")
                continue
            cmp = compare_json(json.loads(old), json.loads((run_now / fname).read_text()))
            bad = bool(cmp["changed"] or cmp["missing"])
            ok &= not bad
            lines.append(
                f"- `{fname}`: {cmp['n_leaves_before']:,} values before; "
                f"**{len(cmp['changed'])} changed, {len(cmp['missing'])} missing**; "
                f"{cmp['n_renamed_leaves']} carried under a declared rename "
                f"({', '.join(f'`{a}` -> `{b}`' for a, b in cmp['renamed']) or 'none'}), "
                f"values identical; {cmp['n_exempt_leaves']} exempt "
                f"(`{'`, `'.join(sorted(PRESENTATION_KEYS))}`).")
            for path, a, b in cmp["changed"][:20]:
                lines.append(f"    - CHANGED `{'.'.join(map(str, path))}`: {a!r} -> {b!r}")
            for path in cmp["missing"][:20]:
                lines.append(f"    - MISSING `{'.'.join(map(str, path))}`")
            if cmp["added_key_paths"]:
                lines.append("    - added (new information, no old value displaced): "
                             + ", ".join(f"`{p}`" for p in cmp["added_key_paths"]))

        if spec["report"]:
            before_md = (git_show(ref, f"reports/milestones/{spec['report']}") or b"").decode()
            now_md = (ROOT / "reports" / "milestones" / spec["report"]).read_text()
            now_all = all_tokens(now_md)
            gone = sorted({t for t in table_tokens(before_md) if t not in now_all})
            allowed = EXPECTED_GONE.get(name, {})
            unexplained_gone = [t for t in gone if t not in allowed]
            ok &= not unexplained_gone
            lines.append(
                f"- report tables, before -> after: {len(table_tokens(before_md)):,} numeric "
                f"table tokens before, **{len(unexplained_gone)} absent from today's report "
                f"without a declared reason**" + (f" ({unexplained_gone[:15]})"
                                                  if unexplained_gone else "") + ".")
            for t in gone:
                if t in allowed:
                    lines.append(f"    - `{t}` not in a table now: {allowed[t]}")
            n_rows, problems = rows_preserved(before_md, now_md)
            declared = EXPECTED_ROW_CHANGES.get(name, {})
            undeclared = [q for q in problems if not any(key in q for key in declared)]
            ok &= not undeclared
            lines.append(
                f"- report tables ROW BY ROW: {n_rows} data rows before; "
                f"{n_rows - len(problems)} found again with every number intact, "
                f"{len(problems) - len(undeclared)} differ for a declared reason, "
                f"**{len(undeclared)} differ without one**.")
            for q in problems:
                why = next((v for key, v in declared.items() if key in q), None)
                lines.append(f"    - {q}" + (f" - DECLARED: {why}" if why else " - **UNDECLARED**"))
            pool = renderings(result_numbers)
            if name == "M7":      # the report also quotes the runs it folds in
                for extra in sorted((ROOT / "results" / "M7").glob("M7-LFL-*/*.json")):
                    pool |= renderings(numbers_in(json.loads(extra.read_text())))
            embedded: set[str] = set()
            for extra_md in spec.get("embedded", []):
                embedded |= set(table_tokens(
                    (ROOT / "reports" / "milestones" / extra_md).read_text()))
            today = table_tokens(now_md)
            unexplained = sorted({t for t in today if t not in pool and t not in embedded
                                  and t.lstrip("+-") not in pool
                                  and not re.fullmatch(r"[-+]?\d{1,2}", t)})
            lines.append(
                f"- report tables, after -> result files: {len(today):,} numeric table "
                f"tokens today, {len(today) - sum(t in unexplained for t in today):,} are "
                f"renderings of a number in the run's JSON"
                + (f" or come from the embedded hand-written `{'`, `'.join(spec['embedded'])}`"
                   if spec.get("embedded") else "") + f"; {len(unexplained)} distinct "
                "tokens are not matched by this script's format list"
                + (f": {unexplained[:40]}" if unexplained else "") + ".")
        lines.append("")
    lines.insert(0, f"**Overall: {'PASS - no result moved' if ok else 'FAIL'}**\n")
    return lines, ok


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--before-ref", default=BEFORE_REF)
    ap.add_argument("--markdown", type=Path, default=None)
    args = ap.parse_args()
    lines, ok = check(args.before_ref)
    lines.insert(1, f"Before = git `{args.before_ref}`; after = the working tree.\n")
    text = "\n".join(lines)
    print(text)
    if args.markdown:
        args.markdown.write_text(text + "\n")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
