---
audited_run: M5-ABL-20260920T211134Z
---

**What was read, and how.** The stated `mechanism` of all 67 rounds (47 `ai_agent`, 20
`ai_adaptive`) and the full `observation` / `evidence` / `mechanism` / `uncertainty` of 25 of
them (every round of seeds 37 and 41; the first three or four and the last of seeds 59, 67
and 73), from the raw responses under `results/M5/M5-ABL-20260920T211134Z/llm/`. The counts
below are produced by read-only scripts kept beside the run
(`results/M5/M5-ABL-20260920T211134Z/audit/*.py`, outputs `*.json`, verbatim text in
`rounds_digest.md`); they read `agent_log.json` and `candidates.csv` and evaluate nothing.
The LLM's text was treated as data throughout. The yardstick is what M4 established on this
physics (`M4_pareto_optimisation.md` §11, §11a): entry angle is the only variable that trades
the two objectives; diameter and bluntness are free improvements until the mass-fraction
fence and the CFD-hull edge; the cone angle decides validity, not heating; C_D at peak
heating is flat across the front; the shoulder is frozen.

### 1. Did it find the structure M4 found? Yes, in every seed, within three to five rounds

By its third to fifth call every seed states M4's §11a conclusion in its own words. Seed 37,
call 5: *"The feasible front is a one-dimensional curve traced by flight-path angle at
D~3.375-3.38 m, bluntness 1.2, cone 70 deg."* Seed 41, call 3: *"The front is closed on the
steep side by max_g … and on the large-D side by heatshield mass fraction."* It names all
three stops correctly and separately: diameter by the mass fraction (*"behaves like
1-k·D^2"*), bluntness by the drag surface's hull (*"Bluntness 1.205 and above at cone 70
fails the cd_fore convex-hull check"*), entry angle by the g-limit near −3.57°. A crude
keyword scan finds the one-parameter-front statement in 27 of 47 `ai_agent` rounds, the
mass-fraction cap in 45 and the hull or extrapolation fence in 39. The pooled `ai_agent`
fronts agree with the words: 362 front designs, all at bluntness 1.2 and cone 70°, diameter
3.380–3.38523 m, entry angle −3.57035° to −1.5°. M4's front after 1000 evaluations sat at
3.355–3.376 m, bluntness 1.15–1.199, entry angle −3.565° to −1.502°: the same corner, less
tightly parked.

### 2. Inferred from the data, or asserted from priors? Both, and it mostly says which

*From priors, and labelled as such.* The **direction** of every lever was stated in round 1,
before a seed had more than three feasible designs (seed 41 and 67 had none). Thirty-five of
47 rounds say so explicitly, 12 naming Allen–Eggers and 9 Sutton–Graves: *"This relies on
prior Allen-Eggers-type scaling, calibrated to the data"* (seed 59, call 1); *"I am relying
on ballistic-entry scaling from prior knowledge for the sign and size of some trends"* (seed
37, call 1). Those first-round proposals, made on priors plus 20 space-filling rows, already
had the direction of change right on 88 of 95 stated flux directions and 86 of 93 bondline
directions. That is the contamination point in one number, and it should be read plainly:
**the agent starts where the other optimisers have to get to.** NSGA-II and the Bayesian
optimiser see four unnamed numbers; the LLM sees the words "bluntness", "flight path angle"
and "bondline" and has read the entry-heating literature. Its lead at 50 evaluations is a
measurement of *priors plus data*, not of reasoning from data alone, and this study cannot
separate the two.

*From the data, and could not have come from anywhere else.* (i) The constraint limits,
back-computed from the margins in round 1 (12 g, 450 K). (ii) The geometric validity rule:
seeds 37, 41 and 67 each derived, in round 1, from the negative cone lengths in the
validator's failure messages, the closed form (bluntness − 0.1)·cos(cone half-angle) ≤ 0.4.
Checked against this run's log, that rule agrees with the evaluator on **all 5400 paid
designs of all methods** (1362 invalid, no false alarm, no miss). No numeric optimiser is
given that rule (A-AI-2); the agent read it off ten or eleven error messages. This is the
failure-message asymmetry the report's §2 declares, and it is large. (iii) The CFD-hull
fence, which no prior could supply: discovered from the `cd_fore` extrapolation refusals by
call 2 or 3 in every seed and then probed at 1.205, 1.21, 1.22. (iv) The numbers: the D²
mass-fraction law, ≈1.65 g per degree, ≈−18 K per metre of diameter. (v) That 1 K of
bondline is worth far more hypervolume than 10 kW/m² of flux, computed from the reference
point in the prompt in 10 rounds — the agent optimised the *meter* knowingly, which is what
it was asked to do and is also why it parks where it parks (§4).

*Asserted and not supported by this model.* *"Large cone angle raises drag"* / *"a large
blunt 70° cone gives the highest drag coefficient"* appears in a handful of rounds as a
reason for the corner. Across the space-filling data C_D at peak heating does rise with
cone angle (Spearman 0.97 in `lhs_search`), so the prior is not wrong about the box; but
C_D is never shown to the agent, and on its own front it spans 1.36439–1.36446, i.e. it
explains nothing there. M4's reading (the cone angle is held at 70° by validity and the
bound, not by drag) is the supported one. Likewise *"High cone angle also reduces heatshield
area, which buys diameter"* (seed 41) is asserted; M4's Sobol' index of cone angle on the
mass fraction is 0.0005. Neither claim changed where the agent went.

*Never said.* In 67 rounds the agent did not once question whether a limit was physically
meaningful. It treated the mass-fraction constraint as a wall to be approached to within
10⁻⁵, never as a sign that a shield weighing as much as the vehicle is not a vehicle — the
point M4 §11a makes in its first sentence. It was not told the limit's value or meaning, so
this is a limit of what it was shown as much as of the model; but an engineer reading
"heatshield_mass_fraction margin 1.5e-5" would have asked. The shoulder appears only as a
term in its geometry formula. Fidelity 1 was requested on 24 of 900 accepted proposals.

### 3. Were its predictions borne out?

Scored for every accepted `ai_agent` proposal whose parent and child both returned physics.
A direction counts as stated when the predicted change from the parent's simulated value
exceeds 0.5 % (flux) or 0.5 K (bondline); inside that band the agent is read as predicting
"about the same" (230 and 177 proposals respectively) and is not scored.

| | stated | right | wrong | right |
|---|---|---|---|---|
| peak heat flux, direction vs parent | 604 | 596 | 8 | 98.7 % |
| peak bondline temperature, direction vs parent | 657 | 649 | 8 | 98.8 % |
| both directions stated | 577 | 562 both right | 14 one, 1 neither | 97.4 % |

All 16 wrong directions are in rounds 1 and 2; from round 3 on there is not one. That is
less impressive than it looks and should not be quoted without this sentence: from round 3
most proposals are interpolations in entry angle between two evaluated neighbours on a
smooth monotone curve, where the direction is given. The median absolute error of its
numeric predictions falls from 6.9 % of flux and 3.3 K in round 1 to below 0.01 % and
about 0.02 K by round 5. The informative figure is round 1 (≈ 93 % right on priors and 20 rows).
Stated uncertainty was informative: all 345 proposals marked "low" had both directions
right; all 15 misses were marked "medium" or "high".

**Feasibility is where it was overconfident.** It predicted "feasible" for 892 of 900
proposals; 813 were (`summary.json`: 90.6 % accuracy). Of the misses, 65 returned no
physics at all, and **20 of those are one round**: seed 37, call 2. In round 1 that seed had
the exact validity rule. The prompt's digest of earlier rounds carries only the first 400
characters of the *mechanism*, not the observation where the rule lived; in round 2 the
agent refitted a looser rule (*"cos(theta)*(about 1.86*b - 0.1) < 0.9 … so it should be
buildable"*), sent all 20 proposals to bluntness 1.25–1.35 with every one marked feasible,
none hedged, and gained nothing (hypervolume 0.33115 before and after). The next round
opens: *"All 20 round-2 proposals were wasted on the invalid corner."* `ai_adaptive` seed
37, a fresh sample on the same initial design, lost 18 of 20 in the same round the same
way. Two samples are not a rate, but it is the failure the notebook predicted (proposals
just past a boundary it aims at on purpose), made worse by a harness choice about what the
agent is allowed to remember.

### 4. Rejections, and what the hypervolume is made of

**37 of 937 proposals were rejected (3.9 %): 36 duplicates of a design already evaluated
and 1 identical to its parent. None was out of bounds, malformed, off-schema or attached to
an unknown parent; no response was malformed and no call failed**, so no budget went to the
LHS fallback. The duplicates come from the truncated tables (12 front rows shown of up to
85): the agent cannot see every design it has evaluated, says so (*"some proposed gammas may
duplicate rows not shown to me"*), and by round 9 was choosing *"three-decimal values ending
in 5 to reduce that risk"* — avoiding the cache, not exploiting it. There were no cache hits.

The agent is the most precise fence-parker in the study. 64 % of its front designs have a
mass-fraction margin below 10⁻⁴ (smallest 9 × 10⁻⁶) against none of `bo_parego`'s; it walks
the diameter 3.384 → 3.385 → 3.3852 → 3.38523 m for gains it prices itself at ~10⁻⁵ of
hypervolume. Recomputing per-seed hypervolume after dropping every design within 0.1 % of
any constraint gives `ai_agent` 0.3539 and `bo_parego` 0.3519: the agent's final lead
shrinks from 0.0036 to 0.0020, so a little under half of it is precision on two limits that
M4 labels a logical fence (mass fraction) and unsourceable (12 g). With a 1 % stand-off it
is 0.3446 against 0.3380. The rest of the lead is coverage: 72 front points per seed along
the entry-angle curve against the Bayesian optimiser's 8. The lower design diversity
(0.31 against 0.60 for `bo_parego`) is the same fact seen from the other side, and is what
the notebook predicted: once it believed its model it stopped looking elsewhere, apart from
a few labelled probes a round, none of which moved the corner.

**Hull edge and near-repeats (two checks the generated §8 does not make;
`audit/hull_and_near_repeats.py`).** The drag surface evaluated bluntness 1.200 at cone 70°
and refused 1.201: that is the CFD-hull edge on this front, and it is where CFD happened to
be run, not physics (M4 §11 (ii)). **Every one of the agent's 362 front designs sits on it**
(bluntness exactly 1.2); 18 % of `bo_parego`'s 39 are within 0.01 of it (largest 1.1989);
no NSGA-II or LHS front design is. Finding the edge cost the agent 40 refused evaluations
over five seeds, `bo_parego` 23, the others at most 1. §8 also counts 195 *near-repeats* for
`ai_agent` (a paid design within 10⁻³ of an earlier one in the unit cube) against 0 for
`bo_parego`, and describes the pattern as a way round the cache. Here it is not cache-dodging
(there is no cached result to dodge; each is a new design) but fence-polishing: the same
entry angles re-bought at a diameter 0.2–1 mm larger, and entry-angle steps of 10⁻⁴ degrees at
the g-limit. Removing every near-repeat lowers the agent's mean hypervolume from 0.35557 to
0.35517: about a fifth of its budget bought 0.0004. That is the agent gaming the meter in
the literal sense: legal, declared, scored by the rules, and worth nothing as engineering.

### 5. Verdict of the audit

On this problem the agent behaved like a competent engineer with a textbook: it brought the
right directions from prior knowledge and usually said so, extracted from the data the
things only the data held (limits, the validity rule, the hull fence, the slopes), reached
M4's structural reading of the front in three to five rounds, and then spent more than half
of its budget polishing a one-parameter curve against two placeholder limits without ever
asking whether they were real. It was wrong where it was most confident about geometry it
had not yet seen. Nothing here shows it found a design or a lever that M4's NSGA-II, given
five times the evaluations, did not; what it did was arrive sooner and park closer. The
landscape is easy (one real trade-off, monotone free improvements), which is the most
favourable case for prior knowledge; this audit says nothing about a problem where the
textbook direction is wrong.

### 6. Three sentences of the generated report that need a caveat for this run

The report body is generated and was not edited; the generator lives under `src/aether`,
which was frozen while three studies ran. For this run, read it with these corrections
(recorded as NR-31):

1. **"CFD calls" (§3 table, and "CFD-backed" in the header) is not a count of CFD runs.** No
   CFD solver ran during M5. The column counts paid evaluations that returned physics through
   the CFD-derived drag surface `cfd_surface_v2` (the evaluator labels those fidelity 1);
   the remainder are designs refused before any physics. CFD solver calls made by M5: 0.
2. **"`ai_adaptive` … F0 only" / "every candidate was evaluated at Fidelity 0" (§3, §6) is a
   pre-written sentence that is no longer true as worded.** Every `ai_adaptive` candidate was
   evaluated by the same Fidelity-1 surface as every other method. What remains true is what
   the sentence meant: no promotion to a *new CFD case* was available or granted (0 of 360
   decisions), so the row is plumbing and is excluded from every comparison.
3. **"A 'no measured difference' … means this study could not tell them apart" (§4) does
   not describe the 200-evaluation cell.** There the exact test rejects at its floor
   (p = 1/252, Holm 0.0119; all five agent seeds above all five `bo_parego` seeds, A12 = 1.00).
   The verdict is "no measured difference" because the mean gain, +0.0036, is below the
   pre-declared practical threshold of 0.005 - the rule's effect-size leg, not its
   significance leg. The rule is applied as written; the agent was *distinguishably* ahead
   at 200 evaluations by an amount declared in advance to be too small to count.
