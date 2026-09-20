# M8 — Thermal coupon: safety and experimental protocol

> **This experiment has not been run.** This document is the plan. Nothing in it should
> be read as a record of anything that happened.
>
> **Adult supervision is required for every step that energises the heater.** This
> protocol assumes a school or home workshop, a student, and a supervising adult who has
> read §1 before the first run. If no supervisor is available, the experiment does not
> happen; there is no solo version of it.

---

## 1. Hazards and controls

Read this section in full before energising anything. The hazards are ordinary — this is
a small heater on a plastic plate — but they are real, and two of them (fume and
thermal-runaway) are the kind that are easy to not notice until they matter.

### 1.1 Burns

The heated face reaches the ceiling temperature set in §3 and stays hot for **tens of
minutes** after the heater is switched off. The deepest sensor peaks *after* the heater
goes off — that lag is literally what the experiment is about.

- Never touch the coupon, the heater or the clamp until the surface channel reads below
  40 °C. The instrument tells you; your hand does not.
- The holder's legs exist partly so the hot assembly is not in contact with the bench.
- Keep a metal tray or a ceramic tile under the rig.

### 1.2 Fire and thermal runaway

A resistive heater with no thermostat will keep heating until something stops it. The
failure that matters is a **controller or logging failure while the heater is on**.

- The heater circuit must have a **physical switch or a plug within arm's reach**, on the
  supply side, that kills power without going through software.
- Use a supply with an adjustable **current limit** set just above the working current.
  If the heater shorts, the limit is what prevents the interesting outcome.
- Fuse the heater circuit at or just above the working current.
- **Never leave an energised run unattended, ever, not even for the long 3000 s step.**
  Someone stays in the room, watching the live surface temperature, for the whole run.
- Nothing combustible within 300 mm: no paper, no filament spools, no cloth, no
  isopropanol.

### 1.3 Fumes

Heated thermoplastics emit volatile organic compounds and ultrafine particles; ABS and
ASA are worse than PETG and PLA. The ceiling in §3 keeps the coupon below its softening
point, which substantially limits this, but does not eliminate it.

- Work in a **ventilated space** — an open window with cross-flow, a fume extractor, or
  outdoors in still conditions.
- Stop immediately and ventilate if you can smell the coupon. A smell means decomposition
  products are reaching you; it also means the coupon is above its intended ceiling and
  the run is void anyway.
- Anyone with asthma or a respiratory condition should not be in the room during runs.

### 1.4 Electrical

- Low-voltage DC (≤ 24 V) only. **Do not build a mains-voltage heater.** If the only
  heater available is a mains silicone pad, it must be driven through a proper,
  commercially built, earthed controller by the supervising adult, or not used.
- Dry hands, dry bench, no liquids near the supply.
- Inspect heater leads before every session. A cracked lead on a heater that is about to
  be clamped against plastic is the worst combination on this list.

### 1.5 Eyes and mechanical

- Safety glasses whenever drilling sensor holes or sectioning the spare coupon.
- Drill the holes in a vice, never freehand into a part held in your fingers.

---

## 2. Hard stop conditions

If any of these occurs, **cut power first and investigate afterwards.** A run stopped
early is data about why it stopped; a run continued past one of these is a hazard.

| Condition | Why |
|---|---|
| Any channel exceeds the ceiling of §3 | The coupon is softening; properties are changing under you and the run is void regardless |
| Any channel reads a discontinuity, goes open-circuit, or flatlines | A sensor has come loose, and a loose sensor near a heater is also a short-circuit risk |
| Smell, smoke, visible deformation, or a bubbling adhesive | Decomposition |
| Logger stops recording or the clock jumps | You are now running an unmonitored heater |
| Current draw departs from the expected value by more than ~10% | Heater or contact has changed; also possibly a partial short |
| Anything at all you do not understand | Genuinely: this is the most important row |

Record every stop in the engineering notebook, including what the channels read at the
moment of the stop. A record of an aborted run is worth keeping (spec §31).

---

## 3. The temperature ceiling

**Ceiling = (datasheet T_g or HDT of the exact filament used) − 20 K**, and never above
any component's rating (heater, adhesive, sensor, wire insulation) minus its own margin.
Take the lower of all of them.

The 20 K margin exists because the datasheet value is a property of the *material*, the
coupon is a *printed part* whose behaviour near T_g is worse than the bulk polymer's, and
your temperature measurement has its own uncertainty. Above T_g the polymer's density,
conductivity and specific heat all change and the model's constant-property assumption —
the thing being tested — stops applying. A run that softens the coupon does not produce a
bad result; it produces no result.

**This document does not supply the number.** It varies by grade and manufacturer, and a
fabricated value here would be worse than none. Get it from the datasheet of the spool.

Write the ceiling on a card and tape it to the bench. Then size the experiment against
it, before printing anything:

```bash
.venv/bin/python experiments/thermal_coupon/analysis/design_cases.py --ceiling-degc <yours>
```

That script solves for the largest matched-energy pair that stays under the ceiling in
both cases, and prints the predicted peak at every sensor depth. If the predicted
separation between the two cases at the deepest sensor is not several times your sensor
uncertainty, the experiment cannot answer its question yet — change the coupon thickness
or the durations until it can. Doing that *before* building is the entire point of having
a model.

---

## 4. Build

1. Print the coupon 60 × 60 × 10 mm, **100% infill**, flat on the bed. Print a second,
   identical coupon in the same job — it will be sectioned.
2. Print the holder from `cad/coupon_holder.stl` (or from the `.scad`, via OpenSCAD).
   Any filament; it is not in the thermal path except through the corner pads.
3. **Measure the coupon**: mass on a scale reading to 0.01 g, and all three dimensions
   with calipers at several places. Density = mass / volume. This is a *measurement* and
   it is never fitted — record it and its uncertainty in the metadata sidecar.
4. Drill the sensor holes per `cad/sensor_placement.svg`: from one **side edge**,
   parallel to the heated face, staggered, each to the centreline. §"Why the sensors go
   in from the side" in `cad/make_sensor_drawing.py` explains why this is not optional —
   a wire running across the gradient conducts heat to its own junction and reads low.
5. Install sensors, back-fill each hole, route wires out through the holder's wire gap
   with strain relief.
6. **Section the spare coupon** and measure the actual hole depths with calipers.
   Record the measured depth and an honest uncertainty per channel. The model is fitted
   against the *declared* depths, so a 0.5 mm depth error becomes a property error.

---

## 5. Sensor calibration — two-point

Do this **with the sensors installed in the coupon**, not on the bench, so the whole
measurement chain is calibrated together.

### 5.1 Ice point

1. Make a slush of crushed ice and distilled water in an insulated vessel — mostly ice,
   just enough water to fill the gaps. **Slush, not ice water**: a bath with visible free
   water above the ice is not at 0 °C.
2. Immerse the instrumented coupon (or a bagged sensor set, if immersion would wet the
   installation) and stir gently.
3. Wait for every channel to settle, then log ≥ 120 s.
4. Reference: **0.000 °C**, exactly, by definition of the ice point at 1 atm.

### 5.2 Boiling point

1. Bring distilled water to a rolling boil in the same room.
2. Suspend the sensors in the **water**, not in the steam above it, and not touching the
   vessel wall.
3. Log ≥ 120 s at a stable reading.
4. Reference: **not 100 °C**. The boiling point depends on the local atmospheric
   pressure. Read the pressure at the time (a local weather station's station-level
   pressure, or a barometer) and use the corresponding boiling point from a steam table.
   Record which source you used. Assuming 100 °C at a few hundred metres of altitude
   introduces roughly a kelvin of error straight into the calibration you are trying to
   remove.
5. If the sensor's rating or the coupon's ceiling makes a 100 °C point impossible, use a
   stirred warm-water bath at a temperature read by an independently calibrated
   reference thermometer, and say so in the metadata.

### 5.3 Applying it

Fit a two-point linear correction per channel, `T_true = a·T_raw + b`, and record `a` and
`b` in each channel's entry in the metadata sidecar. Also record the **residual scatter**
at each fixed point — that is the number that becomes `temperature_uncertainty_k`, and
`compare_model.py` uses it to widen the coverage band.

Two points give you offset and span. They do not give you linearity. Note in the
notebook that any nonlinearity between the two points is uncorrected.

---

## 6. Heater flux calibration — calorimetric slug

Electrical power is easy to measure; the *flux into the coupon* is not the same thing.
Some of the electrical power goes into the heater's own thermal mass, out of its back
face, and out of its edges. That difference is a systematic error that a model
calibration will silently absorb into the material properties.

### Method

1. Machine or buy a **metal slug** — aluminium or copper — of similar face area to the
   coupon, and **measure its mass** to 0.01 g. Its specific heat is a published,
   well-known property of the metal; cite whichever reference you use.
2. Instrument the slug with one sensor in a drilled hole near its centre.
3. Insulate the slug on every face **except** the heated one, as well as you can, and
   record how (foam, ceramic wool, still air in a box).
4. Apply the heater exactly as it will be applied to the coupon — same clamp, same
   pressure, same interface material.
5. Energise at a known electrical power and log the slug temperature for a period short
   enough that the slug stays close to ambient, so losses are small.
6. In that early window the slug is nearly a lumped capacity:

   ```
   q_in [W] = m · c_p · dT/dt
   ```

   Fit the slope `dT/dt` over the window. Divide by the heated area to get the flux in
   W/m². The **ratio** of that to the electrical power is the heater's delivery
   efficiency for this arrangement.
7. Repeat at ≥ 3 power levels and check the efficiency is constant. If it is not, the
   flux is not simply proportional to power and the acquisition file must carry a
   measured `heater_flux_w_m2` column rather than one computed from `V·I`.
8. Estimate the uncertainty: propagate the mass, the specific-heat reference, the area,
   and the slope fit. Record it as `heater.flux_uncertainty_w_m2` in every sidecar.

**Bound the losses you did not model.** Repeat the slug run with the insulation
deliberately worse and see how much the fitted flux moves. That difference is a floor on
your systematic error, and it belongs in the notebook.

---

## 7. Contact-resistance characterisation

Do this separately, and then **hold the value fixed during calibration**. This is not
tidiness; it is a result the synthetic twin produced (NR-11 in
`docs/negative_results.md`):

> With a prescribed heater flux, contact resistance enters the model only through the
> surface-loss term. It is therefore weakly identifiable, and a fit allowed to move it
> will use it to absorb other errors — in the synthetic check it came out several hundred
> percent wrong while dragging conductivity and specific heat about 12% off with it.

### Method

1. With the heater clamped to the coupon exactly as it will be for the real runs, apply a
   **steady, modest flux** and wait for a near-steady state (several diffusion times —
   `design_cases.py` prints the diffusion time for your coupon).
2. Measure, simultaneously: the heater-side interface temperature (a sensor bonded to the
   heater's own face, or the heater's own resistance-temperature relation if it is
   characterised) and the coupon's 0 mm surface channel.
3. At steady state,

   ```
   R_contact [K·m²/W] = (T_heater − T_surface) / q''
   ```

4. Repeat at ≥ 2 flux levels; the resistance should be roughly constant. If it is not,
   the clamp pressure is changing with temperature and you must say so.
5. **Do not disturb the clamp afterwards.** Re-clamping changes the number. If the
   heater has to come off, re-measure.

Feed the result to the calibration as `--fix contact_resistance_m2k_w=<value>`.

---

## 8. Calibration runs

Two runs, and the reason for each is that it constrains something the other cannot.

| Run | What | Why |
|---|---|---|
| **CAL-1 cool-down** | Pre-heat the coupon uniformly (a warm oven or a long low-power soak), remove the heat source, log until it is within ~1 K of ambient — typically ≥ 2 diffusion times | Zero heater flux, so the decay is governed by the loss coefficients and the thermal mass alone. This is what pins `h_front` and `h_back`. |
| **CAL-2 long step** | Constant heater flux held for **at least 2–3 diffusion times**, then off, logging until the interior has peaked and started to fall | The steady depth gradient `dT/dx = q''/k` pins conductivity; the transient approach to it pins the diffusivity and hence specific heat. |

**CAL-2 must be long.** In the synthetic check, a step of about one diffusion time left
conductivity and specific heat degenerate: the fit recovered their *ratio* to 0.4% and
each of them ~12% low. Three diffusion times separated them to better than 0.5%. For a
10 mm coupon of a typical thermoplastic that means a run of the order of an hour, which
is the single biggest time cost in this protocol and is not negotiable.

Log ambient air temperature throughout. Note the room's ventilation state — an open
window changes `h`, and `h` is being fitted.

Then:

```bash
calibrate.py fit --runs data/cal_1.csv data/cal_2.csv \
                 --fix contact_resistance_m2k_w=<from §7> --out results/
```

Read the output. If any parameter is reported **at a bound**, the data did not constrain
it and it must not be quoted as a measurement. If the RMSE is much larger than your
sensor uncertainty, there is model error, and you should look at the residual shape
before going any further.

---

## 9. Declare the tolerance — BEFORE the validation runs

Write into the engineering notebook, and commit it:

- the pooled RMSE, peak error and time-to-peak error you will accept as agreement, and
  your justification for each in terms of the sensor uncertainty and the flux uncertainty
  from §6;
- what you will conclude if the residuals are **structured** rather than scattered —
  a trend in a residual plot is model error, and no parameter value fixes it;
- what you will do if the two cases disagree in the *direction* the model predicted but
  not the *magnitude*.

`compare_model.py` will not assign a verdict. That is on purpose: a threshold chosen
after seeing the residuals is not a test.

---

## 10. Freeze, predict, archive, commit

```bash
calibrate.py freeze --calibration results/calibrated_parameters.yaml \
                    --out blind_validation/frozen_parameters.yaml
make_prediction.py --frozen blind_validation/frozen_parameters.yaml \
                   --case data/val_a_case.csv \
                   --measurement data/val_a.csv \
                   --out blind_validation/predictions
```

`--measurement` names the path the measurement *will* occupy; the script refuses to run
if that file already exists, because a prediction made after the measurement is not a
prediction.

Do this for **both** cases, A and B, before running either. Then **commit and push the
predictions and their manifests**. See `blind_validation/README.md` — the commit is what
makes the archiving checkable by someone who does not trust you.

---

## 11. The validation runs

Run **VAL-A** (high peak, short) and **VAL-B** (low peak, long), with amplitudes and
durations from `design_cases.py`, carrying the same integrated energy.

- Start each from a coupon that has returned to within ~0.5 K of ambient. Record the
  initial temperature of every channel; do not assume it is ambient.
- Log ambient throughout.
- Run each case for the full record length `design_cases.py` gives, which includes the
  post-heating soak. **The deepest sensor peaks minutes after the heater goes off.**
  Stopping the log when the heater stops discards the most informative part of the run —
  the same mistake the simulation made and had to fix (NR-02 in
  `docs/negative_results.md`).
- Repeat each case at least twice. Two runs that disagree with each other by more than
  they disagree with the model mean the rig is not repeatable, and nothing can be
  concluded until it is.
- Do not touch the clamp between A and B. If you must, re-measure §7 and re-calibrate,
  and the frozen parameters are void.

---

## 12. Compare and record

```bash
compare_model.py --prediction .../prediction_val_a.csv \
                 --manifest   .../manifest_val_a.json \
                 --measurement data/val_a.csv --out results/
```

Check the manifest line first. If it says MISMATCH, the prediction file changed after
archiving and the comparison is void — find out why before reading any number below it.

Then write the engineering-notebook entry (spec §32: Question, Hypothesis, Action,
Expected, Observed, Evidence, Interpretation, Next), update `VALIDATION_MATRIX.md` row
M8 against the tolerance declared in §9, and put anything that went wrong into
`docs/negative_results.md`. A run that failed is a result; a run that is quietly not
mentioned is a missing one.
