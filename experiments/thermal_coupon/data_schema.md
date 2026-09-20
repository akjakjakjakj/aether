# M8 acquisition data schema

Every acquisition run is **two files with the same stem**:

```
<run>.csv           the samples
<run>.meta.yaml     everything needed to interpret them
```

`analysis/coupon_model.py::load_run` refuses to load a CSV whose sidecar is missing, and
refuses a sidecar that does not declare a depth for every sensor channel present in the
CSV. That refusal is deliberate. A column of temperatures without the depth it was
measured at is not data; it is a column of numbers, and it cannot be compared with a
model.

---

## 1. The CSV

Plain comma-separated text. Lines beginning with `#` are comments and are skipped — the
first line of a synthetic file is a `#` comment saying so.

| Column | Unit | Required | Meaning |
|---|---|---|---|
| `time_s` | s | **yes** | Seconds from the start of the run. Strictly increasing. Not a wall-clock timestamp. |
| `heater_flux_w_m2` | W·m⁻² | **yes** | Flux delivered into the coupon face, after the §6 efficiency correction. Zero during a cool-down run. |
| `heater_v` | V | no | Measured heater voltage, if logged |
| `heater_a` | A | no | Measured heater current, if logged |
| `t_ch1_degc` … `t_chN_degc` | **°C** | **yes**, ≥ 1 | Calibrated sensor readings. The channel *number* carries no meaning; the depth lives in the sidecar. |
| `t_ambient_degc` | **°C** | recommended | Ambient air near the rig, out of the plume. Used as the convective and radiative reference. |
| `quality_flag` | – | recommended | `0` good, `1` suspect, `2` reject. Non-zero samples are excluded from fits and metrics but **kept in the file**. |

### Why Celsius in the file and Kelvin everywhere else

The project is SI and Kelvin internally (spec §8), and mixing the two is exactly the
error §8 forbids. But a thermocouple logger emits Celsius, and silently re-typing its
output into a column called `t_ch1_k` is how a 273.15 K error gets into a repository.

The resolution: the raw file stays in the unit the instrument produced, the column name
says so out loud with a `_degc` suffix, and conversion happens at **exactly one place** —
`load_run`. Nothing downstream ever sees a Celsius value. If you write your own loader,
convert there and nowhere else.

### Sampling

- **≥ 1 Hz.** The fastest thing in the record is the surface response at the start of a
  step, with a timescale of seconds.
- A constant rate is not required — `time_s` is read per row — but a *known* one is.
- Record for the full length `design_cases.py` gives, which includes the post-heating
  soak. The deepest sensor peaks minutes after the heater goes off.

### Missing data

Leave the field empty rather than writing a sentinel. `load_run` reads an empty field as
NaN and every fit and metric masks NaN. A `-999` in a temperature column will be fitted.

---

## 2. The metadata sidecar

YAML. `metadata_template.meta.yaml` in this directory is a fill-in-the-blanks copy.

```yaml
schema_version: 1
run_id: CAL-2                    # unique, referenced in the notebook
run_type: calibration_step       # see the list below
synthetic: false                 # true ONLY for generated data
utc_start: 2026-09-21T14:03:00+00:00
operator: <name>
supervisor: <name>               # protocol.md requires one for energised runs
notes: >
  Free text. Ventilation state, anything unusual, anything you would want to know
  in three months when the residual looks odd.

coupon:
  material: <filament, grade, manufacturer as printed on the spool>
  datasheet_tg_or_hdt_degc: <from the datasheet; the ceiling derives from this>
  print:
    layer_height_mm:
    infill_percent: 100
    nozzle_degc:
    bed_degc:
    orientation: flat on bed, layer lines parallel to the isotherms
  thickness_m:                   # MEASURED with calipers, not nominal
  thickness_uncertainty_m:
  measured_dimensions_m: [, , ]
  measured_mass_kg:
  density_kg_m3:                 # mass / volume. Measured, never fitted.
  density_uncertainty_kg_m3:

heater:
  type: <film / silicone pad / metal block + cartridge / lamp>
  heated_area_m2:                # MEASURED contact area, not the heater's nameplate area
  flux_source: calorimetric_slug # or electrical_power
  flux_efficiency:               # from protocol.md section 6, if flux_source is electrical
  flux_uncertainty_w_m2:
  contact_resistance_m2k_w:      # from protocol.md section 7
  contact_resistance_uncertainty_m2k_w:
  clamp_note: <how it was clamped; whether it was disturbed since section 7>

sensors:
  - channel: t_ch1_degc
    type: <type_k_thermocouple / ntc_thermistor + part>
    depth_m: 0.0000              # MEASURED on the sectioned spare, not nominal
    depth_uncertainty_m: 0.0003
    temperature_uncertainty_k: 0.4   # residual scatter at the fixed points, section 5.3
    calibration:
      method: two_point_ice_boil
      ice_point_reading_degc:
      boil_point_reading_degc:
      boil_point_reference_degc:     # NOT 100 unless you are at 1 atm - say where it came from
      gain: 1.0
      offset_k: 0.0
  # ... one entry per channel present in the CSV

sampling:
  rate_hz:
  logger: <instrument>

ambient:
  t_ambient_k:                   # nominal; the CSV column is authoritative if present
  ventilation: <window open / extractor / still room>

initial:
  t_initial_k:                   # only needed for a declared case file with no measurements
```

### `run_type` values

| Value | Meaning |
|---|---|
| `calibration_cooldown` | No heater flux; constrains the loss coefficients |
| `calibration_step` | Long constant flux; constrains conductivity and specific heat |
| `contact_resistance` | Steady-state run for protocol.md §7 |
| `flux_calibration` | Calorimetric slug run, protocol.md §6 — a slug, not the coupon |
| `blind_validation` | One of the matched-energy validation cases |
| `repeat` | A repeat of an earlier run; put the original's `run_id` in `notes` |
| `aborted` | Stopped by a §2 hard-stop condition. **Keep it** (spec §31) |

### Fields that are measured and must never be fitted

`density_kg_m3`, `thickness_m`, every `depth_m`, `heated_area_m2`. Each one is a number
you got from a scale, calipers or a sectioned coupon. If a calibration is allowed to
move them it will quietly absorb a measurement mistake into an "effective" property, the
calibration runs will fit beautifully, and the blind case will not. That is the exact
failure §47's blind case exists to catch — so do not hand it the opportunity.

---

## 3. Declared case files

A file for `blind_validation/make_prediction.py` is the **same schema with the
temperature columns removed**: `time_s` and `heater_flux_w_m2` only, plus a sidecar that
declares the sensors (so the prediction knows which depths to report), the coupon, the
heater, and `initial.t_initial_k`.

`make_prediction.py` **refuses** a case file containing any `t_ch*` column. The single
easiest way to accidentally produce a non-blind "blind prediction" is to point it at the
measurement file, so that is blocked rather than warned about.

---

## 4. Synthetic files

Data generated by `analysis/synthetic.py` carries three independent markers, because a
file gets copied out of its directory and loses its context:

1. `synthetic` in the **filename** — the only marker that travels with the file;
2. a first line beginning `# SYNTHETIC DATA` and containing `NOT A MEASUREMENT`;
3. `synthetic: true` in the sidecar, which `calibrate.py` prints loudly and which
   propagates into the frozen parameter file, the prediction manifest and the comparison
   report.

If you are looking at a file with any of those markers, it came out of the solver. It is
a software check. It is not experimental evidence, and it says nothing about any
material.
