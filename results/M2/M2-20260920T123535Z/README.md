# Aborted run - kept as evidence for negative result NR-09

First launch of the M2 validation study. Stopped by hand after the two coarse cases because
`sphere_M3_coarse` missed the declared force-convergence criterion on DRIFT
(see its case_result.json) with a fixed iteration count. The pipeline was then given
run-until-converged logic and the study was restarted under a new run ID with a new config
snapshot. Nothing from this directory is used in the M2 report.
