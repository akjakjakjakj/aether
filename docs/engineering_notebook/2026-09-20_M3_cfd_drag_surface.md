# 2026-09-20 — M3: a drag coefficient that knows what shape the capsule is

> **Status when written: PROVISIONAL.** Gate G4 was IN_PROGRESS (the M2 fine-mesh sphere
> cases were still running on the same machine). Nothing built today feeds an optimisation.

## Question

At constant C_D the capsule's forebody shape has no aerodynamic consequence: only its
diameter acts. If C_D comes from CFD as a function of Mach number and shape, (a) how far do
peak heat flux, bondline temperature and peak deceleration move, and (b) does shape start to
matter to the thermal objectives through drag — not just through the nose-radius term of
Sutton–Graves?

## Hypothesis

Written before any design point ran:

- Blunt-forebody C_D,fore will be close to modified-Newtonian levels, will rise with cone
  angle, and will be nearly flat in Mach above about 10 (Mach-number independence).
- The baseline config's C_D = 1.20 is a placeholder; a 25° sphere-cone should come out well
  below it and a 70° one above it. If so, the *baseline* moves a lot and the M4 front (70°
  class) moves a little, in opposite directions.
- Base drag will be a few percent of the total at Mach 3 and negligible above Mach 10, because
  of the 2/(γM²) factor, whatever the base pressure is.
- Expected trouble: M2's agent had flagged the 60°-cone/Mach-6 domain. Not expected: anything
  going wrong at the *slender* end.

## Action

1. Asked where in Mach the entry happens before choosing a Mach range. Most of the heat load
   is above Mach 10, and over half is above Mach 20. A surface over the M2 benchmark's Mach
   3–6 would have been accurate where it does not matter. Range set to Mach 3–20; held
   outside. Reasoning in `docs/theory/cfd_drag_surface.md`.
2. Design: inputs log(Mach), R_n/D, cone half-angle, R_c/D. Aft angle, length and diameter are
   *not* inputs — the forebody-only domain cannot see the first two, and inviscid flow has no
   length scale (checked with a two-diameter pair rather than assumed). Hull anchors at both
   ends of the Mach range + scrambled-Sobol fill; held-out test points drawn before any run.
3. Coarse smoke test of four extreme points first. It broke three ways (NR-19, NR-20): Mach-20
   impulsive start → negative temperature; wide cone → shock walks into the inflow boundary;
   slender cone → the Mach-angle boundary cuts the cone shock. Each isolated in the §36 order,
   fixed additively (`run_case` default behaviour unchanged), and guarded by an automatic
   clearance check with a logged re-run.
4. Measured wall time and **deviated from the brief**: the all-medium design would have taken
   7–8 h on this fanless laptop with the M2 benchmark and an interactive session competing.
   Ran everything on the coarse mesh and a seeded 8-point subset on the medium mesh.
5. Opened NASA TN D-4800 for the base-pressure band instead of trusting the sourcing report's
   summary of it. That changed the model: I had assumed base pressure ≤ freestream; figure
   11(b) shows it *above* freestream for blunted bodies at Mach 10–20. The band now extends to
   p_b/p∞ = 3 there, which makes the assumed base drag slightly *negative* at the low end.
6. GP surface (reusing `aether.surrogate`), held-out + 5-fold validation, hull guard, G4 guard,
   GCI hook. Registered `cfd_surface_v1`; left it off.
7. After the first pass, 7 of 56 cases had missed the force criterion, three of them hull
   anchors, several by a hair. Added a patience pass — more extensions, **same criterion**
   (NR-09's rule) — and wrote into the config that this was decided after seeing the first
   pass. Some converged; the rest stay rejected (NR-21).
8. The first G5 comparison flagged four of five M4-front designs as outside the hull: the one
   anchor placed for the front had missed it (NR-22). Added three late anchors from the front's
   shape range, appended so that no existing point was renumbered.
9. G5 study: determinism/provenance, constant vs surface on the baseline and five M4-front
   designs, a shape sweep, and sensitivity to everything the surface cannot know.

## Expected

See Hypothesis.

## Observed

Numbers are in the generated report and the tables beside it; deliberately not retyped.

- The hypothesis about levels held: the baseline capsule's C_D falls well below 1.20 and the
  M4-front shape's rises above it, so the two move in opposite directions.
- **Mach independence is weaker than I assumed.** C_D,fore is still changing by a percent or
  more between Mach 10 and 20 for the blunt shapes. Holding the Mach-20 value above Mach 20 —
  where more than half the heat load is — is an approximation of that size, not an identity.
- Base drag: as expected in size; not as expected in sign at high Mach (see Action 5).
- Coarse vs medium on capsule shapes: see report §5.
- The GP is accurate to a couple of percent inside the hull but **somewhat overconfident**
  (predicted 68% intervals cover fewer than 68% of held-out truths); on the 7 usable held-out
  points it is biased low. Tried replacing the cone-angle input with sin²θ (the Newtonian
  variable): k-fold RMSE moved from 0.0326 to 0.0313 on the first-pass table — not worth
  changing a declared input for after having seen the test set. Not adopted.
- After the late anchors went in, the k-fold z-score spread rose to about 1.65: the GP's error
  bars are too narrow. The measured spread is stored with the surface and applied as a sigma
  inflation factor. A recalibration by one number, not a cure.
- Shape now matters through drag, by a lot at the slender end.
- Near-flat-faced and some slender shapes at high Mach hover just outside the 0.1%
  peak-to-peak criterion indefinitely. It looks like a shock-position limit cycle, not slow
  convergence; more iterations do not cure the worst of them.

## Evidence

- `reports/milestones/M3_coupled_model.md` (generated), `reports/figures/M3_*.{png,pdf}`
- `results/M3/M3-DP-20260920T1610Z/` — `design_points_<level>.csv`, `attempts_<level>.csv`
  (every attempt, including crashes and rejected cases), `design_skipped.csv`, per-case force
  histories / dictionaries / log tails under `cases/`, surface validation tables,
  `coupled/` (G5, comparison, shape sweep, sensitivity, Mach bands)
- `data/aero/cfd_surface_v1/` — the persisted surface (training table + pinned kernel)
- `results/M3/smoke-coarse*/` — the smoke tests that found NR-19 and NR-20
- `docs/negative_results.md` NR-19 … NR-22; `ASSUMPTIONS.md` A-CFD-5 (update), A-CFD-9 … 14,
  A-AERO-1, A-AERO-2
- `tests/test_cfd_design_points.py`, `tests/test_aero_surface.py`

## Interpretation

The interesting result is not any C_D value. It is that the constant 1.20 was hiding two
errors of opposite sign, so switching fidelity will not shift the design space uniformly: it
penalises the slender-to-moderate shapes (less drag → deeper, hotter pulse) and mildly rewards
the blunt ones. M4's front was already blunt, so its *ranking* may survive; its *numbers* will
not, and the screening that froze shape variables at Fidelity 0 has to be redone.

What I trust least, in order: (1) the held value above Mach 20; (2) the perfect-gas assumption
at those Mach numbers, which is an argument and not a validation; (3) the coarse mesh;
(4) the GP's error bars. The base-drag band, which I expected to be the weak point, turns out
to matter least.

## Next

- When G4 passes: the GCI hook starts returning a band by itself; rebuild with
  `make aero-surface` and re-run `make m3-coupled` so the artefacts stop saying IN_PROGRESS.
- Coordinator decisions are listed at the end of the M3 report hand-off: medium-mesh re-run
  overnight, whether to extend CFD to Mach 27, and whether the strict convergence rule should
  keep excluding the flat-faced high-Mach corner.
- Then `make doe` (re-derive the screening) and `make optimize` at Fidelity 1.
