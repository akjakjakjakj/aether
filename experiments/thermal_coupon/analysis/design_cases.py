#!/usr/bin/env python3
"""Size the matched-energy validation pair against a temperature ceiling, before printing.

    python experiments/thermal_coupon/analysis/design_cases.py \\
        --parameters ../blind_validation/frozen_parameters.yaml \\
        --thickness-m 0.010 --density 1180 \\
        --ceiling-degc 85 --short-s 200 --long-s 800

The M8 experiment is a PAIR of heating histories carrying the SAME integrated energy:

    VAL-A   high peak, short   q_A * t_A = E
    VAL-B   lower peak, long   q_B * t_B = E,   t_B >> t_A

Matching the energy is what makes the pair a clean test. In the re-entry study the
shallow trajectory had both a longer pulse AND a larger integrated load, so the two
effects are confounded there; fixing the energy isolates the DURATION.

What the model predicts, and why it is not a re-entry result
------------------------------------------------------------
At matched energy the model predicts the SHORT pulse leaves the interior HOTTER, which
is the opposite of the project's headline burn-vs-bake ordering. There is no
contradiction: the long case spends longer at elevated temperature and therefore loses
more of the same energy through its two faces before it can diffuse inward. The coupon
tests the model's transient conduction, not the project's trajectory conclusion, and
this script exists partly so that distinction is made with numbers before anyone builds
anything.

The ceiling
-----------
The peak temperature anywhere in the coupon must stay a declared margin below the
polymer's glass-transition or heat-deflection temperature, taken from the datasheet of
the actual spool. `--auto-energy` bisects on the energy to find the largest matched pair
that respects the ceiling in BOTH cases, so the experiment is designed against the limit
rather than discovering it by melting a coupon.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import yaml

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from coupon_model import (  # noqa: E402
    KELVIN_OFFSET,
    CouponGeometry,
    CouponParameters,
    diffusion_time_s,
    predict_sensors,
)


def simulate_pulse(geometry: CouponGeometry, params: CouponParameters, *,
                   flux_w_m2: float, on_s: float, depths_m: np.ndarray,
                   t_initial_k: float, t_ambient_k: float,
                   settle_factor: float = 2.0, n_samples: int = 1201
                   ) -> dict[str, np.ndarray | float]:
    """One rectangular heating pulse, run well past the pulse so the interior peaks.

    The record continues for `settle_factor` diffusion times after the heater goes off,
    because the deepest sensor peaks LATE - the same lag that made the entry model
    under-predict the bondline before the soak-out phase was added (NR-02).
    """
    tau = diffusion_time_s(geometry, params)
    duration = on_s + settle_factor * tau
    t = np.linspace(0.0, duration, n_samples)
    flux = np.where(t <= on_s, flux_w_m2, 0.0)
    temps = predict_sensors(geometry, params, t, flux, depths_m,
                            t_initial_k=t_initial_k, t_ambient_k=t_ambient_k)
    return {
        "time_s": t, "flux_w_m2": flux, "temperature_k": temps,
        "peak_k": temps.max(axis=0),
        "time_to_peak_s": t[temps.argmax(axis=0)],
        "max_anywhere_k": float(temps.max()),
        "energy_j_m2": flux_w_m2 * on_s,
    }


def largest_safe_energy(geometry, params, *, short_s: float, long_s: float,
                        depths_m: np.ndarray, ceiling_k: float, t_initial_k: float,
                        t_ambient_k: float, tolerance_j_m2: float = 5.0e3,
                        max_energy_j_m2: float = 2.0e7) -> float:
    """Bisect on matched energy E so neither case exceeds `ceiling_k` anywhere [J/m^2].

    The short case always binds - same energy in less time is a higher peak - but both
    are evaluated rather than assumed, because a long enough case with a large enough
    loss coefficient could in principle behave otherwise and a silent assumption is how
    a coupon gets melted.
    """
    def hottest(energy: float) -> float:
        return max(
            simulate_pulse(geometry, params, flux_w_m2=energy / short_s, on_s=short_s,
                           depths_m=depths_m, t_initial_k=t_initial_k,
                           t_ambient_k=t_ambient_k)["max_anywhere_k"],
            simulate_pulse(geometry, params, flux_w_m2=energy / long_s, on_s=long_s,
                           depths_m=depths_m, t_initial_k=t_initial_k,
                           t_ambient_k=t_ambient_k)["max_anywhere_k"],
        )

    lo, hi = 0.0, max_energy_j_m2
    if hottest(hi) <= ceiling_k:
        return hi
    while hi - lo > tolerance_j_m2:
        mid = 0.5 * (lo + hi)
        if hottest(mid) <= ceiling_k:
            lo = mid
        else:
            hi = mid
    return lo


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--parameters", default=None,
                    help="calibrated or frozen parameter YAML; omit to use placeholders")
    ap.add_argument("--thickness-m", type=float, default=0.010)
    ap.add_argument("--density", type=float, default=1180.0, help="kg/m^3, MEASURED")
    ap.add_argument("--heated-area-m2", type=float, default=0.060 * 0.060)
    ap.add_argument("--depths-mm", type=float, nargs="+", default=[0.0, 2.0, 5.0, 9.0])
    ap.add_argument("--ceiling-degc", type=float, required=True,
                    help="highest temperature allowed ANYWHERE in the coupon")
    ap.add_argument("--short-s", type=float, default=200.0)
    ap.add_argument("--long-s", type=float, default=800.0)
    ap.add_argument("--energy-mj-m2", type=float, default=None,
                    help="matched integrated energy; omit to solve for the largest safe one")
    ap.add_argument("--ambient-degc", type=float, default=22.0)
    args = ap.parse_args(argv)

    if args.parameters:
        data = yaml.safe_load(Path(args.parameters).read_text())
        params = CouponParameters.from_dict(data["parameters"])
        source = args.parameters
        if data.get("synthetic_inputs"):
            print("*** parameters came from SYNTHETIC data - these numbers are a "
                  "software demonstration, not a plan for a real coupon ***")
    else:
        from synthetic import TRUTH

        params = TRUTH
        source = ("PLACEHOLDER properties from synthetic.py - NOT a measurement of any "
                  "filament. Calibrate first, then re-run this.")

    geometry = CouponGeometry(thickness_m=args.thickness_m, density_kg_m3=args.density,
                              heated_area_m2=args.heated_area_m2)
    depths = np.array(args.depths_mm) / 1e3
    ceiling_k = args.ceiling_degc + KELVIN_OFFSET
    ambient_k = args.ambient_degc + KELVIN_OFFSET
    tau = diffusion_time_s(geometry, params)

    print(f"parameters      {source}")
    print(f"coupon          {args.thickness_m * 1e3:.1f} mm thick, "
          f"{args.density:.0f} kg/m3")
    print(f"diffusion time  L^2/alpha = {tau:.0f} s")
    print(f"pulse durations short {args.short_s:.0f} s = {args.short_s / tau:.2f} tau, "
          f"long {args.long_s:.0f} s = {args.long_s / tau:.2f} tau")
    print(f"ceiling         {args.ceiling_degc:.0f} degC anywhere in the coupon\n")

    if args.long_s <= args.short_s:
        raise SystemExit("--long-s must exceed --short-s or the pair is not a contrast")

    if args.energy_mj_m2 is None:
        energy = largest_safe_energy(
            geometry, params, short_s=args.short_s, long_s=args.long_s, depths_m=depths,
            ceiling_k=ceiling_k, t_initial_k=ambient_k, t_ambient_k=ambient_k)
        print(f"largest matched energy respecting the ceiling: "
              f"{energy / 1e6:.3f} MJ/m2\n")
    else:
        energy = args.energy_mj_m2 * 1e6

    rows = []
    for label, on_s in (("VAL-A (high peak, short)", args.short_s),
                        ("VAL-B (low peak, long)", args.long_s)):
        flux = energy / on_s
        out = simulate_pulse(geometry, params, flux_w_m2=flux, on_s=on_s,
                             depths_m=depths, t_initial_k=ambient_k,
                             t_ambient_k=ambient_k)
        rows.append((label, flux, on_s, out))
        heater_w = flux * args.heated_area_m2
        print(f"{label}")
        print(f"  heater flux   {flux:8.1f} W/m2  for {on_s:5.0f} s  "
              f"({heater_w:.1f} W over {args.heated_area_m2 * 1e4:.0f} cm2)")
        print(f"  record length {out['time_s'][-1]:.0f} s")
        for j, d in enumerate(args.depths_mm):
            print(f"    {d:4.1f} mm  peak {out['peak_k'][j] - KELVIN_OFFSET:6.1f} degC "
                  f"at t = {out['time_to_peak_s'][j]:6.0f} s")
        margin = ceiling_k - out["max_anywhere_k"]
        flag = "OK" if margin > 0 else "*** EXCEEDS CEILING ***"
        print(f"  hottest point {out['max_anywhere_k'] - KELVIN_OFFSET:.1f} degC, "
              f"margin {margin:+.1f} K   {flag}\n")

    deep = len(args.depths_mm) - 1
    a, b = rows[0][3], rows[1][3]
    delta = a["peak_k"][deep] - b["peak_k"][deep]
    print(f"PREDICTION at the deepest sensor ({args.depths_mm[deep]:.1f} mm): "
          f"A is {delta:+.2f} K relative to B.")
    print("This is the falsifiable statement the blind case tests. Archive it with "
          "make_prediction.py BEFORE running either case, and do not adjust the "
          "amplitudes afterwards.")
    if delta > 0:
        print("\nNote the sign: at MATCHED energy the short pulse leaves the interior "
              "hotter, because the long case radiates and convects more of the same "
              "energy away before it diffuses inward. That is the opposite of the "
              "entry-trajectory ordering in M1, where the long case also carried a "
              "LARGER integrated load. Do not quote this as confirming burn-vs-bake.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
