"""The 2026-09-21 report-generator fixes (NR-31, NR-34, NR-35 follow-ups).

Two kinds of test. (1) The generators say what was measured: no label survives from the
model they were first written for. (2) `scripts/check_report_regeneration.py` - the proof
that regenerating the reports moved no result - really does fail when a number moves.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import os
import subprocess
from pathlib import Path

import numpy as np
import pytest

from src.aether.optimization import adaptive_report
from src.aether.optimization.ablation_report import _power_reading, write_m5_report
from src.aether.uncertainty import plots as m7_plots
from src.aether.uncertainty import report as m7_report
from src.aether.uncertainty.propagate import cluster_convergence
from src.aether.uncertainty.statistics import bootstrap_ci, cluster_bootstrap_ci
from src.aether.utils.run import overlapping_runs

ROOT = Path(__file__).resolve().parents[1]
M5_RUN = ROOT / "results" / "M5" / "M5-ABL-20260920T211134Z"
M6_RUN = ROOT / "results" / "M6" / "M6-AF-20260920T211148Z"
M7_RUN = ROOT / "results" / "M7" / "M7-UQ-20260920T233048Z"


def _checker():
    spec = importlib.util.spec_from_file_location(
        "check_report_regeneration", ROOT / "scripts" / "check_report_regeneration.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------------------
# the checker can fail
# ---------------------------------------------------------------------------------------
def test_checker_catches_a_changed_a_missing_and_an_undeclared_renamed_value():
    chk = _checker()
    before = {"a": {"hv": 0.3556, "per_seed": {"cfd_calls": [1, 2]}}, "figures": ["x.png"],
              "gone": 1.0, "nan": float("nan")}
    after = copy.deepcopy(before)
    assert not chk.compare_json(before, after)["changed"]          # NaN == NaN here

    after["a"]["hv"] = 0.3557
    assert chk.compare_json(before, after)["changed"][0][0] == ("a", "hv")

    after = copy.deepcopy(before)
    del after["gone"]
    assert chk.compare_json(before, after)["missing"] == [("gone",)]

    # a DECLARED rename carries the value; the value must still be identical
    after = copy.deepcopy(before)
    after["a"]["per_seed"] = {"surface_evaluations": [1, 2]}
    after["new_block"] = {"total": 0}
    after["figures"] = ["x.png", "y.png"]                           # presentation only
    out = chk.compare_json(before, after)
    assert not out["changed"] and not out["missing"] and out["n_renamed_leaves"] == 2
    assert out["added_key_paths"] == ["new_block.total"]
    after["a"]["per_seed"]["surface_evaluations"] = [1, 3]
    assert chk.compare_json(before, after)["changed"]

    # an UNdeclared rename is a missing value, not a rename
    after = copy.deepcopy(before)
    after["a"]["renamed_hv"] = after["a"].pop("hv")
    assert chk.compare_json(before, after)["missing"] == [("a", "hv")]


def test_checker_compares_tables_row_by_row():
    chk = _checker()
    before = "| m | hv |\n|---|---|\n| `a` | 0.3556 |\n| `b` | 0.2803 |\n"
    gained_a_column = "| m | hv | solver |\n|---|---|---|\n| `a` | 0.3556 | 0 |\n" \
                      "| `b` | 0.2803 | 0 |\n"
    assert chk.rows_preserved(before, gained_a_column) == (2, [])
    moved = gained_a_column.replace("0.2803", "0.2804")
    n, problems = chk.rows_preserved(before, moved)
    assert n == 2 and len(problems) == 1 and "0.2803" in problems[0]
    assert chk.rows_preserved(before, "| m | hv |\n|---|---|\n| `a` | 0.3556 |\n")[1]


@pytest.mark.skipif(not (M7_RUN / "summary.json").exists(), reason="study results not on disk")
def test_no_result_moved_when_the_reports_were_regenerated():
    chk = _checker()
    known = subprocess.run(["git", "-C", str(ROOT), "cat-file", "-e", chk.BEFORE_REF],
                           capture_output=True)
    if known.returncode:
        pytest.skip(f"git ref {chk.BEFORE_REF} not available")
    lines, ok = chk.check(chk.BEFORE_REF)
    assert ok, "\n".join(lines)


# ---------------------------------------------------------------------------------------
# M5 (NR-31)
# ---------------------------------------------------------------------------------------
@pytest.fixture(scope="module")
def m5_summary():
    path = M5_RUN / "summary.json"
    if not path.exists():
        pytest.skip("M5 study results not on disk")
    summary = json.loads(path.read_text())
    if "cfd_solver_calls" not in summary:
        pytest.skip("M5 summary predates the 2026-09-21 generator; run make ablation-report")
    return summary


def _generated(text: str) -> str:
    """The M5 report minus its embedded HAND-WRITTEN audit, which quotes the old wording on
    purpose (it is the record of what was wrong)."""
    head, _, rest = text.partition("## 7. Qualitative audit")
    return head + rest.partition("## 8. Metric-gaming audit")[2]


def test_m5_counts_solver_calls_separately_from_surface_evaluations(m5_summary, tmp_path):
    assert m5_summary["cfd_solver_calls"]["total"] == 0
    surface = sum(sum(m["per_seed"]["surface_evaluations"])
                  for m in m5_summary["methods"].values())
    assert surface > 0                       # a Fidelity-1 run: look-ups, not solver runs
    text = _generated(write_m5_report(ROOT, m5_summary, tmp_path / "r.md").read_text())
    assert "CFD solver calls made by this study, all methods and seeds: 0." in text
    assert "| CFD calls |" not in text and "CFD-backed" not in text
    assert "drag-surface evaluations / seed" in text


def test_m5_adaptive_label_follows_the_recorded_aero_model(m5_summary, tmp_path):
    text = _generated(write_m5_report(ROOT, m5_summary, tmp_path / "r.md").read_text())
    assert m5_summary["fidelity"] == 1
    assert "F0 only" not in text and "evaluated at Fidelity 0" not in text
    assert f"every candidate at Fidelity 1 (`{m5_summary['aero_model']}`)" in text

    f0 = copy.deepcopy(m5_summary)           # the same generator on a Fidelity-0 record
    f0["fidelity"], f0["aero_model"] = 0, "constant"
    assert "every candidate at Fidelity 0 (`constant`)" in write_m5_report(
        ROOT, f0, tmp_path / "f0.md").read_text()


def _cell(diff, p_holm, verdict, *, effect, sig):
    return {"comparator": "bo_parego", "mean_difference": diff, "a12": 1.0,
            "p_helped_holm": p_holm, "p_hurt_holm": 1.0, "verdict": verdict,
            "rule_legs": {"helped": {"effect_size_met": effect, "significance_met": sig},
                          "hurt": {"effect_size_met": False, "significance_met": False}}}


def test_m5_power_paragraph_names_the_leg_that_failed():
    declared = {"min_hv_gain": 0.005, "alpha": 0.05}
    nmd = "no measured difference"
    s = {"criteria_declared": declared, "criteria": {"checkpoints": {
        "50": _cell(0.0283, 0.0278, "AI helped", effect=True, sig=True),
        "100": _cell(0.0100, 0.2000, nmd, effect=True, sig=False),
        "200": _cell(0.0036, 0.0119, nmd, effect=False, sig=True),
        "300": _cell(0.0001, 0.9000, nmd, effect=False, sig=False)}}}
    out = _power_reading(s)
    assert len(out) == 3                                  # "AI helped" needs no caveat
    assert "fails on its significance leg" in out[0]
    assert "**rejects**" in out[1] and "effect-size leg" in out[1]
    assert "could not tell them apart" not in out[1]      # the NR-31 sentence, gone
    assert "Neither leg" in out[2]


def test_m5_wall_time_caveat_is_generated_from_recorded_run_windows(m5_summary, tmp_path):
    text = write_m5_report(ROOT, m5_summary, tmp_path / "r.md").read_text()
    assert "not a clean cost comparison" in text
    for other in m5_summary["concurrency"]["overlapping_runs"]:
        assert other["run_id"] in text
    bare = {k: v for k, v in m5_summary.items() if k != "concurrency"}
    assert "were not recorded for this run" in write_m5_report(
        ROOT, bare, tmp_path / "bare.md").read_text()


def test_overlapping_runs_reads_the_runs_own_timestamps(tmp_path):
    def make(name, created, end_epoch):
        d = tmp_path / "MX" / name
        d.mkdir(parents=True)
        (d / "config_snapshot.yaml").write_text(
            f"_meta:\n  run_id: {name}\n  created_utc: '{created}'\nconfig: {{}}\n")
        (d / "candidates.csv").write_text("x\n")
        os.utime(d / "candidates.csv", (end_epoch, end_epoch))
        return d

    base = 1_800_000_000                                   # 2027-01-15T08:00:00Z
    mine = make("A", "2027-01-15T08:00:00+00:00", base + 3600)
    make("B", "2027-01-15T08:30:00+00:00", base + 7200)    # overlaps the second half
    make("C", "2027-01-15T10:00:00+00:00", base + 9000)    # starts after A ended
    out = overlapping_runs(tmp_path, mine)
    assert [o["run_id"] for o in out["overlapping_runs"]] == ["B"]
    assert out["overlapping_runs"][0]["overlap_fraction_of_this_run"] == pytest.approx(0.5)


# ---------------------------------------------------------------------------------------
# M6 (NR-35)
# ---------------------------------------------------------------------------------------
@pytest.mark.skipif(not (M6_RUN / "summary.json").exists(), reason="M6 results not on disk")
def test_m6_first_paragraph_states_verdict_unrun_arm_and_reachability():
    import yaml

    summary = json.loads((M6_RUN / "summary.json").read_text())
    snap = yaml.safe_load((M6_RUN / "config_snapshot.yaml").read_text())["config"]
    text = " ".join(adaptive_report._read_first(summary, snap))
    assert "NOT_SUPPORTED" in text
    assert "`ai_adaptive`" in text and "untested" in text
    assert "Reachability" in text and "NR-35" in text
    union, ref = summary["truth"]["hv_union_of_arms"], summary["truth"]["hv_reference"]
    assert f"{100 * union / ref:.1f}%" in text

    reachable = copy.deepcopy(summary)       # the sentence is conditional, not pre-written
    reachable["truth"]["hv_union_of_arms"] = ref
    assert "sizing flaw" not in " ".join(adaptive_report._read_first(reachable, snap))


# ---------------------------------------------------------------------------------------
# M7 (NR-34)
# ---------------------------------------------------------------------------------------
def test_cluster_bootstrap_is_wider_than_row_bootstrap_when_rows_share_a_branch():
    rng = np.random.default_rng(3)
    branch = np.repeat(np.arange(24), 125)
    clustered = rng.normal(0.0, 10.0, 24)[branch] + rng.normal(0.0, 1.0, branch.size) + 400.0

    def mean(a):
        return float(np.mean(a))

    row = bootstrap_ci(clustered, mean, n_bootstrap=400, seed=1)
    cluster = cluster_bootstrap_ci(clustered, branch, mean, n_bootstrap=400, seed=1)
    assert (cluster[1] - cluster[0]) > 5.0 * (row[1] - row[0])
    # analytic check: s.e. of the mean is ~ 10 / sqrt(24) = 2.04, so 95% half-width ~ 4
    assert 2.5 < (cluster[1] - cluster[0]) / 2.0 < 5.5

    iid = rng.normal(400.0, 10.0, branch.size)             # no branch effect: they agree
    row = bootstrap_ci(iid, mean, n_bootstrap=400, seed=1)
    cluster = cluster_bootstrap_ci(iid, branch, mean, n_bootstrap=400, seed=1)
    assert 0.5 < (cluster[1] - cluster[0]) / (row[1] - row[0]) < 2.0

    out = cluster_convergence(clustered, branch, 0.01)
    assert out["pre_declared"] is False and out["n_clusters"] == 24
    assert set(out["statistics"]) == {"mean", "p95"}


def test_attribution_panels_carry_their_own_labels_and_every_design(tmp_path, monkeypatch):
    names = ["alpha", "beta", "gamma"]
    inputs = [{"name": n, "kind": "epistemic"} for n in names]

    def block(totals_a, totals_b):
        return {"inputs": inputs, "k_body_over_nose": 1.0, "outputs": {
            "out_a": {"total": totals_a, "total_ci": [[t, t] for t in totals_a]},
            "out_b": {"total": totals_b, "total_ci": [[t, t] for t in totals_b]}}}

    summary = {"run_id": "M7-TEST", "attribution": {
        "design_one": block([0.9, 0.1, 0.0], [0.0, 0.2, 0.8]),
        "design_two": block([0.1, 0.9, 0.0], [0.5, 0.0, 0.5])}}
    captured = {}

    def fake_save(fig, out_dir, stem, caption):
        captured["labels"] = [[t.get_text() for t in ax.get_yticklabels()]
                              for ax in fig.axes if ax.get_visible()]
        captured["titles"] = [ax.get_title() for ax in fig.axes if ax.get_visible()]
        return Path(out_dir) / f"{stem}.png"

    monkeypatch.setattr(m7_plots, "save_figure", fake_save)
    m7_plots.plot_attribution(summary, tmp_path)
    # each panel is sorted by ITS OWN indices (largest last = top bar)
    assert captured["labels"][0][-1] == "alpha" and captured["labels"][1][-1] == "gamma"
    assert captured["labels"][2][-1] == "beta"
    assert len(captured["labels"]) == 4                    # 2 designs x 2 outputs
    assert any("design_two" in t for t in captured["titles"])


@pytest.fixture(scope="module")
def m7_summary():
    path = M7_RUN / "summary.json"
    if not path.exists():
        pytest.skip("M7 study results not on disk")
    return json.loads(path.read_text())


def test_m7_limitations_follow_the_runs_fidelity_and_tier_counts(m7_summary):
    text = m7_report._limitations(m7_summary)
    n_t1 = m7_summary["uncertainty_model"]["tier_counts"]["T1"]
    assert m7_summary["fidelity"] == 1 and n_t1 == 4
    assert "The two inputs that are T1" not in text and "At Fidelity 0" not in text
    assert f"{n_t1} inputs are tiered" in text
    assert "This run is Fidelity 1" in text and "4 C_D terms were propagated" in text

    f0 = copy.deepcopy(m7_summary)
    f0["fidelity"], f0["aero_model"] = 0, "constant"
    assert "This run is Fidelity 0" in m7_report._limitations(f0)


def test_m7_sizing_labels_the_projection_and_prints_the_achieved_rate(m7_summary):
    if "achieved_throughput" not in m7_summary:
        pytest.skip("M7 summary predates the 2026-09-21 generator")
    text = m7_report._sizing(m7_summary)
    achieved = m7_summary["achieved_throughput"]
    assert achieved["evaluations_per_second"] == pytest.approx(
        m7_summary["n_evaluations"] / m7_summary["wall_s"])
    assert "| measured throughput |" not in text
    assert "a projection, not a measurement" in text
    assert f"**{achieved['evaluations_per_second']:.3g} evaluations/s**" in text


def test_m7_convergence_reports_both_bootstraps_and_keeps_the_declared_verdict(m7_summary):
    blocks = m7_summary["propagation"]
    if "cluster_bootstrap" not in next(iter(blocks.values()))["convergence"]:
        pytest.skip("M7 summary predates the 2026-09-21 generator")
    text = m7_report._convergence(m7_summary)
    assert "The pre-declared check is the ROW bootstrap" in text
    assert "all reported statistics are within the declared tolerance on it" in text
    base = blocks["baseline"]["convergence"]
    assert base["verdict"]["mean"]["converged"] is True            # verdict untouched
    strict = base["cluster_bootstrap"]["statistics"]["mean"]
    assert strict["half_width_rel"] > base["tolerance_rel"]         # marginal miss, 1.06%
    assert "the `baseline` mean misses it" in text


def test_m7_cache_hit_sentence_reports_the_measured_count(m7_summary):
    text = m7_report._robust(m7_summary)
    hits = sum(r["cache_hits"] for r in m7_summary["robust"]["runs"])
    paid = sum(r["budget_used"] for r in m7_summary["robust"]["runs"])
    assert f"**{hits:,} cache hits in {hits + paid:,} inner evaluations" in text
    if hits == 0:
        assert "did not occur" in text and "free cache hits" not in text


def test_m7_report_only_reproduces_every_figure(m7_summary):
    written = {Path(p).name for p in m7_summary["figures"]}
    if "M7_robust_vs_nominal.png" not in written:
        pytest.skip("figures not regenerated yet")
    assert {"M7_robust_vs_nominal.png", "M7_shortcut_verification.png",
            "M7_attribution.png"} <= written
