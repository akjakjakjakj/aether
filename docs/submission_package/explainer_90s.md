# 90-second technical explainer — script

Spec §51. Spoken, by the student, to camera or to a person. Target 220–240 words, which is
about 90 seconds at a natural pace. Not read off a card.

**Status: skeleton.** The physics half is final. The result half depends on which studies
have run; `[PENDING FINAL RUN]` marks what cannot be said yet.

---

## Script

**[0:00–0:18] The setup.** *(final)*

> When a spacecraft comes back through the atmosphere, the thing everybody designs against is
> peak heat flux. The single worst instant of heating on the outside of the heat shield.
> That is the number that picks the material.
>
> But the heat shield does not fail on the outside. It fails at the bondline, where the
> shield is glued to the structure underneath.

**[0:18–0:40] Why that changes the problem.** *(final)*

> And the bondline does not care about the worst instant. It cares about how much heat got
> through, and how long it had to soak in. Heat takes time to diffuse through an insulator,
> and in a real heat shield that time is about the same as the length of the entry.
>
> So you can have a shallower entry that is cooler on the surface, and hotter where it
> actually matters.

**[0:40–1:05] What was found.** *(numbers final; from `reports/milestones/M1_burn_vs_bake.md`)*

> I built a model of that. Atmosphere, trajectory, heating, and heat conduction through the
> shield, and I checked each piece against published results before I used it. The
> conduction solver matches an analytical solution to two thousandths of a percent.
>
> Then I swept the entry angle. The shallowest entry I tested cut peak heat flux by
> thirty-eight percent, and ran the bondline a hundred and fourteen kelvin hotter. Every
> single step that made the surface cooler made the inside hotter. There is no angle in
> between where you win on both.

**[1:05–1:25] The part that surprised me.** *(final)*

> The thing I did not expect: with the shape fixed, nothing was feasible at all. Steep
> entries broke the deceleration limit, shallow ones broke the bondline limit, and nothing
> in between passed both. You cannot fix this by flying differently. You have to change the
> vehicle and the trajectory together, and when I did, the joint optimum ran thirty-two
> kelvin cooler at the bondline than the design you get from optimising the peak alone.

**[1:25–1:30] The honest close.** *(final, not optional)*

> That is a model result, with the drag coefficient held constant and no experiment behind
> it yet. It says where the trade lives. It does not say anything about a real vehicle.

---

## Delivery notes

- **Do not open with software, AI, or the framework.** Spec §51. The first sentence is about
  heat shields.
- **"Bondline" needs no definition beyond the one in the script.** "Where the shield is glued
  to the structure" is enough, and it is accurate.
- The strongest 15 seconds is the feasibility squeeze. It is the one moment where the
  listener hears something being *discovered* rather than confirmed, and it is true: it was
  not anticipated.
- **Do not say "perfectly anti-correlated" or quote ρ = −1.000.** Say "every step that made
  the surface cooler made the inside hotter", which is the same fact without the
  near-tautological statistic.
- **Do not quote a margin ratio.** Thirty-two kelvin.
- The close is not a disclaimer to be rushed. Say it at the same pace as the rest.

---

## If asked follow-up questions

The three most likely, with 20-second answers:

**"Why doesn't the heat just radiate away?"** It does, and that is exactly the mechanism.
Radiation goes as the fourth power of surface temperature, so a hot surface sheds heat very
efficiently. A short hard pulse drives the surface hot, and most of that energy leaves again
before it can diffuse inward. A long mild pulse never gets the surface hot enough to shed it
that fast, so more of it goes in.

**"Isn't the answer just a thicker heat shield?"** Yes, and that is recorded as a negative
result. At 40 mm the bondline moved nine kelvin over an entire entry: the effect can be
insulated away. But that is all mass, and nobody flies two and a half times more insulation
than the thermal problem needs. The result is about where the interesting trade lives, not
that every vehicle is at risk.

**"How do you know your model is right?"** I do not know it is right; I know what it has been
checked against, and there is a matrix that says which rows are checked and which are not.
The conduction solver is checked against an analytical solution. The trajectory integrator
reproduces a published comparison. The CFD gate has not passed and I have not run the
experiment. `[PENDING FINAL RUN]` for the uncertainty numbers.

---

## Variant: 60 seconds

Cut the verification sentence from the third beat and the whole fourth beat. Keep the setup,
the mechanism, the 38%/114 K result and the close. Never cut the close.
