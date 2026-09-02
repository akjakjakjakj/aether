# Research story

Dated record of how the question actually developed. Not rewritten to make the result
look predetermined.

---

**2026-08-29 — The question arrives framed.** The capstone specification was issued with
O1 already locked: jointly minimise peak external heat flux and maximum internal
TPS/bondline thermal exposure. The framing — that "cooler is not necessarily safer" —
came from the specification, not from an observation made here. Stating that plainly
matters for the authorship question.

**2026-09-02 — Fidelity 0 built and verified.** Atmosphere, trajectory, heating and
conduction implemented and tested. The conduction solver was verified against the
Carslaw & Jaeger semi-infinite analytical solution to 0.002% before it was used for
anything. Two implementation failures on the way (NR-01, NR-02), one of which would have
understated the project's own result.

**2026-09-02 — The first honest attempt showed nothing.** With a 40 mm TPS the bondline
moved by 9 K across the entire entry. This was not a null result about the physics; it
was a statement that the stack was over-insulated relative to the entry duration.
Resizing to 15 mm — the point where the bondline is actually a design constraint — is
recorded as NR-03, along with the observation that heavy insulation *can* buy the
problem away, at a mass cost.

**2026-09-02 — The result was stronger than the hypothesis required.** H0 asks for the
existence of *one* counterexample pair. What came back was Spearman ρ = −1.000 over the
whole tested domain: peak heat flux and bondline temperature are perfectly
anti-ordered across every candidate. The hypothesis was written to be falsifiable by
finding nothing; instead the entire domain is a counterexample. The reporting was
changed to lead with the rank correlation rather than the single "strongest pair",
because quoting the two endpoints of a monotone sweep as a dramatic pair would overstate
how special they are.

**2026-09-02 — An unplanned result: no feasible design existed at all.** Zero of 27
trajectories satisfied both the deceleration and bondline limits. This was not
anticipated. It reframes M1: the point is not merely that the two metrics disagree, but
that with geometry frozen there is no valid answer for either of them to select. That
observation is what motivated running the geometry axis (M1b) immediately rather than
deferring it to M4.

**2026-09-02 — H1 tested earlier than planned, and supported.** The 2-D grid recovered a
feasible region and produced the comparison the project exists to make: a peak-flux-only
optimiser lands 5.9 K from the bondline allowable, a joint optimiser lands 38.4 K from
it. Both optima sit on the diameter bound, which means the bound is currently doing the
selecting — recorded as an open item rather than presented as a clean optimum.

## Assumptions rejected along the way

- *That the trajectory solve could end at terminal altitude.* False; the bondline peak
  lags (NR-02).
- *That a plausible-looking Pareto plot indicates a correct Pareto implementation.*
  False; the plot is what exposed the bug (NR-04).
- *That a thicker heat shield is a conservative modelling choice.* It is conservative for
  the vehicle and **anti-conservative for the study** — it hides the effect being
  measured (NR-03).
