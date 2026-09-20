# M8 — Thermal coupon experiment: support package

> **STATUS: THE EXPERIMENT HAS NOT BEEN RUN.** No measurement exists anywhere in this
> directory. Everything here is preparation: drawings, a printable holder, a data
> schema, safety and calibration procedure, and the analysis code that will process the
> data once there is some. `VALIDATION_MATRIX.md` row M8 is `IN_PROGRESS` and will stay
> that way until a real coupon has been heated and the comparison has been written.
>
> A synthetic chain check (`tests/test_thermal_coupon.py`) verifies the software works.
> It is not evidence about any material. Every file it produces carries `synthetic` in
> its name and says so in its first line.

---

## 1. What this experiment is for

The project's headline claim rests on one piece of physics: that a slab of solid
material acts as a **diffusive low-pass filter** on a heat pulse, so the interior
temperature history depends on the *shape* of the pulse and not only on its total
energy. That claim is made by `src/aether/tps/conduction1d.py`, and it has so far been
checked only against an analytical solution — which verifies the arithmetic, not the
physics of a real material with real losses and a real contact interface.

This experiment heats a 3-D-printed polymer coupon with two heating histories that carry
**the same integrated energy** — one high-peak and short, one lower-peak and long — and
asks whether the model, calibrated on *different* runs and then frozen, predicts the
in-depth temperature histories of both.

### What it is NOT

- **Not a re-entry simulator.** A hobby heater on a plastic plate at ~350 K has nothing
  in common with a 2 MW/m² stagnation point at 2000 K. No aerothermodynamics, no
  ablation, no radiation-dominated surface, no shock layer.
- **Not a test of the burn-vs-bake conclusion.** M1's result involves a longer pulse
  that *also* carries a larger integrated load. Here the energy is held fixed on
  purpose, which isolates duration and — as `analysis/design_cases.py` will tell you
  before you build anything — reverses the ordering. Read §5 before quoting this
  experiment in the same paragraph as M1.
- **Not a material characterisation.** The properties that come out are *effective*
  through-thickness properties of one printed part at one set of print settings. They
  are not the filament's datasheet properties and must not be reported as such.

**What it is:** a blind test of the transient conduction model, on a real solid, with
real losses, at a scale a student can actually build.

---

## 2. What is in this directory

```
README.md                    this file
protocol.md                  safety, calibration, and the frozen-prediction workflow
data_schema.md               acquisition file format and the metadata sidecar
acquisition_template.csv     empty CSV with the required columns
metadata_template.meta.yaml  empty sidecar with every required field

cad/
  make_coupon_holder.py      deterministic generator: ASCII STL + OpenSCAD source
  coupon_holder.stl          printable frame (generated - do not hand-edit)
  coupon_holder.scad         authoritative editable geometry
  coupon_holder_params.json  dimensions and derived quantities
  make_sensor_drawing.py     deterministic generator for the drawing
  sensor_placement.svg       dimensioned drawing with sensor depths (generated)

analysis/
  coupon_model.py            forward model, data loading, SHA-256 helpers
  design_cases.py            size the matched-energy pair against a temperature ceiling
  calibrate.py               fit parameters from calibration runs; freeze them
  compare_model.py           section 47 metrics, residual plots, uncertainty coverage
  synthetic.py               SYNTHETIC data generator for the software check

blind_validation/
  README.md                  the commit-before-measuring discipline
  make_prediction.py         predict the unseen case from frozen parameters + manifest

data/                        where acquisition files go (empty - nothing measured yet)
```

---

## 3. Bill of materials

**No prices, part numbers, suppliers or brand names appear below.** None were verified,
and an unverified part number in a protocol is worse than no part number: it looks
authoritative and sends someone to buy the wrong thing. What follows is the
*specification* each item has to meet and the trade-off behind it. Sourcing is the
student's job, from a supplier they can actually check.

### Coupon

| Item | Specification | Notes |
|---|---|---|
| Filament | Any thermoplastic whose datasheet glass-transition or heat-deflection temperature is comfortably above the planned ceiling | See §4 — this is a decision, not a default |
| Coupon | 60 × 60 × 10 mm flat plate, printed **solid** (100% infill) | Voids are unmodelled insulation; a gyroid coupon is not a slab |
| Print orientation | Flat on the bed, so layer lines run **parallel** to the isotherms | Through-thickness conductivity of a printed part is lower than in-plane; keep the anisotropy on one axis and call the fitted value "effective" |
| Spare coupon | One extra from the same print job, to be sectioned | Used to measure actual sensor-hole depths, and to check for voids |

### Heating

| Option | For | Against |
|---|---|---|
| **Polyimide film heater**, adhesive-backed, flat, sized to the coupon face | Thin and low thermal mass — closest to the model's zero-heat-capacity heater assumption; uniform flux | Fragile; needs good adhesion or the contact resistance drifts |
| **Silicone rubber heater pad** | Robust, even heating, easy to clamp | More thermal mass than a film; adds a lag the model does not have |
| **Aluminium spreader block + cartridge heater** | Very even flux; easy to instrument and to calibrate calorimetrically | Large thermal mass badly violates the model's heater assumption; needs the mass measured and accounted for |
| **Halogen / IR lamp (non-contact)** | No contact resistance at all | Absorbed flux depends on the polymer's unknown surface absorptivity, which becomes a second unfitted parameter; alignment and view factor are hard |

Also needed: an adjustable **DC supply** or a PWM controller with a current readout,
sized to deliver the flux `analysis/design_cases.py` says you need (on the order of a
few watts to a few tens of watts over 36 cm² — compute it, do not guess); a **voltmeter
and ammeter** (or a supply with calibrated readback) so electrical power is *measured*,
not assumed from a nameplate.

### Sensing — the choice that matters most

| Option | Resolution and range | Trade-off |
|---|---|---|
| **Type-K thermocouple**, fine-gauge bead or ~1 mm sheathed probe, with a cold-junction-compensating interface IC or a multi-channel TC DAQ | Wide range, well past any polymer's limit; absolute accuracy is limited by the alloy tolerance, which is why §6 makes you calibrate | Standard tolerance grades have absolute errors of a few kelvin — unusable without two-point calibration; the resolution of common single-channel TC ICs is coarse relative to the effect being measured |
| **NTC thermistor**, small glass-bead or epoxy-bead, with a precision divider and a 16-bit-or-better ADC | Far better resolution and repeatability over a narrow range; the range is the limitation | Limited maximum temperature (check the part's rating against your ceiling); self-heating must be managed by keeping excitation current low or pulsing it; needs its own Steinhart–Hart or β calibration |

**Recommendation, stated as a recommendation:** if the ceiling is below the thermistor's
rated maximum, use thermistors. The quantity being measured is a **difference of a few
kelvin between two cases** (`design_cases.py` predicted ~3.5 K at the deepest sensor for
the placeholder properties), so resolution and repeatability matter far more than range,
and a thermocouple's absolute accuracy is not the binding constraint anyway once it is
two-point calibrated. Use thermocouples if the ceiling is high enough to need them.

Either way: **at least four channels** (see `cad/sensor_placement.svg`), a logger
sampling at ≥ 1 Hz with a known clock, and one extra channel measuring **ambient air**
near the coupon but out of the plume.

### Rig

- The printed holder (`cad/coupon_holder.stl`), which supports the coupon on four small
  corner pads so only ~4% of the back face touches anything, and stands it 20 mm off the
  bench so the back face sees room air.
- Thermally conductive paste or the same filament, to back-fill the sensor holes.
- A light, even clamping arrangement for the heater — enough pressure for repeatable
  contact, not enough to bow a 10 mm plate.
- A non-combustible work surface, and a way to stop the heater instantly (§ protocol).

---

## 4. What the student must decide

These are genuinely open. Nothing in this package chooses them, and each one changes the
experiment.

1. **Which polymer.** The ceiling in §6 is derived from the filament's datasheet
   glass-transition or heat-deflection temperature, and that number varies by grade and
   manufacturer. Do not take it from a table on the internet and do not take it from
   this document — take it from the datasheet of the spool you print with. As families,
   PLA softens lowest and polycarbonate highest, with PETG and ABS/ASA between; the
   ordering is not a substitute for the number.
2. **Which heater**, from the four options above. This determines whether the model's
   zero-thermal-mass heater assumption is nearly true (film), approximately true
   (silicone pad), or false and in need of correction (metal block).
3. **Thermocouples or thermistors**, from the range-versus-resolution trade above. This
   follows from the ceiling, which follows from decision 1.
4. **How the heater flux is known** — from electrical power with a measured heated area,
   or from the calorimetric slug calibration in the protocol, or both. Doing both and
   comparing is the strongest option and costs one extra afternoon.
5. **The declared tolerance** that decides whether the blind prediction counts as
   agreement, written down *before* the experiment (protocol step 9). `compare_model.py`
   deliberately refuses to pick one.

---

## 5. Running the chain

```bash
# 0. generate the printable parts and the drawing (deterministic)
.venv/bin/python experiments/thermal_coupon/cad/make_coupon_holder.py  --out experiments/thermal_coupon/cad
.venv/bin/python experiments/thermal_coupon/cad/make_sensor_drawing.py --out experiments/thermal_coupon/cad

# 1. size the matched-energy pair against your ceiling, BEFORE printing
.venv/bin/python experiments/thermal_coupon/analysis/design_cases.py --ceiling-degc 85

# 2. after the calibration runs: fit, then freeze
.venv/bin/python experiments/thermal_coupon/analysis/calibrate.py fit \
    --runs experiments/thermal_coupon/data/cal_*.csv \
    --fix contact_resistance_m2k_w=<measured> \
    --out experiments/thermal_coupon/results
.venv/bin/python experiments/thermal_coupon/analysis/calibrate.py freeze \
    --calibration experiments/thermal_coupon/results/calibrated_parameters.yaml \
    --out experiments/thermal_coupon/blind_validation/frozen_parameters.yaml

# 3. predict the unseen cases and ARCHIVE, then commit before measuring
.venv/bin/python experiments/thermal_coupon/blind_validation/make_prediction.py \
    --frozen experiments/thermal_coupon/blind_validation/frozen_parameters.yaml \
    --case   experiments/thermal_coupon/data/val_a_case.csv \
    --measurement experiments/thermal_coupon/data/val_a.csv \
    --out    experiments/thermal_coupon/blind_validation/predictions

# 4. run the experiment, then compare
.venv/bin/python experiments/thermal_coupon/analysis/compare_model.py \
    --prediction  .../prediction_val_a.csv \
    --manifest    .../manifest_val_a.json \
    --measurement experiments/thermal_coupon/data/val_a.csv \
    --out         experiments/thermal_coupon/results
```

### The software check, which is not data

```bash
.venv/bin/python experiments/thermal_coupon/analysis/synthetic.py --out /tmp/m8_synthetic
.venv/bin/python -m pytest tests/test_thermal_coupon.py -q
```

The test generates fake measurements from the solver with known parameters, calibrates
against them **at a different mesh resolution**, freezes, predicts an unseen triangular
pulse, and checks the parameters and the prediction come back. It currently recovers
conductivity, specific heat and both loss coefficients to well under 1%, and predicts
the unseen case to better than 0.1 K against the noise-free truth.

**That is a statement about the code. It is not a statement about physics, and it is not
experimental evidence.** No real material was involved at any point.

---

## 6. The one result that is already recorded

The synthetic chain surfaced a genuine identifiability limit that changes the physical
protocol, so it is written down in `docs/negative_results.md` (NR-11) rather than buried
here:

- With a **prescribed** heater flux, the heater-to-coupon **contact resistance** is only
  weakly observable — it does not change how much heat enters, only the temperature of
  the flux-application plane and hence the surface loss. Fitting it alongside everything
  else lets it absorb other errors: in the synthetic twin it came out several hundred
  percent wrong while dragging conductivity and specific heat ~12% off with it. The
  protocol therefore measures it separately and holds it fixed during calibration.
- A step-heating calibration run **shorter than about three diffusion times** leaves
  conductivity and specific heat degenerate with each other. Their *ratio* is recovered
  well; their individual values are not. Hence the long step in the protocol.

Both were found by running the software, not by reasoning about it, which is the reason
the synthetic twin exists.
