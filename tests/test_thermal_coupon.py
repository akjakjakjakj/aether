"""M8 SYNTHETIC TWIN — end-to-end check of the thermal-coupon analysis chain.

*** THIS IS A SOFTWARE TEST. IT IS NOT EXPERIMENTAL EVIDENCE. ***

The physical coupon experiment has not been run and no measurement exists. What these
tests do is generate fake "measurements" from the project's own conduction solver with
KNOWN parameters and seeded noise, then push them through the real pipeline —

    calibrate  ->  freeze  ->  blind predict  ->  archive  ->  compare

— and check that the known parameters come back out and that the blind prediction is
accurate. Passing proves the chain is wired up and the inverse problem is well posed for
this run design. It proves nothing about whether the model describes a real polymer,
because the data never touched one.

`VALIDATION_MATRIX.md` row M8 is `IN_PROGRESS` for exactly this reason.
"""

import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "experiments" / "thermal_coupon" / "analysis"
BLIND = ROOT / "experiments" / "thermal_coupon" / "blind_validation"
for _p in (str(ANALYSIS), str(BLIND)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import calibrate  # noqa: E402
import compare_model  # noqa: E402
import coupon_model  # noqa: E402
import make_prediction  # noqa: E402
import synthetic  # noqa: E402

GEN_CELLS = 60
"""Cells used to GENERATE the synthetic data."""
FIT_CELLS = 40
"""Cells used to FIT it. Deliberately different: if both used the same mesh the test
would only prove that the code can invert its own discrete operator."""

MEASURED_CONTACT_RESISTANCE = 1.6e-3
"""Held fixed during calibration, standing in for protocol.md's separate
contact-resistance characterisation. See `test_contact_resistance_is_weakly_identified`
for why it cannot simply be fitted alongside everything else."""


def _compact_specs():
    """The standard run set, decimated so the whole chain runs in a few seconds."""
    specs = synthetic.run_definitions()
    specs["CAL-COOLDOWN"]["n_samples"] = 241
    specs["CAL-STEP"]["n_samples"] = 301
    specs["BLIND-RAMP"]["n_samples"] = 301
    return specs


def _geometry(n_cells=GEN_CELLS):
    return coupon_model.CouponGeometry(
        thickness_m=0.010, density_kg_m3=1180.0, heated_area_m2=0.060 * 0.060,
        n_cells=n_cells)


def _strip_to_declared_case(measured_csv: Path, out_dir: Path) -> Path:
    """Build a DECLARED heating history from a measured file, dropping every temperature.

    This is what the student does by hand before the experiment: write down the heating
    history they intend to apply, with no temperatures in it, because there are not any
    yet.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    lines = measured_csv.read_text().splitlines()
    comments = [ln for ln in lines if ln.lstrip().startswith("#")]
    rows = [ln for ln in lines if not ln.lstrip().startswith("#")]
    header = rows[0].split(",")
    keep = [i for i, name in enumerate(header)
            if name in ("time_s", "heater_flux_w_m2")]
    out = comments + [",".join(header[i] for i in keep)]
    out += [",".join(r.split(",")[i] for i in keep) for r in rows[1:]]
    case_csv = out_dir / "blind_ramp_case_synthetic.csv"
    case_csv.write_text("\n".join(out) + "\n")

    meta = yaml.safe_load(
        coupon_model.sidecar_path(measured_csv).read_text())
    meta["run_id"] = "BLIND-RAMP-CASE"
    meta["initial"] = {"t_initial_k": 295.15}
    coupon_model.sidecar_path(case_csv).write_text(yaml.safe_dump(meta, sort_keys=False))
    return case_csv


@pytest.fixture(scope="module")
def chain(tmp_path_factory):
    """Run the entire synthetic chain once and hand every artefact to the tests."""
    base = tmp_path_factory.mktemp("m8_synthetic")
    data = base / "data"
    specs = _compact_specs()

    written = {}
    for name, spec in specs.items():
        run = synthetic.generate_run(name, spec, geometry=_geometry(), noise_k=0.4, seed=7)
        written[name] = synthetic.write_run(run, data)

    runs = [coupon_model.load_run(written[n][0]) for n in ("CAL-COOLDOWN", "CAL-STEP")]
    result = calibrate.calibrate(
        runs, fixed={"contact_resistance_m2k_w": MEASURED_CONTACT_RESISTANCE},
        n_cells=FIT_CELLS)

    cal_path = base / "calibrated_parameters.yaml"
    cal_path.write_text(yaml.safe_dump(result.to_dict(), sort_keys=False))
    frozen_path = base / "frozen_parameters.yaml"
    calibrate.freeze(cal_path, frozen_path)

    case_csv = _strip_to_declared_case(written["BLIND-RAMP"][0], base / "case")
    case = make_prediction.load_declared_case(case_csv)
    case["frozen_path"] = frozen_path
    frozen = make_prediction.load_frozen(frozen_path)
    prediction = make_prediction.predict_with_uncertainty(
        case, frozen, n_samples=40, n_cells=FIT_CELLS, seed=11)
    pred_csv, manifest_path = make_prediction.write_prediction(
        case, frozen, prediction, base / "predictions")

    measured = coupon_model.load_run(written["BLIND-RAMP"][0])
    loaded_pred = compare_model.load_prediction(pred_csv)
    manifest = compare_model.check_manifest(manifest_path, pred_csv)
    comparison = compare_model.compare(loaded_pred, measured)
    comparison["manifest"] = manifest

    return {
        "base": base, "data": data, "written": written, "calibration": result,
        "calibration_path": cal_path, "frozen_path": frozen_path, "case_csv": case_csv,
        "prediction_csv": pred_csv, "manifest_path": manifest_path,
        "manifest": manifest, "comparison": comparison, "measured": measured,
    }


# ---------------------------------------------------------------------------------
# 1. Parameter recovery
# ---------------------------------------------------------------------------------

@pytest.mark.parametrize("name,tolerance_pct", [
    ("conductivity_w_mk", 3.0),
    ("specific_heat_j_kgk", 3.0),
    ("h_front_w_m2k", 5.0),
    ("h_back_w_m2k", 5.0),
])
def test_calibration_recovers_the_known_parameters(chain, name, tolerance_pct):
    """The inverse problem is well posed for this run design and this mesh mismatch.

    Tolerances are set generously relative to what is actually achieved (well under 1%
    on every parameter) so that a genuine regression trips them but ordinary numerical
    drift does not.
    """
    truth = synthetic.TRUTH.to_dict()[name]
    fitted = getattr(chain["calibration"].parameters, name)
    error_pct = 100.0 * abs(fitted - truth) / truth
    assert error_pct < tolerance_pct, f"{name}: {fitted:g} vs truth {truth:g}"


def test_calibration_residual_is_the_size_of_the_injected_noise(chain):
    """RMSE much larger than the noise means model error; much smaller means overfitting."""
    assert 0.5 * 0.4 < chain["calibration"].rmse_k < 3.0 * 0.4


def test_calibration_records_its_inputs_and_flags_them_synthetic(chain):
    cal = chain["calibration"]
    assert cal.any_synthetic is True
    assert len(cal.inputs) == 2
    for entry in cal.inputs:
        assert len(entry["sha256"]) == 64
        assert entry["sha256"] == coupon_model.sha256_file(entry["path"])


def test_contact_resistance_is_weakly_identified_and_the_fit_says_so(chain):
    """Documented identifiability limit, asserted so it cannot be quietly forgotten.

    With a PRESCRIBED heater flux, contact resistance enters the model only through the
    surface-loss term: it changes the flux-application-plane temperature, not the flux.
    It is therefore far less observable than conductivity, and a fit that is allowed to
    move it will absorb other errors into it. `protocol.md` measures it separately for
    this reason. The check here is on the fit's OWN uncertainty estimate: it must report
    contact resistance as markedly less determined than conductivity.
    """
    runs = [coupon_model.load_run(chain["written"][n][0])
            for n in ("CAL-COOLDOWN", "CAL-STEP")]
    free = calibrate.calibrate(runs, n_cells=FIT_CELLS)

    def relative_sigma(name):
        return free.sigma[name] / getattr(free.parameters, name)

    assert relative_sigma("contact_resistance_m2k_w") > 3.0 * relative_sigma(
        "conductivity_w_mk")


# ---------------------------------------------------------------------------------
# 2. Freezing and blind prediction
# ---------------------------------------------------------------------------------

def test_frozen_file_is_marked_frozen_and_points_back_at_its_calibration(chain):
    frozen = yaml.safe_load(chain["frozen_path"].read_text())
    assert frozen["frozen"] is True
    assert frozen["synthetic_inputs"] is True
    assert frozen["source_calibration"]["sha256"] == coupon_model.sha256_file(
        chain["calibration_path"])


def test_prediction_refuses_parameters_that_are_not_frozen(tmp_path):
    loose = tmp_path / "loose.yaml"
    loose.write_text(yaml.safe_dump({"frozen": False, "parameters": {}}))
    with pytest.raises(ValueError, match="not marked"):
        make_prediction.load_frozen(loose)


def test_prediction_refuses_a_case_file_that_already_contains_measurements(chain, tmp_path):
    """The single easiest way to accidentally fake a blind prediction, blocked."""
    leaky = tmp_path / "leaky_synthetic.csv"
    shutil.copy(chain["written"]["BLIND-RAMP"][0], leaky)
    shutil.copy(coupon_model.sidecar_path(chain["written"]["BLIND-RAMP"][0]),
                coupon_model.sidecar_path(leaky))
    with pytest.raises(ValueError, match="measurement columns"):
        make_prediction.load_declared_case(leaky)


def test_manifest_hashes_every_input_and_the_prediction_itself(chain):
    manifest = json.loads(chain["manifest_path"].read_text())
    assert manifest["kind"] == "aether_m8_blind_prediction"
    assert manifest["synthetic"] is True
    assert manifest["created_utc"].endswith("+00:00")
    for entry in manifest["inputs"].values():
        assert entry["sha256"] == coupon_model.sha256_file(entry["path"])
    assert set(manifest["code"]) >= {"coupon_model.py", "conduction1d.py"}
    assert manifest["outputs"]["prediction_csv"]["sha256"] == coupon_model.sha256_file(
        chain["prediction_csv"])


def test_a_tampered_prediction_is_detected(chain, tmp_path):
    """An edited prediction must void the comparison, not quietly improve it."""
    tampered = tmp_path / "prediction_tampered.csv"
    text = chain["prediction_csv"].read_text().splitlines()
    text[-1] = text[-1].replace(",", ",", 1) + ""
    text.append(text[-1])
    tampered.write_text("\n".join(text) + "\n")
    check = compare_model.check_manifest(chain["manifest_path"], tampered)
    assert check["intact"] is False


# ---------------------------------------------------------------------------------
# 3. Comparison on the unseen case
# ---------------------------------------------------------------------------------

def test_blind_prediction_matches_the_unseen_case(chain):
    """The whole point: parameters fitted on a step and a cool-down predict a ramp."""
    pooled = chain["comparison"]["pooled"]
    assert pooled["rmse_k"] < 1.0, pooled
    assert abs(pooled["bias_k"]) < 0.3, pooled


@pytest.mark.parametrize("key,limit", [
    ("peak_robust_error_k", 0.4),
    ("time_to_peak_robust_error_s", 20.0),
])
def test_section_47_metrics_are_small_on_every_sensor(chain, key, limit):
    """Limits are set from what the smoothed estimators actually achieve, with headroom.

    A peak error can never be measured better than the record it is read from allows.
    With smoothing (`compare_model.SMOOTHING_FRACTION`) the residual estimator bias on
    this case is 0.04-0.15 K against 0.4 K of injected sensor noise, and the
    time-to-peak error is within three samples; the limits here are roughly 3x that, so
    a genuine regression trips them and ordinary numerical drift does not. What pins the
    model down absolutely is
    `test_blind_prediction_is_essentially_exact_without_sensor_noise` below.
    """
    for sensor in chain["comparison"]["per_sensor"]:
        assert abs(sensor[key]) < limit, (sensor["channel"], sensor[key])


def test_blind_prediction_is_essentially_exact_without_sensor_noise():
    """The same chain, scored against the noise-free truth instead of a noisy record.

    Every metric in the noisy comparison is dominated by the injected noise, which makes
    it a poor test of the software. Re-scoring the identical frozen prediction against
    the clean forward solution isolates what is actually being checked: that calibration
    on a step plus a cool-down, at a DIFFERENT mesh resolution from the one that
    generated the data, reproduces an unseen triangular pulse.
    """
    specs = _compact_specs()
    clean = synthetic.generate_run("BLIND-RAMP", specs["BLIND-RAMP"],
                                   geometry=_geometry(), noise_k=0.0, seed=7)
    calibration_runs = []
    for name in ("CAL-COOLDOWN", "CAL-STEP"):
        run = synthetic.generate_run(name, specs[name], geometry=_geometry(),
                                     noise_k=0.4, seed=7)
        calibration_runs.append(run)

    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        paths = [synthetic.write_run(r, tmp)[0] for r in calibration_runs]
        result = calibrate.calibrate(
            [coupon_model.load_run(p) for p in paths],
            fixed={"contact_resistance_m2k_w": MEASURED_CONTACT_RESISTANCE},
            n_cells=FIT_CELLS)

    predicted = coupon_model.predict_sensors(
        _geometry(n_cells=FIT_CELLS), result.parameters, clean["time_s"],
        clean["flux_w_m2"], clean["sensor_depths_m"],
        t_initial_k=specs["BLIND-RAMP"]["t_initial_k"], t_ambient_k=synthetic.T_AMBIENT_K)

    residual = predicted - clean["clean_k"]
    assert np.sqrt(np.mean(residual**2)) < 0.10, "noise-free RMSE [K]"
    peak_error = predicted.max(axis=0) - clean["clean_k"].max(axis=0)
    assert np.all(np.abs(peak_error) < 0.20), peak_error


def test_the_raw_peak_estimators_are_the_biased_ones(chain):
    """Guards the reason the `*_robust_*` metrics exist.

    The claim is statistical, so it is asserted statistically. The maximum of a noisy
    record is biased HIGH by roughly sigma*sqrt(2 ln N), which makes a correct model look
    like it under-predicts the peak: the raw peak error must therefore be negative on
    every sensor, and smaller in magnitude once the plateau average removes most of that
    bias. Asserting the per-sensor inequality directly would be asserting a coincidence -
    it held for one noise seed and failed for another, which is how the non-deterministic
    seeding bug in `synthetic._stable_offset` was found.
    """
    sensors = chain["comparison"]["per_sensor"]
    assert all(s["peak_error_k"] < 0.0 for s in sensors), [s["peak_error_k"] for s in sensors]
    raw = float(np.mean([abs(s["peak_error_k"]) for s in sensors]))
    robust = float(np.mean([abs(s["peak_robust_error_k"]) for s in sensors]))
    assert robust < raw, (robust, raw)

    surface = min(sensors, key=lambda s: s["depth_m"])
    assert abs(surface["time_to_peak_error_s"]) >= abs(
        surface["time_to_peak_robust_error_s"])


def test_synthetic_generation_is_reproducible_across_processes(chain):
    """The seed offset must not depend on Python's salted str hash.

    Regenerating the same run in this process must reproduce the file this module's
    fixture wrote earlier, byte for byte. Before the fix this passed within a process
    and failed between them, so the comparison is against the file on disk.
    """
    specs = _compact_specs()
    regenerated = synthetic.generate_run("BLIND-RAMP", specs["BLIND-RAMP"],
                                         geometry=_geometry(), noise_k=0.4, seed=7)
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        again, _ = synthetic.write_run(regenerated, tmp)
        assert coupon_model.sha256_file(again) == coupon_model.sha256_file(
            chain["written"]["BLIND-RAMP"][0])
    assert synthetic._stable_offset("CAL-STEP") == 5311


def test_uncertainty_band_covers_most_of_the_measurement(chain):
    """Coverage is scored against the band widened by the declared sensor noise.

    It is not asserted to be exactly 95%: the band excludes model-form error and the
    residuals are correlated in time, so the nominal figure would be a coincidence. What
    is asserted is that the band is neither degenerate nor absurd.
    """
    for sensor in chain["comparison"]["per_sensor"]:
        assert not sensor["band_is_degenerate"]
        assert sensor["coverage_fraction"] > 0.80, sensor
    assert chain["comparison"]["pooled"]["mean_coverage_fraction"] > 0.85


# ---------------------------------------------------------------------------------
# 4. The synthetic data can never be mistaken for a measurement
# ---------------------------------------------------------------------------------

@pytest.mark.parametrize("run_name", ["CAL-COOLDOWN", "CAL-STEP", "BLIND-RAMP"])
def test_every_synthetic_artefact_announces_itself(chain, run_name):
    csv_path, meta_path = chain["written"][run_name]
    assert "synthetic" in csv_path.name
    assert "synthetic" in meta_path.name
    first = csv_path.read_text().splitlines()[0]
    assert first.startswith("#") and "SYNTHETIC" in first
    assert "NOT A MEASUREMENT" in first
    meta = yaml.safe_load(meta_path.read_text())
    assert meta["synthetic"] is True


def test_the_prediction_and_its_report_are_labelled_synthetic_too(chain, tmp_path):
    """The label has to survive every hop, or the last document in the chain lies."""
    assert "synthetic" in chain["prediction_csv"].name
    assert "SYNTHETIC" in chain["prediction_csv"].read_text().splitlines()[0]

    report = tmp_path / "comparison.md"
    result = dict(chain["comparison"])
    result["synthetic"] = True
    compare_model.write_report(result, [], report)
    text = report.read_text()
    assert "NOT EXPERIMENTAL EVIDENCE" in text
    assert "physical experiment has not been run" in text


def test_the_solver_extension_defaults_leave_the_entry_model_untouched():
    """Cross-check from the coupon side: a coupon stack with no bench terms is the
    original adiabatic entry stack."""
    geom = _geometry(n_cells=20)
    params = coupon_model.CouponParameters(conductivity_w_mk=0.2,
                                           specific_heat_j_kgk=1500.0)
    stack = coupon_model.build_stack(geom, params, t_initial_k=300.0, t_ambient_k=300.0)
    assert stack.h_front_w_m2k == 0.0
    assert stack.h_back_w_m2k == 0.0
    assert stack.front_contact_resistance_m2k_w == 0.0
    assert stack.t_radiation_sink_k == 300.0


def test_diffusion_time_is_the_number_the_protocol_uses_to_set_run_length():
    geom = _geometry()
    params = synthetic.TRUTH
    tau = coupon_model.diffusion_time_s(geom, params)
    alpha = params.conductivity_w_mk / (geom.density_kg_m3 * params.specific_heat_j_kgk)
    assert tau == pytest.approx(geom.thickness_m**2 / alpha)
    assert 500.0 < tau < 2000.0, "a 10 mm polymer coupon should soak in ~15 minutes"


def test_sensor_sampling_extrapolates_rather_than_clamping_at_the_faces():
    """A surface sensor sits outside the cell centres; clamping would bias it."""
    depth = np.array([0.001, 0.003, 0.005])
    field = np.array([[310.0, 305.0, 300.0]])
    out = coupon_model._sample_at_depths(depth, field, np.array([0.0, 0.006]))
    assert out[0, 0] == pytest.approx(312.5)      # linear extrapolation, not 310.0
    assert out[0, 1] == pytest.approx(297.5)      # not 300.0
