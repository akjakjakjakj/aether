# Defence questions

The final repository must be explainable by the student without AI assistance. These are
the questions to be able to answer cold. Answering "the model said so" is a fail.

## Physics

1. Why does stagnation heating scale as V³ and only as √ρ? What does that imply about
   *when* during an entry peak heating occurs relative to peak deceleration?
2. Why are re-entry capsules blunt? Derive it from the 1/√R_n term and explain the
   physical mechanism behind the correlation.
3. State three assumptions built into Sutton–Graves that would be violated at
   lunar-return speed.
4. Write down the diffusion timescale of the TPS stack. Why does it matter that it is
   comparable to, not much shorter than, the entry duration?
5. Explain in one sentence why a *lower* peak heat flux can produce a *hotter* bondline.
6. Why does the bondline temperature peak after aeroheating has stopped?
7. What is the ballistic coefficient, and why does lowering it move peak deceleration to
   higher altitude?
8. In the 3-DOF equations, where does the term V²cos γ / r come from and what would
   happen if it were dropped?

## Numerics

9. Why is backward Euler used rather than forward Euler? What is the stability limit of
   the explicit scheme for this mesh, and how many timesteps would it force?
10. Why must interface conductivity be a harmonic and not an arithmetic mean? What
    physically goes wrong with the arithmetic version?
11. The radiating boundary condition is nonlinear. How is it handled, and why did the
    first approach diverge?
12. What does the energy-balance residual measure? What value does this solver achieve
    and why is that number so small?
13. Grid convergence was demonstrated. What is the observed order of accuracy in space,
    and does it match theory?
14. What does geopotential altitude mean and why does USSA-76 use it?

## Method

15. Why is `evaluate_design` the only permitted evaluation path?
16. What is a Pareto front? Why must a two-objective front be monotone, and how did that
    fact catch a bug?
17. The M1 sweep reports Spearman ρ = −1.000. Why is that number close to worthless as
    independent evidence, and what *is* the defensible claim from that sweep?
18. Why does an unsourced constraint limit get stored as `null` rather than a large
    number?
19. Which validation rows are `LIMITED` rather than `PASS`, and what specifically is
    missing from each?
20. Why may no CFD result enter the optimisation loop yet?

## Honesty

21. Name the strongest negative result in this project and why it was kept.
22. Which assumptions, if corrected, would *weaken* the headline result? Which would
    strengthen it?
23. Both M1b optima sit on the diameter bound. Why is that a problem, and what would you
    do about it?
23b. Why is "six times the thermal margin" a bad way to report the M1b comparison, and
    what should be reported instead?
24. What did AI contribute to this project, and what did it not?
25. What would falsify H0? What experiment or simulation would you run to try?
