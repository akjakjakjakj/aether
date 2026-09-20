# M2 prototype runs (2026-09-20) - evidence for negative results NR-07 and NR-08

Exploratory runs made BEFORE the validation config was frozen. They are not part of the
gate; they are kept because docs/negative_results.md cites them.

- `forebody_coarse80x60_M3_Co0p5/` - sphere forebody, Mach 3, 80x60 cells, maxCo 0.5,
  6000 iterations. C_D limit cycle; declared convergence criterion NOT met (NR-07).
- `forebody_coarse80x60_M3_Co0p2/` - same mesh, maxCo 0.2, 15000 iterations. Criterion met.
- `mpi_timing/` - last lines of the solver log for 300 iterations on the 320x240 (76 800
  cell) mesh with 1 rank and with 8 MPI ranks (NR-08). Compare the ClockTime lines.

Not preserved: the first full-body prototype (its scratch directory was cleaned before the
decision to keep prototypes was made). It is reproduced inside the audited pipeline as the
`spherefullbody_*` case of the validation run (NR-06).
