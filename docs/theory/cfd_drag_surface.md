# The CFD drag surface: design decisions made before the numbers

This note records WHY `cfd_surface_v1` is built the way it is. Results are in the generated
report, `reports/milestones/M3_coupled_model.md`; nothing here is a result.

## What a drag coefficient is doing in this project

The trajectory integrator needs one number per time step: how hard the air pushes back,
`D = q_dyn * C_D * A_ref`. At Fidelity 0 that number is a constant (A-TRAJ-2), which makes the
capsule's shape aerodynamically invisible - only its diameter acts. The surface replaces the
constant with `C_D(Mach, shape)` from CFD, so a blunter or sharper forebody decelerates
differently, flies a different trajectory, and sees a different heat pulse.

## Why Mach 3 to 20, and not the Mach 3 to 6 that M2 validated

Because of where the entry actually happens. For the baseline capsule the heat pulse and the
deceleration pulse both sit far above Mach 6 (the report prints the heat-load share per Mach
band from a baseline run). A surface confined to Mach 3-6 would be accurate where it does not
matter and silent where it does.

The solver can be run at Mach 20 because the perfect-gas Euler equations contain only the
Mach number and gamma - there is no "enthalpy" in them to get wrong. That is also exactly the
limitation: real air at those speeds dissociates, and the perfect-gas shock layer is too hot
and too thick. What survives is the *pressure* on a blunt face, which is set mainly by the
normal momentum flux rho*V^2 (stagnation Cp ~1.84 at gamma = 1.4 against the Newtonian limit
of 2). So the surface is a defensible first-order model of pressure DRAG at hypersonic speed
and of nothing else; the gas-model error is carried as a declared band (A-CFD-1), not hidden.

Two checks keep the extension honest. Every case's stagnation pressure is compared with the
exact Rayleigh-pitot relation, which holds at any Mach number. And Mach-number independence
(Anderson, *Hypersonic and High-Temperature Gas Dynamics*, 2nd ed., section 4.3 - section
title verified against the Library of Congress table of contents; the text was not opened) is
not just cited: the report measures how much C_D,fore still changes between Mach 10 and 20.

Above Mach 20 the Mach-20 value is held (Mach independence). Below Mach 3 the Mach-3 value is
held - a convenience, not physics, tolerable only because almost none of the heating happens
there; the report quantifies both the share and the sensitivity.

## Why not angle of attack

The mesh is an axisymmetric wedge, so alpha = 0 is built in. Spec section 18 asks for C_L
"only if physically required", and a ballistic entry does not require it. The cost is stated:
no lift, no trim, no stability, and no lifting-entry trajectories under this surface.

## Why diameter is not an input

Inviscid perfect-gas flow has no length scale, so C_D depends on shape and Mach only. The
design runs everything at one diameter and checks the claim with one pair of cases at two
diameters.

## Why anchors plus a space-filling fill

A GP must not extrapolate (spec section 25); the guard is the convex hull of the training
points. A hull of interior space-filling points never reaches the corners of the box, and the
M4 front sits in a corner (bluntness about 1.2, cone angle about 69 degrees, shoulder ratio
0.10, squeezed against the geometric-validity boundary). So the valid vertices of the shape
box, points on the validity boundary and named shapes are run at both ends of the Mach range,
and a scrambled-Sobol sequence fills the interior. The price: a failed anchor case removes
its corner from the usable hull, and the report says which.

## Why base drag is a band

See `src/aether/aerodynamics/base_drag.py`. The forebody-only CFD cannot compute it (A-CFD-4,
NR-06). The honest statement of what is known is an interval on the base-pressure ratio with
an exact lower end (vacuum) and a sourced upper end, multiplied by a factor 2/(gamma M^2) that
makes the whole term small at the Mach numbers where the heating happens.
