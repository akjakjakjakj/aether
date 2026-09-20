# 1. Introduction

*Draft. Does not depend on any pending run.*

A thermal protection system is sized against two different numbers, and the design
literature is explicit about which number does which job. NASA's own aerothermodynamics
training material states the division directly: heat flux, together with pressure and shear,
is used to select the TPS material, while heat load, the time integral of that flux,
determines the thickness [1]. The same source states the consequence for trajectory design
as an exercise with a known answer: "The selection of γ becomes a trade between peak heat
rate (TPS material selection), and total heat load (TPS thickness and mass)", with a steeper
entry giving higher peak heat flux and a shallower one giving higher total heat load [1].

So the trade is known. What is less often stated is where the failure it guards against
actually occurs. A heat shield does not fail at its outer surface, which is designed to get
very hot and to radiate most of the incoming energy straight back out. It fails at the
bondline, the plane where the thermal protection is attached to the structure it is
protecting, and the accepted design criterion there is a maximum temperature at that single
plane, held below an allowable that comes from the structural substrate rather than from the
insulator [1].

That allowable is not a universal constant, and the numbers make the point. The Space Shuttle
Orbiter's aluminium primary structure carried a design temperature limit of 350 °F, which is
449.8 K [2]. The Apollo Command Module's ablator-to-stainless-honeycomb interface was held to
600 °F, 588.7 K [3]. Orion's Avcoat on a composite skin over a titanium skeleton is quoted
against an allowable of 500 °F, 533.2 K [4]. Three flown vehicles, three allowables, each
set by what is behind the heat shield rather than by the heat shield itself.

Now put the two observations together. Peak heat flux is an instantaneous quantity evaluated
at the outer surface. Bondline temperature is what is left after the entire heat pulse has
been filtered by conduction through the stack, and it arrives late, after aeroheating has
stopped, because heat already inside the material keeps diffusing inward. There is no reason
those two should be minimised by the same entry, and a straightforward argument says they
should not be. Stagnation heating goes as V³√ρ, so a shallower entry, which decelerates
higher up in thinner air, has a lower peak. But it also takes much longer, and a longer pulse
delivers more total energy. Whether that matters depends on a single comparison: the
diffusion time of the stack, L²/α, against the duration of the entry. If the stack is much
thicker than the diffusion length √(αt) over an entry, the bondline never learns that the
entry happened. If it is much thinner, the bondline simply tracks the surface. Only when the
two timescales are comparable does the *duration* of the heat pulse change the answer rather
than just its size, and a realistic heat shield sits in exactly that regime, because a
designer who used much more insulation than the thermal problem required would be flying
unnecessary mass.

This project asks what follows from that. Specifically: whether minimising peak external heat
flux alone can select a trajectory that is worse at the bondline, and whether optimising the
peak and the in-depth response jointly finds designs that a sequential procedure would miss.
The objective is stated as a multi-objective problem and kept that way. It is deliberately
not collapsed into a single weighted score, because the weights would then be doing the
engineering.

The approach is to build a reduced-order chain, verify each component against something
outside itself before using it, demonstrate the effect where the model is defensible, and
then add fidelity under an explicit gate: no CFD result may enter the optimisation loop until
mesh independence, force convergence and a published blunt-body comparison have all been
documented. That gate is the reason several results in this paper are reported at reduced
fidelity and labelled as such rather than upgraded on the strength of a solver that runs.

## What this paper claims, and what it does not

The claim is narrow on purpose. Within a verified reduced-order model and a documented set of
assumptions, peak external heat flux and peak bondline temperature are optimised by different
entry trajectories, and a joint objective selects a design with measurably more bondline
margin than a peak-flux-only objective does. Nothing here is a statement about a flight
vehicle, a qualified TPS material, or a flight condition. The aerodynamics at the fidelity
where the headline result was obtained are a constant drag coefficient, and no experimental
validation of any kind exists.

## Provenance of the question

One thing belongs in the introduction rather than in a footnote. The research question, the
locked objective and the three hypotheses were set out in a project specification that the
author received and accepted, and the framing that motivates the whole project, that
minimising peak heat flux may not produce the thermally safest entry, came from that
specification rather than from an observation made during this work. What was done here is
the modelling, the verification, the attempt to falsify, and the decisions about what the
evidence does and does not support. Stating that plainly costs nothing and is the honest
description of the authorship. The full record of how the question then developed, including
the results that were not anticipated, is in the project's research story [5].

---

## Notes for revision

- Reference numbering is local to this section and is reconciled at assembly. [1] is the
  TFAWS course (🟡 T2, opened and read); [2] NASA CR-159900; [3] NASA TN D-7564; [4] Vander
  Kam and Gage; [5] `docs/research_story.md`. Full entries in the Related Work section's
  reference list.
- The paragraph on the three allowables is doing real work and should not be cut for length.
  It is what turns "the bondline matters" from an assertion into a sourced observation, and
  it is also what makes the project's own 450 K placeholder defensible later, conditionally
  on the structure being aluminium-like.
- Do not add a sentence about optimisation methods, surrogates or AI to this section. The
  first mention of any of those belongs in Methods. Spec §51's rule about public-facing
  material leading with the scientific question applies here for the same reason.
- If an orienting figure is wanted, `reports/figures/M1_temperature_field.png` shows the
  depth-versus-time temperature field and makes the surface-versus-bondline distinction
  visible in one image.
