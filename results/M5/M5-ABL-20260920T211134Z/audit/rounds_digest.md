## ai_adaptive seed_37 call_01  (20 proposals, 1 ask fidelity 1)

**observation:** Only 2 of 20 evaluated designs are feasible, and only C-ca305253716b is non-dominated (flux 345120 W/m2, Tbond 406.56 K). Eleven of the 20 failed on geometry, so the hypervolume is mostly limited by wasted slots and by the max_g limit (12 g), which caps how steep the entry angle can be. I backed out the constraint limits from the margins: max_g 12, bondline 450 K, and heatshield mass fraction roughly 0.09*D^2 relative to its limit, so D is capped near 3.3 m. The geometry failures are consistent with nose radius = bluntness*D and shoulder radius = 0.1*D. Fore-cone length is then proportional to 0.4 - (b-0.1)*cos(theta), so a design is valid only if (b-0.1)*cos(theta) < 0.4. The formula reproduces the reported negative lengths for C-892b8b20e709 and C-c170e00795a8. I keep it below about 0.38 in every proposal. Bluntness above 0.9 needs a cone half-angle of 60 deg or more.

**evidence:**
- Geometry: C-c170e00795a8 (b=0.929, 53.06 deg gives 0.4985), C-892b8b20e709 (0.608) and C-77238b231f4a fail. C-ca305253716b (0.367), C-30ab3c9fdbef (0.362) and C-f1dfaff79f31 (0.246) are valid, consistent with a 0.4 threshold.
- max_g: 9.85 at gamma=-2.32 (C-30ab3c9fdbef), 11.20 at -3.16 (C-ca305253716b), 13.57 at -4.54 (C-7e930f570744). This fits g ~ 6.1 + 1.63*|gamma| for large D, so the g limit of 12 allows |gamma| up to about 3.6 deg. Small-D designs (C-7139ecfe995b, C-6c8d751b6b54) run 1-1.5 g higher.
- Mass fraction: margins of 0.185 (D=3.007), 0.171 (D=3.044), 0.452 (D=2.48), -0.37 (D=3.74) and -0.77 (D=4.33) scale as D^2. Zero margin falls near D~3.3-3.35 m.
- Scaling fitted to the rows: flux falls with D and with nose radius, and rises only weakly with |gamma| (C-7e930f570744 vs C-ca305253716b, C-1d847642b793). Bondline temperature (T-300) scales roughly as D^-0.5 * sin(gamma)^-0.35 with almost no dependence on nose radius, so steeper entry lowers T (C-1d847642b793 372 K, C-0a0993b4b67b 374 K). Larger bluntness at high cone angle therefore lowers flux without raising T.
- Small-D designs (C-6c8d751b6b54: 2.63e6 W/m2, 510 K; C-7139ecfe995b) are far worse on both objectives and infeasible, so the useful region is D ~3.0-3.35 m, gamma ~ -3.3 to -3.6 deg, with high bluntness and cone angle.

**mechanism:** Bigger diameter lowers ballistic coefficient, so peak density and heat load fall. A larger nose radius (bluntness*D) cuts stagnation-point flux roughly as 1/sqrt(Rn). Steeper entry shortens the heating pulse and lowers the integrated load that drives bondline temperature, but raises peak deceleration, which max_g caps near gamma ~ -3.6 deg. Large cone angle raises drag and gives room for high bluntness within the geometry limit. Heatshield mass fraction grows with D^2 and is the binding constraint at the large-D end. Tbond has the larger effect on hypervolume, since each 10 K is worth about 0.067 of the normalised T axis, so I push toward the steepest gamma that keeps g under 12, the largest allowed D, and high bluntness. Some proposals probe the g and mass-fraction boundaries and single-variable effects (bluntness, cone angle, gamma) to calibrate the model.

**uncertainty:** The scaling exponents and the g and mass-fraction fits come from 9 valid points, so the numeric predictions are rough (about +/-10% on flux, +/-5 K on T). Geometry validity assumes Rn=b*D and Rs=0.1*D, fitted to two failure lengths, and there may be other minimum-length rules. I do not know how cone angle enters drag, g or mass fraction, and proposals at D>=3.3 or gamma <= -3.55 may fail max_g or mass fraction.

## ai_adaptive seed_37 call_02  (20 proposals, 1 ask fidelity 1)

**observation:** The feasible front has one point, C-05ff421c45e2 (279k W/m2, 394.04 K). The normalised hypervolume of 0.331 matches that point exactly. The temperature axis dominates the score, because 1 K is worth roughly 15 times more than 10k W/m2. The feasible region is a narrow cluster near D 3.0-3.37 m, bluntness 1.0-1.25, cone 66-70 deg and gamma -3.1 to -3.6 deg. Three constraints bound it. max_g <= 12 sets a steepest gamma of about -3.58 deg. Heatshield mass fraction caps D at about 3.38 m at high bluntness and cone angle. Geometry validity caps bluntness at about 0.4/cos(cone)+0.1, which is 1.27 at 70 deg. Steeper gamma, larger D and higher bluntness all lower both objectives, so the best remaining move is to push toward the corner where all three limits meet.

**evidence:**
- C-3583b7488cf2 (D3.3, bl1.2, c70, gamma -3.6) has the lowest temperature of any near-feasible candidate at 392.29 K and 285.6k, but g=12.016 fails the limit by 0.1%. C-dcc8aaeb364a (gamma -3.55) gives g=11.921, so the g limit sits near gamma -3.58 to -3.59.
- C-05ff421c45e2 (D3.35, bl1.1) has mass margin 0.0179. C-0d18a7fb8799 (D3.3, bl1.15) has 0.048, C-15107d6a0298 (D3.2, bl1.2) has 0.106 and C-613443d901da (D3.0069) has 0.209. Margin falls about 0.6 per metre of D, so D is capped near 3.37-3.38.
- C-3a694f0320f1 and C-dcc8aaeb364a differ only in gamma (-3.4 vs -3.55). Mass margin is identical at 0.04787, so mass fraction does not depend on gamma. Temperature falls about 1.1 K per 0.1 deg of steeper gamma. Flux rises only about 2.8k per 0.1 deg.
- Geometry failures such as C-892b8b20e709 and C-a91d9ef63c92 fit an axial cone length of (0.4 + 0.1cos(theta) - bl*cos(theta))*D / tan(theta). I checked this against the failure messages (-369 vs -367 mm, -2983 vs -2984 mm). bl=1.24 at cone 70 is valid, with a positive length of about 12 mm.
- Flux falls with bluntness and D. C-3583b7488cf2 (bl1.2, D3.3) and C-0d18a7fb8799 (bl1.15) show about -3k per +0.05 bl. C-05ff421c45e2 (D3.35) has the lowest flux at 279k.

**mechanism:** Peak deceleration in a ballistic entry is roughly independent of ballistic coefficient, so max_g is set mainly by gamma (my prior knowledge, consistent with the g values in the table). That makes about -3.58 deg the steepest allowed entry. Steeper entry shortens the heat pulse and lowers bondline temperature. A larger diameter lowers ballistic coefficient and raises the nose radius, which cuts flux and temperature, but heatshield mass fraction limits D. Higher bluntness and cone angle reduce flux and slightly help mass margin. The best corner is therefore D about 3.30-3.37, bluntness 1.24-1.25, cone 70 deg and gamma about -3.55 to -3.58. I also add a few shallow-gamma, low-flux points to spread the front along the flux axis.

**uncertainty:** The g-limit is close to the gamma range I probe, so several proposals with gamma between -3.55 and -3.585 could fail max_g by 0.1-0.5%. Mass margin at D 3.36-3.37 is predicted to be only about 0.01 and could turn negative. My sensitivities are rough finite differences from confounded rows. The geometry-validity rule is fitted to only two failures, and bl 1.25 at cone 70 leaves only about 8 mm of fore-cone length. Predicted temperature gains are small (1-3 K).

## ai_adaptive seed_37 call_03  (20 proposals, 0 ask fidelity 1)

**observation:** Round 2 lost 18 of 20 evaluations to 'aero surface extrapolation' failures. Every failure has bluntness >= 1.24 at cone 70, plus (1.2, cone 69). All the successful high-bluntness points sit at cone 70 with bluntness <= 1.2, or at (1.12, cone 68). The valid region for the cd_fore surrogate therefore ends at bluntness ~1.2 on the cone=70 edge, and inside that the edge runs roughly from (1.12, 68) to (1.2, 70). The feasible front is only 3 points, clustered at ~280-290 kW/m2 and ~393-394 K. Bondline temperature has the larger hypervolume leverage: 1 K is worth about as much as ~40 kW/m2 of flux. The binding constraints are max_g (limit 12, near gamma ~ -3.58) and heatshield mass fraction (limit reached near D ~3.38). The nearly feasible C-3583b7488cf2 (b=1.2, cone 70, gamma -3.6) has the lowest temperature (392.3 K) and fails max_g by only 0.13%.

**evidence:**
- C-3583b7488cf2: b=1.2, cone 70, D=3.3, gamma -3.6 gives 285.6 kW/m2, 392.29 K, g=12.016, so it is infeasible by 0.13%. Gamma -3.58 should be just feasible.
- g rises about 1.7 g/deg of steepening: C-05ff421c45e2 (gamma -3.4) gives 11.70 g and C-b57da803fe39 (gamma -3.55) gives 11.95 g. That puts the g limit near gamma -3.58 to -3.59.
- Mass-fraction margin falls as D grows: D=3.3 gives 0.046-0.050 (C-bd537396e7e1, C-3583b7488cf2), D=3.35 gives 0.015-0.018 (C-05ff421c45e2, C-b57da803fe39), and D=3.74 gives -0.37 (C-0a0993b4b67b). That is about 0.6-0.9 per metre, so D <= ~3.37 is needed.
- Every one of the 18 round-2 failures (e.g. C-ec5c054f9438, C-460ff98d4dde) has b>=1.24, or b=1.2 with cone 69. These are all outside the hull, while C-3583b7488cf2 (1.2, cone 70) is valid.
- Shallower gamma lowers flux and raises temperature: C-05ff421c45e2 (-3.4) has 279k and 394.0 K, versus C-b57da803fe39 (-3.55) at 288.5k and 393.2 K. This supports a few shallow-gamma points to spread the front.

**mechanism:** Peak flux scales roughly as sqrt(rho_peak/Rn), with rho_peak proportional to ballistic coefficient times sin(gamma). Flux therefore falls with a larger D (about D^-1.5), with a larger nose radius (higher bluntness), and with a shallower gamma. Bondline temperature follows the integrated heat load. Steeper entry shortens the pulse and lowers temperature, until the max_g cap is hit at about -3.58 deg. Maximum cone angle (70) and bluntness of about 1.2 minimise both objectives, and D is pushed to the mass-fraction limit near 3.36-3.38. I stay strictly inside the known-valid bluntness/cone region (cone 70 with b<=1.2, plus a few interior points). I probe b=1.22 once to locate the hull edge. A handful of shallow-gamma points at b=1.2 extend the front toward low flux. Flux and temperature predictions come from a simple scaling anchored on C-3583b7488cf2, which is prior-knowledge physics, not a fit.

**uncertainty:** The exact hull boundary between b=1.2 and b=1.24 at cone 70 is unknown, so the b=1.22 probe may fail. The g margin near gamma -3.58 is about 0.2% and depends slightly on b and D, so some steep-gamma points may narrowly fail. The mass-fraction margin at D >= 3.37 is extrapolated from few points and may depend on gamma through heat load. The temperature rise at very shallow gamma (-2 to -3) is extrapolated with high uncertainty.

## ai_adaptive seed_37 call_04  (20 proposals, 0 ask fidelity 1)

**observation:** The feasible front is a one-dimensional curve in flight_path_angle. It sits in the corner of the design box at bluntness 1.2, cone 70 and D about 3.35 (fluxes 241k-276k W/m2, bondline temperatures 391-411 K). Three constraints bind. max_g caps gamma near -3.57 deg. The heatshield mass fraction caps D near 3.385 m. The aero surrogate's convex hull caps bluntness and cone. Every geometry failure has bluntness >= 1.22 at cone 70, or cone 69 with bluntness 1.2. Normalised hypervolume is dominated by the temperature axis (150 K span against a 2.5e6 W/m2 flux span), so the main remaining gains are a slightly larger D at the mass limit, plus extending the front to shallow gamma.

**evidence:**
- Fixed D=3.35, bluntness 1.2, cone 70, gamma swept from -2.0 to -3.45 (C-3cfec4d90b09, C-4370b59bae5e, C-e6138656a3bd, C-a51f1ded896c, C-15eefd667953): flux 241k->276k, temperature 410.7->392.9 K, g 9.72->11.79. Steeper entry lowers temperature at the cost of flux and g.
- Gamma -3.58, bluntness 1.2, cone 70, D swept from 3.30 to 3.38 (C-363a563b3536, C-492a26649e0e, C-764c593a20a3, C-6146d28a8413, C-2a109f1c4205, C-053e6577c074): flux falls 285.1k->275.4k (about -1.2k per 0.01 m) and temperature 392.49->391.08 K, so larger D is better on both objectives. g rises only about 0.004 per 0.01 m.
- Mass-fraction margin: 0.0207 at D=3.35, 0.0149 at 3.36, 0.0090 at 3.37, 0.0031 at 3.38 (C-3e5fe5688040, C-053e6577c074). That is about -0.0059 per 0.01 m, so the limit is D of about 3.385.
- g is close to 12.0 at C-6146d28a8413 (-3.58, D 3.35), C-3e5fe5688040 (-3.57, D 3.37) and C-c4095cf95503 (-3.5, D 3.35, 11.869). This gives about 1.66 g per deg, so at D of about 3.383 the gamma limit is roughly -3.57.
- Geometry failures C-35e288c12205, C-11ae4eb65bbb, C-f414065c6995, C-02c5b1aac369, C-660a8eef4199, C-f933198e1835 and C-02bec3a7a6f4 all have bluntness >= 1.22 at cone 70. C-460ff98d4dde (cone 69, bluntness 1.2) also fails. Lower bluntness or smaller D are worse: C-d883f15f56c5 (bluntness 1.05) has higher flux, and C-7139ecfe995b and C-6c8d751b6b54 (D about 1.2-1.4) have flux 1.8-2.6e6 and violate temperature.

**mechanism:** Peak flux scales roughly as sqrt(rho_peak/Rn), so larger D and a larger nose radius lower it. Bondline temperature follows the integrated heat load, which a steeper entry lowers by shortening the pulse. Peak g is set mainly by gamma. The optimum therefore sits where the mass-fraction limit (D about 3.385) and the g limit (gamma about -3.57) meet, at the highest bluntness and cone angle the surrogate hull allows. This is the prior-knowledge picture, and the tabulated trends agree with it. I stay on the known-safe edge (bluntness 1.2, cone 70), and move D from 3.35 to about 3.383 to shift the whole front down in both objectives. I also sweep gamma from -1.5 to -3.565 to extend the front to low flux and to densify it, since a shallower entry trades temperature for flux.

**uncertainty:** Values at gamma shallower than -2.0 are extrapolated (about -1.5 to -1.9), so temperature and flux there may be off by several K or several percent. The D=3.384-3.385 points sit within about 0.001 of the mass-fraction limit, and the g margin at gamma -3.565 to -3.56 is only about 0.01. Either could tip a point to infeasible. The hull boundary of the aero surrogate is not known precisely, so I did not try bluntness > 1.2 or cone < 70 with bluntness 1.2. I did not test any different region of the design space, so a better basin may exist that I have no data on.

## ai_adaptive seed_37 call_05  (20 proposals, 0 ask fidelity 1)

**observation:** All 12 feasible non-dominated designs sit at the same corner: bluntness 1.2, cone 70 deg, D about 3.383-3.385 m. Only flight_path_angle varies along the front, from -1.5 deg (227k W/m2, 418 K) to -3.565 deg (274.6k W/m2, 391.2 K). Two constraints pin the corner. Heatshield mass fraction runs out at D about 3.385 m (margin falls roughly 0.6 per metre of D). max_g runs out at gamma about -3.57 deg. Eight of the geometry failures come from bluntness above 1.2 at cone 70, or from cone 69 at bluntness 1.2, so the aero surrogate's convex hull ends there. Round 2 wasted 18 evaluations by probing outside it.

**evidence:**
- C-fb90f652dec5 through C-f71f4a44911d: on the front, flux rises and bondline temperature falls monotonically as gamma steepens at fixed D of about 3.383, b 1.2, cone 70.
- C-3583b7488cf2, C-2a109f1c4205 and C-053e6577c074 (all gamma -3.58/-3.6): max_g is slightly violated (12.002-12.016 against a 12 limit) while their mass margins are positive, so gamma about -3.565 is the g limit.
- C-6ffb6b7edb43 (3.384 m, margin 0.00074), C-1a745bbcb46d (3.385 m, margin 0.00014) and C-053e6577c074 (3.38 m, margin 0.0031): mass margin goes to zero near D of 3.3852.
- C-d883f15f56c5 (b 1.05, D 3.37, gamma -3.58): flux 284k against about 277.5k for b 1.2, with a worse bondline temperature and a lower mass margin. Higher bluntness therefore helps every metric.
- C-11ae4eb65bbb, C-660a8eef4199 and C-460ff98d4dde (b 1.24-1.25 at cone 70; b 1.2 at cone 69): 'cd_fore' extrapolation failure, so the hull boundary is at or near the (1.2, 70) vertex.

**mechanism:** Peak flux scales roughly as sqrt(rho_peak/Rn). It falls with larger D (larger Rn and lower ballistic coefficient) and with higher bluntness. Bondline temperature follows the integrated heat load, which a steeper entry lowers. Peak g is set mainly by gamma (prior knowledge, consistent with the table). The corner is already at the surrogate's edge, so the front can only be refined. I do this by filling gamma gaps at D 3.385 and by probing interior bluntness and cone combinations. Those probes use convex combinations of evaluated points, so they should stay inside the hull and avoid no-geometry failures. I expect them to be dominated but informative about cone and bluntness sensitivity.

**uncertainty:** I cannot see the round-2 and round-3 points, so the effect of cone angle on flux, mass and g is unknown. The exact hull edge near (b 1.2, cone 70) is unknown, so proposal 13 could fail. The D 3.385 mass margin is only about 1e-4, so small sensitivities could flip feasibility. My flux and temperature predictions are interpolations along the gamma sweep, and I extrapolated them for the exploratory points.

## ai_adaptive seed_37 call_06  (19 proposals, 0 ask fidelity 1)

**observation:** The feasible front is one curve: D≈3.385 m, bluntness 1.2, cone 70 deg, with only flight-path angle varying. Flux rises from about 227k to 274k W/m2 as gamma steepens from -1.5 to -3.565 deg, and bondline temperature falls from 418 to 391 K. Three limits pin the corner. The mass-fraction margin reaches zero at D≈3.3852. The g limit is reached at gamma≈-3.57 deg. The aero surrogate refuses to extrapolate for bluntness ≥1.22 at cone 70 and for (1.2, 69). Hypervolume has saturated at 0.355, so this round fills the gaps along the gamma curve and probes the corner limits.

**evidence:**
- C-a29bfeb09454, C-c197169fbbea, C-5b7da58ad0af, C-064ad9f5e91d, C-c89ccbca6e15 and C-3f1d8b1bcb6a show a smooth flux-versus-temperature trade along gamma at D=3.385, with gaps of 0.2-0.3 deg between -2.05 and -3.1.
- C-f71f4a44911d (gamma -3.565, g 11.991) and C-6146d28a8413, C-2a109f1c4205, C-053e6577c074 (gamma -3.58, g 12.002-12.014, infeasible) place the g limit near gamma -3.569 to -3.570.
- The mass-fraction margin falls about 0.59 per m of D. At b=1.2 it is 0.01486 at D=3.36 (C-2a109f1c4205), 0.0031 at 3.38 (C-053e6577c074), 1.45e-4 at 3.385 and 8.6e-5 at 3.3851 (C-8b8656d1393f), so the cap is D≈3.38525.
- At D=3.36, C-0968b66c7c61 (b=1.0) has margin 0.0095 and C-2a109f1c4205 (b=1.2) has 0.01486. Higher bluntness therefore raises the D cap slightly, by roughly 0.045 m per unit bluntness.
- C-11ae4eb65bbb, C-f414065c6995, C-660a8eef4199 and C-35e288c12205 (b 1.22-1.25) and C-460ff98d4dde (b 1.2, cone 69) failed with cd_fore extrapolation errors. C-0a1dd43d842b (1.19, 69.95) and C-b80fd27a21c5 (1.15, 69.3) evaluated normally.

**mechanism:** Peak flux scales roughly as sqrt(rho_peak/Rn), so larger D and larger bluntness lower it (this is prior knowledge, consistent with the tables). A steeper gamma shortens the heat pulse and lowers bondline temperature until max_g binds, since g depends mainly on gamma. The front is therefore the one-dimensional gamma sweep at the largest D that mass fraction allows. Interpolating in the gaps adds a little hypervolume. Slightly raising bluntness or D at the corner would cut flux by 0.1-0.5%, but only if the surrogate hull allows it.

**uncertainty:** The 1.205 and 1.21 bluntness probes may hit the surrogate hull boundary and return no geometry; the hull edge between 1.2 and 1.22 is unknown. Predicted margins near the mass and g limits are within about 1e-4 of zero, so the corner points may land infeasible. Gap-fill predictions are linear interpolations between neighbouring evaluated points, and I have no data on regions far from this corner.

## ai_adaptive seed_37 call_07  (20 proposals, 1 ask fidelity 1)

**observation:** The feasible front is essentially a one-dimensional flight-path-angle sweep at the corner design D≈3.385 m, bluntness 1.2, cone 70°. Along it, flux rises from 227k to 274.5k W/m2 and bondline temperature falls from 417.9 K to 391.1 K as gamma goes from -1.5° to -3.57°. Diameter is capped by the mass-fraction limit: the margin is 1.4e-4 at D=3.385 and 2.7e-5 at D=3.3852, and it falls about 0.59 per metre, so the limit sits at D≈3.38524. Gamma is capped by max_g (about 12 g at gamma≈-3.570). Every bluntness or cone move away from (1.2, 70) either lowered the mass-fraction margin or produced a 'cd_fore' extrapolation failure. All 33 no-geometry failures I can see in the data are extrapolation failures at bluntness above 1.2 or cone below 70.

**evidence:**
- C-7fdf9581b717 (D 3.3852, gamma -3.569) is feasible with max_g margin 2.0e-4 and mass margin 2.7e-5, so it sits at both binding limits.
- C-6146d28a8413, C-2a109f1c4205, C-053e6577c074 and C-3583b7488cf2 all have max_g margin below 0 at gamma -3.58 to -3.6, so the g cap is about -3.570.
- C-67c092ae8706 and C-b80fd27a21c5 (bluntness 1.1 and 1.15, cone 69.5 and 69.3) have negative mass margin at D≈3.38, so lowering bluntness or cone hurts.
- C-4aa35af3d6a3, C-39bfab3c832b, C-460ff98d4dde, C-02bec3a7a6f4 and C-35e288c12205 fail the cd_fore hull check at bluntness above 1.2 or cone below 70, so the surrogate domain edge is at the corner.
- The front points at D 3.385 (C-948029610632 through C-7fdf9581b717) give a smooth monotone flux/temperature curve in gamma that I can interpolate.

**mechanism:** Flux and bondline temperature trade off through gamma alone. A shallower entry lowers peak dynamic pressure and flux but lengthens the heat pulse, which raises bondline temperature. Peak g depends mainly on gamma, roughly on sqrt(sin gamma). That relation is prior knowledge, but it fits the tabulated g values. D, bluntness and cone are already at their joint limits, and a small D increase to 3.3852 gives a slightly lower flux and temperature at every gamma. The remaining gain is to fill gaps in the gamma curve at D=3.3852, using linear interpolation of the neighbouring evaluated points. I expect each new point to add very little hypervolume. The hypervolume is dominated by the temperature axis, so only a genuinely new low-temperature region could add a lot, and the data show no route into one.

**uncertainty:** I do not see the full 34-point front or the other 92 feasible designs, so some of these gamma values may sit close to points I was not shown. The gain per point is about 1e-6 to 1e-5 in normalised hypervolume. The last gamma value, -3.570, is within about 4e-5 of the max_g limit and could come out infeasible. Interpolated flux and temperature are accurate to roughly ±1k W/m2 and ±0.3 K. The effect of the tiny D change from 3.385 to 3.3852 is extrapolated from only a few points.

## ai_adaptive seed_37 call_08  (21 proposals, 0 ask fidelity 1)

**observation:** The feasible front is a one-dimensional sweep in flight_path_angle at the corner D≈3.385, bluntness 1.2, cone 70. It runs from about (227k W/m², 417.9 K) at gamma -1.5 to about (274.6k, 391.1 K) at gamma -3.57. Three limits pin this corner. Heatshield mass fraction caps D at about 3.38524. Peak g depends almost only on gamma and reaches 12.0 at -3.57. Cone 70 is the variable maximum, and bluntness above about 1.2 at cone 70 fails the cd_fore surrogate's convex-hull check. The last four rounds moved normalised hypervolume by less than 0.003 in total, so it is saturated.

**evidence:**
- C-25994855d0b4: D=3.3852, gamma=-3.57 gives g margin 4e-5 and mass margin 2.7e-5, so gamma and D are both at their limits.
- C-948029610632 (gamma -1.5) and C-25994855d0b4 (gamma -3.57) are the two ends of a smooth convex front.
- Mass margin vs D at bluntness 1.2, cone 70: C-053e6577c074 (3.38) 0.0031, C-9311986cd363 (3.383) 0.0013, C-294c231fb7c2 (3.3852) 2.7e-5. This is about -0.59 per metre, so the margin reaches zero near D=3.38524. Margin is the same across gamma.
- Seven geometry failures (C-4aa35af3d6a3, C-39bfab3c832b, C-35e288c12205, C-660a8eef4199 and others) all have bluntness of 1.205 or more at cone 70. C-460ff98d4dde (bluntness 1.2, cone 69) also fails. Bluntness and cone are therefore capped at the hull corner (1.2, 70).
- C-d883f15f56c5 (D 3.37, bluntness 1.05) and C-3583b7488cf2 (D 3.3) are dominated by the sweep, so lowering D or bluntness does not help.
- Slopes along the front are convex: dT/dF is -0.68 K per 1k W/m² between gamma -1.5 and -2.5, and -0.47 between -2.5 and -3.57. Linear chords across gaps therefore underestimate the dominated area.

**mechanism:** Peak flux scales roughly as sqrt(rho_peak/Rn), and bondline temperature follows the heat load, which is roughly flux times pulse time. Both improve with larger D. The mass-fraction limit stops D near 3.3852. Steeper gamma shortens the pulse, so temperature falls and flux rises, until the g cap at gamma≈-3.57. The remaining hypervolume gain therefore comes from filling the gaps on the convex front and from a slightly larger D (3.38524) that lowers flux by about 5 W/m². This flux effect relies on prior scaling knowledge, consistent with the tables. Where the front is already sampled densely, gains are near 1e-5. I spend the round on gap-filling with interpolated predictions and no risky off-corner exploration.

**uncertainty:** Expected gains are tiny. Mass margin at D=3.38524 is about +3e-6 by linear extrapolation, so a small nonlinearity could make those points infeasible. Interpolated flux and temperature should be within about 0.3% and 0.3 K. I cannot exclude a better region outside the hull corner, but geometry failures make it unreachable with these variables.

## ai_adaptive seed_37 call_09  (19 proposals, 0 ask fidelity 1)

**observation:** The feasible front is essentially a one-dimensional sweep in flight_path_angle_deg at D~3.3852, bluntness 1.2, cone 70. It runs from gamma=-1.5 (227.2 kW/m2, 417.9 K) to the max_g cap at gamma~-3.5701 (274.6 kW/m2, 391.1 K). D is capped by the heatshield_mass_fraction margin (~3e-6 to 3e-5 at D=3.3852), and the geometry surrogate is at its convex-hull edge. Bluntness above 1.2 (1.205-1.25) and cone below 70 with D below 3.38 all failed geometry or were dominated. The remaining hypervolume comes only from filling gaps in the sweep, and the gaps are small. I do that here, plus two tiny D probes and one gamma probe right at the g cap.

**evidence:**
- C-42e1b7d95981 (gamma -1.5) and C-c2d1addc0c7e (-1.75) leave a 0.25 deg gap; C-760c0b324dc5 (-1.95) to C-8438a428eb66 (-2.2) leaves another 0.25 deg gap.
- Smaller gaps remain between -2.35 and -2.5 (C-8dd96d9f9b80, C-e7776fa4dd93), -2.6 and -2.75 (C-e80bd3e93def, C-f402f187ca09), -2.83 and -2.95, and -3.05 and -3.2 (C-b16616085f94, C-7dcb5a130823).
- C-746e99b64989 at gamma -3.5701 has max_g margin 2.5e-5, which leaves ~1.5e-4 deg of headroom (max_g slope ~1.7 g/deg).
- Mass-fraction margin vs D: 3.383 -> 1.3e-3, 3.385 -> 1.4e-4, 3.3852 -> 3e-6 to 2.7e-5. A linear estimate puts zero margin near D~3.38525.
- Geometry failures C-4aa35af3d6a3, C-39bfab3c832b and C-fb6ea8c7e775 (bluntness 1.205-1.21) show that bluntness above 1.2 is outside the surrogate hull, so I leave bluntness and cone at 1.2 and 70.

**mechanism:** Flux and bondline temperature trade off through gamma. A steeper entry raises peak flux (~20-24 kW/m2 per deg) and lowers bondline temperature (~10-16 K per deg) by shortening the heat pulse. g rises with steepness and caps at about -3.57 deg. The front is smooth and slowly curving, so interpolating linearly between neighbouring rows gives reliable predictions, and each new gap point adds a small sliver of dominated area. The relations between D, flux and mass fraction come from the tables plus prior knowledge that flux ~ 1/sqrt(nose radius).

**uncertainty:** Gains are tiny (order 1e-4 in normalised hypervolume). D probes near 3.38523 may break the mass-fraction limit, because the true parent D values are hidden by rounding. The gamma=-3.5702 probe may exceed max_g. Predicted values are linear interpolations, accurate to about 0.2% on flux and about 0.2 K on temperature. No higher-fidelity check is requested.

## ai_adaptive seed_37 call_10  (7 proposals, 0 ask fidelity 1)

**observation:** The feasible front is essentially a one-dimensional sweep in flight_path_angle at D=3.3852, bluntness=1.2, cone=70. The corner is boxed in by three limits. Mass fraction caps D at about 3.3852, with margin near 3e-6 to 1e-4. max_g caps gamma at about -3.57. The aero surrogate refuses to extrapolate, so bluntness above 1.2 or cone below 70 with these D values fail geometry. Only 7 evaluations remain, so I spend them all on gamma gaps between neighbouring front points, keeping the other three variables fixed. Larger bluntness and higher D are off the table because they lose the evaluation slot or violate mass fraction.

**evidence:**
- C-c2d1addc0c7e (gamma -1.75: 232230 W/m2, 413.81 K) and C-cc705aab04af (gamma -1.97: 236940, 410.43) leave a 0.22 deg gap. I found no listed rows between them.
- C-e7776fa4dd93 (gamma -2.5: 248970, 403.04) and C-f402f187ca09 (gamma -2.75: 254890, 399.92) leave a 0.25 deg gap. C-f402f187ca09 to C-c9e8e66242d4 (gamma -3.0: 260850, 397.01) leaves another 0.25 deg gap.
- C-941731176c95 (gamma -3.05: 262060, 396.45) and C-6848871b6f6a (gamma -3.25: 266870, 394.29) leave a gap near gamma -3.14. C-8438a428eb66 (gamma -2.2) and C-7fc4070b9d5d (gamma -2.4) bracket -2.29.
- Eight recent rows at D 3.285 to 3.3855 with bluntness 1.205 to 1.25 all failed with 'aero surface extrapolation', so bluntness above 1.2 is unusable at these D values. C-746e99b64989 (gamma -3.5701, g=12.0000) confirms the g cap. C-053e6577c074, at D=3.38 and gamma -3.58, violates max_g.

**mechanism:** Between neighbouring rows the front is smooth and slowly curving. A steeper entry shortens the heat pulse, so bondline temperature falls by roughly 12 to 16 K per deg. It also raises peak dynamic pressure, so flux rises by roughly 20 to 24 kW/m2 per deg. Linear interpolation between neighbours should therefore predict new points well. Each new point sits on the front and adds a small sliver of hypervolume. This is prior knowledge fitted to the tabulated rows, not a new model.

**uncertainty:** Expected hypervolume gains are tiny, on the order of 1e-5 to 1e-4 normalised. Front curvature could put some points slightly off the interpolation. Some chosen gammas may have been evaluated already in the 193 rows not shown, but I picked non-round values to reduce duplicate risk. Mass-fraction margin at D=3.3852 is tiny (3e-6 to 3e-5) and varies slightly between rows, but it has stayed positive across all D=3.3852 rows shown.

## ai_adaptive seed_41 call_01  (20 proposals, 0 ask fidelity 1)

**observation:** None of the 20 evaluated designs is feasible, so there is no front yet. 10 of 20 returned no geometry. Every one of those has a cone half-angle too small for its bluntness. Fitting the 10 failures and the valid rows gives a validity rule: with nose radius = bluntness*D and shoulder radius = 0.1*D, the fore cone has positive length only if cos(theta) < 0.4/(bluntness-0.1). That means bluntness <= 0.5 is always valid, bluntness 0.7 needs theta > 48 deg, 0.9 needs > 60 deg, 1.1 needs > 66.4 deg, and 1.2 needs > 68.7 deg. The rule reproduces the sign of the fore-cone length in all 10 failures and every valid row. The constraint limits back-computed from the margins are max_g <= 12.0 and bondline T <= 450 K. Peak g depends mostly on |gamma| (about 6.3*sqrt|gamma| for D > 2.5), so gamma must be shallower than about -3.5 deg. The mass-fraction limit is not stated. Its value scales roughly as D^2 times a coefficient that falls with cone angle (about 0.089 at theta >= 62 deg, about 0.11 at theta <= 40 deg). That puts the D limit near 3.0-3.3 m. In these data, bondline T falls as D, nose radius and steepness rise. Peak flux falls with larger nose radius and larger D. Because T spans only 300-450 K against a 2.5e6 flux reference, reducing T is worth far more hypervolume, so I favour large D, large bluntness and gamma near -3.3 to -3.5, with a few shallower points to spread the front.

**evidence:**
- Geometry failures C-0e7ec9742f84 (b=.94, th=55.1), C-2e989122c857 (b=.97, th=59.8), C-7fd3f4505944 (b=.75, th=36.4) and C-de1dd6ca3952 (b=.84, th=40.6) all violate cos(th) < 0.4/(b-0.1). Valid rows C-36f9165b9496 (b=.87, th=65) and C-26bc5a06b4e4 (b=.70, th=51.6) satisfy it.
- max_g margins imply a 12.0 limit: C-ee99f55de428 has 10.189 with margin 0.1509. Bondline margin gives 450 K: 455.54 with margin -0.01232. g vs gamma: C-f97dae207371 (-1.85 deg) 9.42, C-ee99f55de428 (-2.64) 10.19, C-63aaa0985529 (-4.10) 12.49, C-36f9165b9496 (-4.86) 13.8.
- Mass fraction is roughly proportional to D^2. C-63aaa0985529 (D=2.99) is at 0.97 of the limit, C-ab9827dc6929 (D=3.21) at 1.004, C-baa2f9e65f32 (D=4.01) at 1.47, C-50a0a474d0f6 (D=1.23) at 0.15. High-theta rows (C-36f9165b9496, C-12010dd082dd, C-c72c38c9187a) sit near 0.089 of the limit per m^2, against about 0.11 for C-f97dae207371 and C-63aaa0985529 at theta <= 38 deg.
- Peak flux fits q ~ 7e6*sqrt(sin(gamma)/(D^2*Rn)) within about 10%, where Rn = b*D. Bondline T-300 fits about 0.307*sqrt(q/|gamma_deg|). For example C-ab9827dc6929 (q=479k, gamma -4.26) gives 335*0.307 = 103 K against 103.1 K observed, and C-63aaa0985529 gives 108.8 K against 109.6 K.
- C-63aaa0985529 (D=2.985, gamma=-4.1) has T=409.6 K and q=515k, and misses only on max_g (-0.04). C-ab9827dc6929 misses on max_g and mass fraction. Together they show the feasible region needs D of about 3.0 or less and |gamma| of about 3.5 or less.

**mechanism:** Peak deceleration in a ballistic entry is set mainly by entry angle. That makes max_g a ceiling on |gamma|, and the ceiling is where bondline temperature is lowest (T scales roughly as gamma^-0.25). Heat-shield mass fraction scales with the shield area, about D^2. It is lower for wide cones because they have less lateral area, which caps D near 3.0-3.3 m. Within those two limits, a large nose radius (Rn = b*D) lowers stagnation heat flux and heat load together. So the best trade-off has D near its mass limit, high bluntness with a cone angle above the validity boundary, and gamma just inside the g limit. Shallower gamma trades a little T for lower peak flux, which extends the front.

**uncertainty:** The g estimate for gamma near -3.5 (about 11.8 against a limit of 12) has only about 3% margin. I have no data on how theta and D affect g. The dependence of mass fraction on theta is inferred from correlation, not isolated. The validity rule is fitted; the length discrepancy (about 2%) suggests the shoulder radius or nose definition is slightly off, so I keep at least 1.3 deg of margin on theta. Flux and T models are rough fits (10-15% error) and small-D rows deviate. I do not know whether very high bluntness or theta near 70 deg adds flux penalties (e.g. shoulder heating) that this reduced-order model may include. Prior knowledge (Allen-Eggers scaling) supports the g and T trends, but the numeric fits come from the 10 valid rows.

## ai_adaptive seed_41 call_02  (20 proposals, 1 ask fidelity 1)

**observation:** The feasible front is a tight cluster at D≈3.0-3.3 m, bluntness 1.0-1.2, cone 68-70°, gamma -2 to -3.5°, with flux 283-300 kW/m² and bondline T 396-419 K. Hypervolume is about 0.32, and it is limited mainly by T: the normalised T axis (300-450 K) has far more room than the flux axis (reference 2.5 MW/m²). From the data I fitted rough local trends: T falls about 17 K per metre of D, about 0.8 K per 0.1 of bluntness, and about 11.7 K per degree of steepening gamma. Flux falls roughly as D^-1.45 and drops about 8%/deg with shallower gamma. max_g depends almost only on gamma (about 11.83 at gamma -3.5, D 3.25), so the limit of 12 caps gamma near -3.58. Heatshield mass fraction scales as D², with 1-margin ≈ 0.79*(D/3)², so D is capped near 3.37 m. Cone angle affects T, flux and g very little but is best at 70°. All 8 geometry failures have cone angle too small for the bluntness, which suggests a bluntness limit that shrinks as the cone gets shallower. This is an inference, not verified.

**evidence:**
- C-19d65f7d82f4 (D3.25, bl1.0, c69, g-3.5): T 395.58 and flux 300k with mass margin 0.072. C-bd65eb0949c1 (D3.3, g-3.3): margin 0.042. Mass margin therefore hits zero near D≈3.37.
- C-29603553ab30 (g-2.0): flux 283k, T 418.8. C-aa9546beae98 (g-2.4): T 414.5. C-ec050d7f0c55 (g-3.5): T 401.4 at D3.0. So T drops about 11-12 K per degree of steepening, at the cost of higher flux and g.
- max_g at g-3.5 is 11.61 (D2.7), 11.74 (D3.0) and 11.83 (D3.25), while cone 62/66/70 at D3.0 give identical g (C-7e855dcecd98, C-ec050d7f0c55, C-5eac89a9568b). g is set by gamma, with a weak D effect.
- Higher bluntness lowers both objectives slightly: C-268997241f64 (bl1.2, D3.1, g-3.4) has flux 307k and T 398.1, versus C-31cee390321b (bl1.1, c69.5) at 312.6k and 398.8.
- Infeasible steep-entry points (C-36f9165b9496, C-ab9827dc6929) gain little T (T≈398-403) but break max_g. Small-D points have high flux. The high-D, high-bluntness corner is therefore the best region.
- All 8 geometry failures have a small cone angle for their bluntness, e.g. C-2e989122c857 (bl0.97, c59.8) and C-7fd3f4505944 (bl0.75, c36). Every point with c≥62 and bl≤1.2 was valid, so I keep c=70 with bl≤1.25.

**mechanism:** Bondline T is driven by the heat pulse. A larger D lowers the ballistic coefficient, so peak heating occurs higher in the atmosphere and is lower. A steeper gamma shortens the pulse but raises g. The g limit of 12 fixes gamma at about -3.55, and the mass-fraction limit fixes D at about 3.35-3.37. A larger nose radius (bluntness) and a high cone angle reduce stagnation flux without changing g. The optimum T is therefore at the corner D≈3.35, bl 1.2, c70, gamma≈-3.5, near about 392 K and 279 kW/m². Since flux is cheap in hypervolume terms, I also spread points along the front with shallower gamma at D≈3.35 (lower flux, higher T) to cover the trade-off.

**uncertainty:** All numbers are extrapolations from local trends. D≥3.36 could violate mass fraction if my scaling is off, and gamma≤-3.55 could violate g at large D. Bluntness 1.25 at c70 is beyond the tested range and could be an invalid geometry. Shallow-gamma flux and T predictions rely on interpolation between D3.0 data and the fitted D scaling.

## ai_adaptive seed_41 call_03  (20 proposals, 1 ask fidelity 1)

**observation:** All 10 feasible non-dominated points sit on one curve: D about 3.35 m, bluntness 1.2, cone 70 deg (the upper bound), with only flight-path angle varied. Along it, gamma trades heat flux (231k to 278k W/m2) against bondline T (418.7 K to 391.9 K). The binding limits are max_g (about 12, which sets gamma near -3.55) and heatshield_mass_fraction (which sets D near 3.38 at cone 70). Flux is already about 0.1 of the 2.5M reference, so hypervolume gains come almost entirely from lowering T, and only marginally from lowering flux. The local optimum is close, so I mostly refine along its active constraints.

**evidence:**
- C-04a14692e856 (gamma -1.5) to C-b460a0993d3f (gamma -3.55): T falls 418.67 to 391.89 K, flux rises 230.7k to 278.3k, and max_g margin falls 0.232 to 0.004.
- Mass-fraction margin at cone 70, bluntness 1.2: 0.0612 at D=3.28 (C-e56e0f295417), 0.0497 at 3.30 (C-cbb67c388863), 0.0207 at 3.35 (C-b460a0993d3f), 0.0090 at 3.37 (C-ddce48f9a845). This is roughly linear at -0.59 per m, so it reaches zero near D=3.385.
- Larger D lowers both objectives: C-e56e0f295417 (D 3.28, gamma -3.5) has flux 285.6k and T 393.64, versus C-c4095cf95503 (D 3.35) with 277.0k and 392.38. That is about -123k W/m2 per m and -18 K per m.
- Lower bluntness is worse: at D 3.35, gamma -3.5, bluntness 1.0 (C-11dcf14fd72e) gives 287.3k / 393.73 K, versus 277.0k / 392.38 K at 1.2. It also costs about 0.005 of mass margin.
- Cone below 70 does not help: C-f901119b3d71 (cone 68, bluntness 1.1) and C-f96d071192f2 (cone 69, bluntness 1.1) are no better than the cone-70 points. The far-off-front points with low cone and low bluntness (C-63aaa0985529, C-50a0a474d0f6) have flux above 500k and higher T.
- C-05edbf22eaa2 (bluntness 1.25, cone 70) failed with cd_fore extrapolation, so the surrogate training range ends near bluntness 1.2 at this cone. There are 11 geometry failures, all with cone too small for the bluntness and diameter, so I keep cone at 60 or above.

**mechanism:** Peak g in a ballistic entry is set mainly by gamma, so the g limit of 12 caps |gamma| near 3.56. Bondline T falls with steeper gamma (shorter heat pulse) and with larger D (lower ballistic coefficient, so peak heating occurs higher in the atmosphere). Mass fraction grows roughly with D^2 and falls slightly with higher cone angle and bluntness, so D is capped near 3.38 at cone 70. High bluntness and cone 70 give high drag, low flux and low T. Because max_g margin is nearly independent of D and cone, the best design pushes D to the mass limit and gamma to the g limit, and the rest of the front is a gamma sweep at that D. All quantitative predictions come from linear fits to the tabulated rows (the D slopes above and the gamma slopes along the D=3.35 line), not from an independent model.

**uncertainty:** The D=3.38 to 3.384 points are only 0.001 to 0.003 in mass margin from infeasibility, and gamma -3.56 is 0.002 from the g limit. The linear margin fit could be slightly off, so a few of these may come back infeasible. The bluntness 1.21 probe may hit the surrogate hull and return no metrics. The cone-60 probe is exploratory and likely dominated, and its g and T effects are uncertain. Predicted flux and T come from local linear fits (about 1 K and 3k W/m2 accuracy).

## ai_adaptive seed_41 call_04  (20 proposals, 1 ask fidelity 1)

**observation:** The feasible front is one ridge: D≈3.38 m, bluntness 1.2, cone 70° (all at the upper limit), with only flight-path angle varying from -1.5 to -3.56. Three constraints bind at once. Peak g caps |gamma| near 3.57, the mass-fraction margin at D=3.38 is only 0.003, and bluntness/cone cannot go beyond (1.2, 70) without geometry or hull failures. Round-3 hypervolume gain was only 0.0043, so the remaining upside is (a) squeezing D and gamma to their exact limits and (b) checking whether slightly lower bluntness or cone at the corner changes T.

**evidence:**
- C-6ffb6b7edb43 (D 3.384) has mass margin 0.000736 and C-d20e6439cf38 (D 3.38) has 0.003097. That is about 0.59 per m, so the zero crossing is near D≈3.3852; D=3.385 should still be feasible.
- C-e6bfb3db2b24 (-3.56, g 11.981) and C-480359711777 (D 3.36, -3.57, g 11.989) give dg/d|gamma|≈1.75 per deg and dg/dD≈0.5 per m. That puts the g=12 limit near gamma≈-3.569 at D=3.385.
- T falls about 9.7 K/deg with steeper gamma (C-41b2ddb7397c to C-e6bfb3db2b24) and about 18 K/m with larger D (C-465478728e6f vs C-e6bfb3db2b24). hf falls about 119 kW/m² per m of D.
- Geometry failures: C-05edbf22eaa2 (b 1.25), C-3d41ce848a30 (b 1.21) and C-7db223121090 (cone 69) fail the aero-surrogate hull. C-e0197c1bd7dc (cone 68) has an overlapping nose sphere and shoulder torus. So (1.2, 70) sits at a vertex of the valid region.
- Mass fraction scales about D² with a shape factor near 1 at (1.2, 70). It is roughly 1.02 at C-36f9165b9496 (b 0.87, cone 65) and 1.11 at C-ab9827dc6929 (b 0.4, cone 53), so the corner is the best place for large D.

**mechanism:** Bondline T is set by heat-pulse severity: it falls with lower ballistic coefficient (larger D, higher-Cd blunt 70° cone) and with steeper entry. g and mass fraction cap gamma and D, and the corner (1.2, 70) maximises Cd and minimises shield mass. The gains left are therefore small: D→3.385 and gamma→-3.567 lower T by about 0.15 K and hf by about 0.4k. Points at the same D along the gamma ridge then replace the current front points. Stagnation heat flux should go roughly as Rn^-0.5, which I am taking from prior knowledge rather than from the data. Lowering bluntness at cone 70 should therefore raise hf, but the effect on T is unmeasured. I probe it at fixed gamma=-3.5 so the effect can be isolated.

**uncertainty:** g at gamma≈-3.567 is within about 0.0005 of the limit, so tiny model errors could flip feasibility. The mass-fraction zero crossing is extrapolated linearly by 0.001 m. The hull shape below (1.2, 70) is unknown, so some bluntness/cone probes may return no geometry. The b^-0.5 heating scaling and the shape-factor model for mass fraction are assumptions, not fitted.

## ai_adaptive seed_41 call_05  (20 proposals, 0 ask fidelity 1)

**observation:** After 4 rounds the feasible front (16 points, normalised hypervolume 0.355) is a one-dimensional ridge at D~3.385 m, bluntness 1.2 and cone 70 deg, parameterised only by flight-path angle from -1.5 to -3.568. Flux and bondline T trade smoothly along it: 227k W/m2 with 417.9 K at -1.5 deg, down to 274.5k W/m2 with 391.1 K at -3.567 deg. Three limits pin this corner. max_g (12) caps |gamma| near 3.57. Heatshield mass fraction caps D near 3.385, with margin 1.4e-4. Bluntness and cone angle sit at the edge of the aero surrogate hull (five geometry or hull failures in the 3.3-3.4 m, 1.2, 68-70 deg neighbourhood). The remaining hypervolume gain is therefore in filling gaps along the ridge and shaving the g limit, not in moving to a new region.

**evidence:**
- C-948029610632, C-17412c93bd7a, C-df9f7a25badc, C-8f79870bde82 and C-1c324800060f are spaced 0.3-0.5 deg apart in gamma, so the ridge has gaps at gamma between -1.5 and -2.0, -2.0 and -2.5, and -2.5 and -3.0.
- C-78a9a956afab (gamma -3.567, g 11.994, margin 5e-4) and C-1a745bbcb46d (-3.55, g 11.966) give dg/dgamma of about 1.65 g/deg. That puts g=12 at gamma of about -3.5706.
- Mass-fraction margin is 0.0207 at D 3.35 (C-ab6fb1629c20) and 1.4e-4 at D 3.385 (C-948029610632), a slope of about 0.59 per metre. Margin does not depend on gamma, so D max is about 3.3852.
- C-c9ba8204e0d2, C-a479cd1dc7b5 and C-bd26f4bc6a38 (bluntness 0.9-1.12, D 3.3-3.35) are dominated by the ridge points at gamma -3.5 (flux 280-300k against 273k), so lower bluntness only raises flux.
- C-05edbf22eaa2 (bluntness 1.25), C-3d41ce848a30 (1.21, D 3.38) and C-7db223121090 (cone 69, bluntness 1.2) all fail the cd_fore hull check, and C-e0197c1bd7dc (cone 68) and C-5608a135cebc (cone 60) fail geometry. Bluntness above 1.2 and cone below 70 at bluntness 1.2 are not reachable.
- Off-ridge designs such as C-ee99f55de428, C-c72c38c9187a and C-50a0a474d0f6 are infeasible or have flux of 0.5-1.8M W/m2, which is far dominated.

**mechanism:** Peak g is set almost entirely by gamma, so g<=12 fixes the steep end of the ridge. Shield mass fraction grows about as D^2 and shrinks slightly with bluntness and cone angle, so D is capped near 3.385 at (1.2, 70). A large D and a blunt, wide cone lower the ballistic coefficient, so peak heating occurs higher in the atmosphere and both flux and T fall. The remaining freedom is gamma. Shallower gamma gives lower flux, from lower dynamic pressure at peak heating, but a longer heat pulse and higher bondline T. The front is therefore a smooth convex curve in gamma at fixed geometry. The plan is to densify it (about 10 fill-ins at 0.1-0.2 deg spacing), push the steep end to the g limit (-3.5695 to -3.570), and spend one probe on the hull edge at bluntness 1.203.

**uncertainty:** Predicted flux and T are linear interpolations along the existing ridge, so they should be good to about 0.5k W/m2 and 0.3 K. The g-limit points (-3.5695 and -3.570) could tip infeasible if g is slightly nonlinear beyond -3.567. The bluntness 1.203 probe may fail the hull check, which would cost one slot. I am relying on prior knowledge of ballistic-entry scaling only for the mechanism; the numbers come from the table.

## ai_adaptive seed_41 call_06  (20 proposals, 0 ask fidelity 1)

**observation:** The feasible front is essentially one ridge at D≈3.385, bluntness 1.2, cone 70 (the upper bound), with only flight_path_angle varying. Along it, flux rises from 227k W/m² at gamma -1.5 to 274.6k at -3.57, and bondline T falls from 417.9 K to 391.1 K. The ridge is capped at the steep end by max_g (margin 4.7e-5 at -3.57) and by heatshield mass fraction (margin 1.4e-4 at D=3.385). Every off-ridge design I can see (the nearly_feasible list) has flux of 440k or more and is dominated. Most of the 8 recent failures are extrapolation refusals at bluntness>1.2 or cone<70, or invalid geometry at lower cone with high bluntness. Hypervolume gains since round 3 have been about 1e-3 or less per round.

**evidence:**
- C-948029610632 (gamma -1.5) and C-81e40e27ff03 (gamma -3.57) bound the ridge, with T from 417.87 to 391.09 K and flux from 227220 to 274570.
- C-81e40e27ff03 has max_g 11.999 (margin 4.7e-5), so gamma steeper than about -3.5703 breaks g<=12.
- C-0265d5374015 (D=3.3851) has mass-fraction margin 8.6e-5 against 1.45e-4 at D=3.385, so D is capped near 3.3853.
- C-3136d3bd2588, C-05edbf22eaa2, C-3d41ce848a30 and C-7db223121090 fail on cd_fore extrapolation at bluntness>1.2 or cone<70, so the corner sits on the surrogate's convex-hull edge.
- C-e0197c1bd7dc and C-5608a135cebc are invalid geometries at cone 68 and cone 60 with bluntness 1.2, so high bluntness needs a high cone angle.
- Off-ridge points such as C-ab9827dc6929, C-f97dae207371 and C-63aaa0985529 have flux of 438k-515k, so those regions are far from competitive.

**mechanism:** Peak g is set almost entirely by gamma, and mass fraction by roughly D² with a weak dependence on cone and bluntness. Together they pin the low-T end at gamma≈-3.57 and D≈3.385. A large blunt 70° cone gives the highest drag coefficient, hence the lowest ballistic coefficient, so peak heating occurs high in the atmosphere. Shallower gamma lowers flux but lengthens the heat pulse, which raises T, so this trade-off is a smooth monotone curve. Remaining hypervolume gain comes from filling gaps along the curve and from small sensitivity probes at the hull edge (bluntness slightly below 1.2, D slightly changed). Most of this reasoning is inferred from the ridge data and the earlier rounds' notes; the effect of bluntness on flux and T at cone 70 is not directly observed in the rows shown.

**uncertainty:** The ridge interpolations are reliable to about ±0.3 K and ±500 W/m². The bluntness, cone and D probes are extrapolations from physical reasoning, and the cone 69.8 probe may hit an extrapolation refusal or invalid geometry. Some of my gamma values may duplicate evaluations that are not in the visible tables. Expected hypervolume gain is small, since the ridge is already dense.

## ai_adaptive seed_41 call_07  (22 proposals, 0 ask fidelity 1)

**observation:** The front is a one-dimensional ridge at the corner D=3.385, bluntness=1.2, cone=70, parameterised by gamma from -1.5 to -3.5702. All three limits pin that corner: g<=12 caps |gamma| near 3.570, mass fraction (proportional to D^2) caps D near 3.3852, and the bluntness/cone hull edge blocks any move to more bluntness or a smaller cone (1.203, 1.21, 1.25 and cone 69 all fail on hull or geometry). Lowering bluntness or cone, or shrinking D, raises flux and T, so those moves are dominated. Normalised hypervolume is 0.3555 and has gained only about 1e-4 to 4e-5 per round since round 4. The remaining gain is in the sparse stretches of the gamma ridge, mainly -2.2 to -2.6 and -2.9 to -3.28, plus tiny D and gamma tweaks at the g and mass-fraction limits.

**evidence:**
- C-948029610632 to C-bc377838462a: flux rises 227k to 275k and T falls 417.9 K to 391.1 K monotonically with steeper gamma, at fixed D=3.385, bluntness 1.2, cone 70.
- Ridge gaps: C-2d7e6dba2267 (-2.2: 242.1k, 407.1 K) to C-249a4f21af03 (-2.6: 251.4k, 401.8 K), and C-3f1d8b1bcb6a (-2.9) to C-f9075e31d70a (-3.28). The ridge is convex, so points inside these gaps should enter the front.
- Mass fraction margin is 0.0001449 at D=3.385, 8.6e-5 at 3.3851 and 2.7e-5 at 3.3852 (C-0265d5374015, C-8d69d1842e32). It is 0.0497 at D=3.3 (C-6041504dc2c9), which matches the D^2 scaling. The zero crossing is near D=3.38525.
- g margin is 5.2e-4 at gamma -3.567 (C-78a9a956afab), 4.7e-5 at -3.57 (C-81e40e27ff03) and 2.5e-5 at -3.5702 (C-bc377838462a). The limit is near -3.5704.
- C-956957ec60d4, C-7112b6b29bcf and C-14444dd6b10a (bluntness 1.19, 1.15, 1.1) show lower bluntness raises flux and breaks mass fraction. C-3136d3bd2588, C-3d41ce848a30, C-05edbf22eaa2 and C-7db223121090 show the hull blocks bluntness above 1.2 and cone below 70 at these D.

**mechanism:** Peak g is set almost entirely by gamma, which fixes the steep end of the ridge. Mass fraction scales with D^2, which fixes D. A larger D and a blunt 70 degree cone give the lowest ballistic coefficient, so peak heating occurs higher and both flux and T fall. Along gamma, shallower entry lowers flux but lengthens the heat pulse and raises T. That gives a smooth convex trade-off curve. The corner design is already at every bound, so the useful moves are to densify the ridge and to test the D and gamma limits, gaining a little hypervolume without risking rejected slots. The gamma^-0.25 and D^2 scalings are partly from prior knowledge; the numbers here are interpolated from the rows cited.

**uncertainty:** Predictions are linear or convex interpolations between neighbouring ridge points and should be accurate to about 0.3 K and 1k W/m2. The main risk is the D=3.3852 and gamma -3.5703 points sitting on the mass-fraction and g limits. I estimate margins of about +1e-5 for g and +2.7e-5 for mass fraction, and a small error would make them infeasible. There is no evidence of any better region away from the corner, so I spent no slots on exploration beyond it.

## ai_adaptive seed_41 call_08  (28 proposals, 1 ask fidelity 1)

**observation:** The feasible front is a one-dimensional ridge at the corner D~3.385, bluntness 1.2, cone 70, running in flight_path_angle from -1.5 (flux 227k W/m2, T 417.9 K) to -3.5703 (flux 274.6k, T 391.1 K). Three limits pin that corner. max_g<=12 caps steepness at gamma ~ -3.5703. Heatshield mass fraction caps D at ~3.3852, and its margin is independent of gamma. The aero surrogate and geometry limit bluntness to <=1.2 and cone to >=~69.8 at this D. Every other region I have seen is dominated. HV has moved by less than 1e-4 per round since round 3. The only remaining gains are a slightly larger D (a tiny dominance improvement at every gamma) and denser sampling along the ridge.

**evidence:**
- C-948029610632 to C-105ca6c5af01: at D=3.385, b=1.2, cone=70, flux rises 227k to 275k while T falls 417.9 to 391.1 K as gamma goes from -1.5 to -3.57. The curve is smooth and convex (dT/dF about -0.73 near -1.5, about -0.41 near -3.5).
- Mass-fraction margin is 0.0001449 at D=3.385, 0.003097 at D=3.38 and 2.677e-05 at D=3.3852. That is linear with slope ~0.59 per m, and it is identical at every gamma. It extrapolates to zero at D~3.38525, so D=3.38523 should be feasible.
- C-956957ec60d4, C-7112b6b29bcf and C-14444dd6b10a: lowering bluntness below 1.2 violates mass fraction and raises flux. C-05edbf22eaa2, C-3d41ce848a30 and C-3136d3bd2588 (b>1.2) and C-e0197c1bd7dc and C-7db223121090 (cone<70 at b=1.2) fail on geometry or surrogate extrapolation. The corner cannot be moved.
- C-6041504dc2c9: D=3.3 gives flux 283k and T 393.3 K at gamma -3.5, worse than D=3.3852 (272.9k, 391.76 K). Larger D helps and smaller D does not.
- C-105ca6c5af01 has g margin 1.486e-05 at gamma -3.5703 and D=3.3852. With dg/dgamma ~1.65 per deg, gamma -3.5704 is right at the g=12 limit.

**mechanism:** Peak g is set almost entirely by gamma, so g<=12 fixes the steep end at ~-3.5703. Shield mass fraction scales with D^2, which fixes D at ~3.3852 for the blunt 70-degree cone. Larger D and higher Cd give a lower ballistic coefficient, so peak heating occurs higher and both flux and T fall slightly. Shallower gamma lowers flux but lengthens the pulse and raises T, which produces the convex ridge. With D at its limit, the front can only be improved by using D=3.38523 (about -25 W/m2 and -0.004 K at each gamma) and by adding points along gamma. All proposals are corner designs (b=1.2, cone=70) with D=3.38523, varying only gamma. One proposal probes gamma=-3.5704 at D=3.3852.

**uncertainty:** Predictions come from interpolating the D=3.385 ridge and applying a small D correction estimated from two nearby D values, so flux and T should be accurate to about 0.1%. The main risk is the two limit-hugging points: D=3.38523 (mass-fraction margin ~1e-5) and gamma=-3.5704 (g margin ~0). Either could come out infeasible. Expected HV gain is very small because the front is nearly saturated.

## ai_adaptive seed_41 call_09  (27 proposals, 0 ask fidelity 1)

**observation:** The front is a one-parameter ridge at D~3.3852, bluntness 1.2, cone 70. The gamma sweep runs from -1.5 (flux 227k, T 417.9) to -3.5703 (flux 274.6k, T 391.1). max_g pins the steep end at gamma about -3.5703, and mass fraction pins D at about 3.3852. Hypervolume has plateaued at 0.3556, and 9 of the last 20 rows show gains of under 1e-4. Bluntness above 1.2 or cone below 70 has repeatedly returned extrapolation or geometry failures. Only the gamma ridge remains safe to sample.

**evidence:**
- C-b8e5f12114a1 to C-c461ce8af13c: flux and T vary smoothly and monotonically with gamma at fixed geometry (flux 227.2k to 274.6k, T 417.87 to 391.08).
- C-c461ce8af13c has max_g margin 1.9e-5 and C-8187cef72ab8 (gamma -3.5704) has -1.4e-5, so the g limit sits at gamma about -3.57031.
- D=3.385 gives mass margin 1.449e-4 (C-163399613c78) and D=3.3852 gives 9.05e-6, so the mass limit is at D about 3.38521 if the slope of about -0.68 per m is linear.
- C-05edbf22eaa2, C-7db223121090, C-3d41ce848a30 and C-3136d3bd2588 failed cd_fore extrapolation with bluntness above 1.2 or cone below 70. C-e0197c1bd7dc and C-5608a135cebc failed on geometry. The buildable, in-hull region is only the corner (1.2, 70).
- C-956957ec60d4, C-7112b6b29bcf and C-14444dd6b10a show lower bluntness breaks the mass-fraction limit and raises flux, so they are worse.

**mechanism:** Peak g is set almost entirely by gamma, which fixes the steep end of the ridge. Mass fraction scales with D^2 and rises with lower bluntness or cone, which fixes D at the corner. A larger D and higher Cd lower the ballistic coefficient, so flux and T both fall. Shallower gamma lowers flux but lengthens the heat pulse and raises T. That gives a convex flux-T curve in gamma. I expect no unexplored region to dominate, so I fill the gaps between known gamma points to sharpen the front. I also test D=3.38521, the last feasible step in D, at several gammas.

**uncertainty:** I am interpolating linearly between neighbouring ridge points, so predictions are good to about 0.05 K and 300 W/m2. The D=3.38521 points could break the mass limit if the mass-margin slope is nonlinear. Near gamma -3.5702 the g margin is about 1e-5 and a small D change could flip it. Some of my gamma values may duplicate unseen evaluated rows, since only part of the 60-point front is shown. I am relying on the shown data plus generic ballistic-entry reasoning. Hypervolume gains will be tiny.

## ai_adaptive seed_41 call_10  (1 proposals, 0 ask fidelity 1)

**observation:** The feasible front is essentially a one-dimensional ridge at D=3.3852 m, bluntness 1.2, cone 70 deg, parameterised by flight-path angle. Steeper entry gives lower bondline T and higher flux. The steep end is capped by max_g<=12 at gamma of about -3.5703 (C-c461ce8af13c). D is capped by the heatshield mass-fraction margin, which is ~1e-5 at D=3.3852. Probes off the corner either violate the mass fraction (C-956957ec60d4, C-7112b6b29bcf, C-14444dd6b10a) or hit geometry or extrapolation failures (C-05edbf22eaa2, C-3136d3bd2588). With one evaluation left, the safest way to gain hypervolume is to fill a gap on the ridge. The largest visible gap in gamma is between -1.68 and -1.9317 (C-d67052cfd2f9 to C-33a892b93afd).

**evidence:**
- C-d67052cfd2f9: gamma -1.68 gives flux 230760 W/m2 and T 414.92 K.
- C-33a892b93afd: gamma -1.9317 gives flux 236070 W/m2 and T 411.00 K.
- C-e9d1bc94c0c6 to C-d67052cfd2f9 to C-33a892b93afd: flux and T are nearly linear in gamma, at roughly 20-21k W/m2 per deg and 16 K per deg, so interpolation is reliable.
- Every evaluated gamma from -1.5 to -3.5703 at (3.3852, 1.2, 70) is feasible, so a mid-range gamma should keep all margins positive; the mass-fraction margin appears independent of gamma.
- C-956957ec60d4, C-7112b6b29bcf, C-14444dd6b10a: reducing bluntness violates the mass fraction, so the corner is the right place to stay.
- C-c461ce8af13c: the max_g margin at gamma -3.5703 is only 1.9e-5, so the steep end is exhausted.

**mechanism:** Peak g is set almost entirely by gamma, so the g limit fixes the steep end. Mass fraction fixes D. Shallower gamma lowers peak flux because entry is at lower density for longer, but lengthens the heat pulse and raises the bondline T. That gives a monotone, nearly linear trade-off along gamma. A point at gamma of about -1.8 sits in the widest visible gap between neighbours and adds a small hypervolume increment. It uses only the existing, verified geometry, so there is no risk of geometry or extrapolation failure.

**uncertainty:** The hypervolume gain is small, about 1e-5 in normalised terms. I have not seen the full 81-point front, so an unseen point may already fill this gap. The flux and T values are linear interpolations from the data, not from a physical model.

## ai_agent seed_37 call_01  (20 proposals, 2 ask fidelity 1)

**observation:** Only 2 of 20 evaluated designs are feasible, and 11 of the 20 returned no geometry. All 11 geometry failures fit one rule I derived from the reported negative cone lengths: fore-cone length = (y2 - y1)/tan(theta), where y1 = Rn*cos(theta) with Rn = bluntness*D, y2 = D/2 - Rs*(1 - cos(theta)) with Rs = 0.1*D. It reproduces -81 mm (C-8fe9c875d634), -367 mm (C-892b8b20e709) and -5413 mm (C-c9569b91ff83). The rule reduces to (bluntness - 0.1)*cos(theta) <= 0.4, independent of D. I hold every proposal to <= 0.376 for margin. The other constraint limits are max_g <= 12 g, bondline <= 450 K, and a mass-fraction limit that scales roughly as D^2 (D up to about 3.3 m). Hypervolume is dominated by the bondline-temperature axis (a 150 K span versus 2.5 MW/m2 for flux). The current front is a single point, C-ca305253716b (345 kW/m2, 406.6 K). Rough log-fits to 9 metric rows suggest that a larger nose radius (bluntness*D) and larger D lower flux and bondline temperature. They also suggest that steeper entry lowers bondline temperature and raises g, with the g limit near gamma of -3.6 deg.

**evidence:**
- Geometry failures C-892b8b20e709, C-c170e00795a8, C-2fe8ade3b390 and C-8fe9c875d634 all violate (b-0.1)cos(theta) <= 0.4; valid rows C-ca305253716b (0.366), C-30ab3c9fdbef (0.361) and C-7e930f570744 (0.20) satisfy it.
- g rises with steepness: C-30ab3c9fdbef -2.32 deg gives 9.85 g, C-ca305253716b -3.16 deg gives 11.2 g, C-7e930f570744 -4.54 deg gives 13.57 g. Steeper rows C-1d847642b793 and C-0a0993b4b67b give 16.6 and 18.8 g. The 12 g limit is therefore near -3.6 deg for large D.
- Mass-fraction margin tracks D^2: C-ca305253716b (D 3.01) 0.185, C-0a0993b4b67b (D 3.74) -0.37, C-1d847642b793 (D 4.33) -0.77. Feasible D is at most about 3.3 m.
- Low bondline temperature comes from large D and steep gamma: C-1d847642b793 372 K and C-0a0993b4b67b 374 K, versus small-D rows C-6c8d751b6b54 510 K and C-7139ecfe995b 469 K.
- Shallow entry raises bondline temperature at similar flux: C-30ab3c9fdbef has 431.6 K at gamma -2.32 deg, versus 406.6 K for C-ca305253716b at -3.16 deg.
- Normalised hypervolume 0.2496 equals (1-345120/2.5e6)*(450-406.56)/150, so the score depends heavily on the bondline term.

**mechanism:** Peak stagnation heating falls with nose radius (about 1/sqrt(Rn)) and with lower ballistic coefficient, i.e. larger D. Bondline temperature follows the heat load, so it falls with a shorter, steeper pulse and with lower peak flux. Steeper entry raises g. The mass fraction limits D to about 3.3 m and g limits gamma to about -3.6 deg. The best corner is therefore D near 3.2-3.3 m, the largest nose radius the geometry rule allows (bluntness about 1.1-1.2 with cone angle 68-70 deg), and gamma near -3.4 to -3.55 deg. Shallower gamma gives lower flux but higher bondline temperature, which traces the trade-off front.

**uncertainty:** The geometry rule is fitted to 11 failures plus valid rows, and I have not seen valid rows with bluntness above 0.88 at cone angles near 70 deg. The flux and bondline scalings come from about 9 rows with noisy exponents. I am relying on ballistic-entry scaling from prior knowledge for the sign and size of some trends. The effects of cone angle on g and drag, and the exact mass-fraction limit near D 3.3 m, are poorly constrained. The g boundary near gamma of -3.6 deg is interpolated.

## ai_agent seed_37 call_02  (20 proposals, 1 ask fidelity 1)

**observation:** Every feasible point sits at large D (about 3.2-3.3 m), high bluntness (1.1-1.18), cone angle near 70 deg and gamma between -2.2 and -3.5 deg. The hypervolume is 0.331. In normalised terms, 1 K of bondline temperature is worth about 0.6% of hypervolume, while 10k W/m2 of flux is worth only about 0.15%. Lowering bondline temperature therefore matters most. Two constraints bound the corner. max_g caps gamma at about -3.6 deg (limit about 12 g, roughly 1.6 g per degree, almost independent of D, bluntness and cone). The heatshield mass fraction caps D. Its margin scales roughly with D^2, and my extrapolation puts the limit near D = 3.38-3.40 m. The unexplored gains are a larger D, bluntness up to 1.35, and a spread of gamma values along the front.

**evidence:**
- D sweep at gamma -3.4 and bluntness 1.1: C-897b67e590d7 (D 2.9) gives 344k W/m2 and 403.0 K, C-5e1c13074d20 (D 3.2) gives 298.7k and 396.9 K, and C-84c7c9af373d (D 3.3) gives 285.8k and 395.0 K. Larger D lowers both objectives.
- Mass-fraction margin versus D: 0.263 at 2.9 m (C-897b67e590d7), 0.103 at 3.2 (C-5e1c13074d20), 0.0748 at 3.25 (C-26ce9aa66580), 0.0455 at 3.3 (C-84c7c9af373d). The margin follows a D^2 scaling and would reach zero near 3.38 m. Bluntness 1.18 with cone 70 adds about +0.003 (C-15f0016ca61b, C-51e48573fc56).
- Gamma sweep at D 3.2, bluntness 1.1, cone 69: gamma -3.25, -3.4, -3.55 and -3.7 give g 11.40, 11.64, 11.89 and 12.14, and bondline temperature 398.5, 396.9, 395.3 and 393.8 K. C-114b79b08144 (gamma -3.7) violates max_g at 12.136 g.
- g depends almost only on gamma. C-7e930f570744 (gamma -4.54) gives 13.57 g and C-0a0993b4b67b (gamma -7.07) gives 18.8 g, while D and bluntness change g by only about 0.4 g per metre. Steeper entry cannot be bought back through geometry.
- Bluntness 1.0 (cone 66), 1.1 (cone 69) and 1.18 (cone 70) at D 3.2, gamma -3.4 give 305.1k, 298.7k and 294.4k W/m2 and 397.7, 396.9 and 396.3 K (C-b6ef7565262e, C-5e1c13074d20, C-15f0016ca61b). Higher bluntness helps both objectives, and the mass margin does not degrade.
- Shallow-gamma front points C-b86d67fded52 (gamma -2.2: 263.6k, 411.2 K) and C-a2a24d2b0ad2 (gamma -2.6: 277.6k, 406.3 K) show the flux versus temperature trade-off. A larger D and higher bluntness should shift this curve down and left.
- All 8 geometry failures have a small cone angle relative to bluntness. From the reported negative cone lengths I fit a rough overlap condition, cos(theta)*(about 1.86*b - 0.1) < 0.9. Cone 70 with b up to 1.35 gives about 0.82-0.85, so it should be buildable. Cone 69 with b 1.3 gives about 0.83-0.86, also inside the limit. C-15f0016ca61b (b 1.18, cone 70) and C-51e48573fc56 already built.

**mechanism:** Stagnation heating falls with nose radius and with lower ballistic coefficient (larger D and bluntness). Peak bondline temperature follows the heat load, which is lower for a shorter, steeper pulse. Peak g is set almost entirely by gamma, since g_max is roughly independent of ballistic coefficient. The best corner is therefore the largest D the mass fraction allows (about 3.36-3.38 m), the largest bluntness the geometry allows (1.35 at cone 70), and gamma near the g limit (about -3.5 to -3.55 deg). Sweeping gamma from -1.8 to -3.4 at that D and bluntness fills the flux versus temperature front with points below the current one.

**uncertainty:** The extrapolation to b 1.35 is outside the sampled range, and the effect of bluntness on mass fraction there is unknown. The mass-fraction edge near D 3.38 is uncertain by about ±0.01 in margin. The g margin at gamma -3.55 is only about 0.5-1%. The geometry-overlap fit uses only 8 failures and could be wrong near b 1.35. I extrapolated the flux D-exponent of about -1.35 from a few points. All predicted values come from local linear extrapolation of the data shown, not from a validated model.

## ai_agent seed_37 call_03  (19 proposals, 0 ask fidelity 1)

**observation:** All 20 round-2 proposals were wasted on the invalid corner (bluntness 1.25-1.35, cone 70, D around 3.36). The geometry check rejects any cone angle too small for the nose radius, and the fore cone length goes negative. At D=3.36 and cone 70, the overrun is -12.7 mm at b=1.30 and -33.7 mm at b=1.35, so the limit is near b=1.27. b=1.25 also failed a separate surrogate check (cd_fore outside its training hull). The only feasible designs sit at b=1.1-1.18, cone 68-70, D 3.2-3.3. Within that set, lower gamma gives lower heat flux and higher bondline temperature (about 264k W/m2 and 411 K at -2.2 deg, about 290k and 394 K at -3.5 deg). Peak g reaches about 11.83 at -3.5 deg and hits its 12 g limit near -3.6 deg. The mass-fraction margin shrinks as D grows (0.106 at D 3.2, 0.078 at 3.25, 0.046 at 3.3 with cone 68). This round stays inside the proven envelope and fills the front along gamma, D and mild bluntness changes.

**evidence:**
- C-b86d67fded52 (D 3.2, b 1.18, cone 70, gamma -2.2): 263.6k W/m2, 411.2 K, feasible. This is the low-flux end of the front.
- C-51e48573fc56 (D 3.25, b 1.18, cone 70, gamma -3.5): 290.4k W/m2, 394.3 K, g margin 0.014. This is the low-temperature end.
- C-114b79b08144 (gamma -3.7, b 1.1, D 3.2): g 12.136, infeasible. Together with C-84c7c9af373d (g 11.68 at -3.4) this puts the g limit near gamma -3.6 deg.
- C-84c7c9af373d (D 3.3, cone 68): mass margin 0.0455, so D above about 3.35 risks the mass-fraction constraint.
- C-2317645f3652, C-f986776067bd, C-733b361d9f0d and the b=1.35 rejections: bluntness at or above 1.25 with cone 69-70 is invalid or outside the hull, so keep b at or below about 1.22.

**mechanism:** Stagnation heating falls with nose radius, so higher bluntness and larger D help. Peak g is set mainly by gamma, and mass fraction limits D. Bondline temperature follows heat load, which is lower for a steeper, shorter pulse. Steep gamma near -3.55 to -3.6 lowers temperature while staying just under the g limit. Shallow gamma (-1.5 to -2.2) lowers peak flux and extends the front to the left. The hypervolume uses a 450 K reference, so a few kelvin of bondline temperature is worth much more than tens of thousands of W/m2. Effects of cone angle and of b between 1.18 and 1.22 are not well known from the data, so I probe them cautiously. These rely partly on prior physical knowledge, not only on the tables.

**uncertainty:** The g-versus-gamma slope is interpolated from designs with different D and b, so gamma of -3.58 to -3.6 may cross 12 g. The mass-fraction margin at D 3.34-3.36 is extrapolated. The b=1.20-1.22 points at cone 70 may fail the geometry or hull check. Effects of cone angle are essentially unobserved. Predicted fluxes and temperatures are linear interpolations and may be off by a few percent.

## ai_agent seed_37 call_04  (20 proposals, 1 ask fidelity 1)

**observation:** Both objectives are dominated by one corner of the design space. Every feasible front point has cone angle 70 (the upper bound), bluntness 1.15-1.2 and D 3.25-3.36 m. Temperature is what moves hypervolume: the flux reference is 2.5e6 W/m2, so flux differences of about 40k barely matter, while 1 K of bondline temperature is worth about 0.006 normalised HV. From the margins, the limits are max_g <= 12.0 and heatshield mass fraction, which behaves like margin ~ 0.0497 + 0.028*(b-1.2) - 0.5855*(D-3.3). This puts the D ceiling near 3.385 m and makes the mass margin almost independent of gamma and cone. Peak g is set mainly by gamma (about 1.8 g/deg near -3.55) with a small positive D dependence (about 0.53 g/m). Larger D lowers both flux and temperature (about -16 K/m in T, flux roughly D^-1.3), and steeper gamma lowers T at about 1 K per 0.1 deg. The best corner is therefore D about 3.375-3.383, b about 1.2, cone 70, gamma about -3.55 to -3.565. Geometry failures occur for b >= 1.3 and for lower cone angles at high b. Bluntness 1.22 fails the cd_fore hull at cone 70, so b must stay at or below about 1.2-1.21.

**evidence:**
- C-cbb67c388863 (D3.3,b1.2,g-3.55): T392.78, g11.933, mass margin 0.0497. C-6b7d0d55c053 (D3.34,b1.15): mass margin 0.02513. C-0e7e9141529e (D3.36,b1.15): 0.01342. These fit the linear-in-D mass-margin law, so D <= 3.384 at b1.2.
- C-9dee12ef8e1a (D3.28,g-3.55) 11.923, C-a07aa6172ab6 (D3.3,g-3.53) 11.898, C-59753de6b401 (D3.25,g-3.58) 11.961, C-a7cedecd1f0d (D3.22,g-3.6) 11.981 give dg/dgamma about -1.8 per deg and dg/dD about +0.5 per m, so the g limit at D3.38 is about gamma -3.56.
- C-a07aa6172ab6 (D3.3,b1.18) T393.11 vs C-9dee12ef8e1a (D3.28,b1.18) T393.27 vs C-cbb67c388863 (D3.3,b1.2) T392.78 show that larger D and b lower T and that b is a weak lever.
- C-1b507004c89c and C-de929f2046c9 (b1.22, cone70) fail the cd_fore hull; C-9c1cc1a27672, C-ec5b30508673, C-ca010b12fec4 (b1.35) and C-f986776067bd (b1.3, cone 69) are invalid geometries. b is capped near 1.2 at cone 70.
- Shallow-gamma points C-e735d4570166 (241k, 421 K), C-30939dece9a3 and C-d916d7265dfe (252k, 409 K) and the steep corner C-cbb67c388863 (284k, 392.8 K) leave gaps in the staircase between gamma -2.2 and -3.3, and none of them uses D above 3.36.

**mechanism:** Stagnation flux falls with nose radius and with lower ballistic coefficient (larger D), so D at its mass-fraction ceiling and the largest valid b minimise flux. Bondline temperature tracks heat load, which falls with a shorter and steeper pulse, so gamma should sit just inside the g limit. Because g rises only slightly with D while T falls with D, pushing D to about 3.38 and backing gamma off by about 0.02 deg gives a net T drop of about 1 K. Re-running the whole gamma sweep at D3.375 dominates the older D3.2-3.3 front points and fills the staircase gaps.

**uncertainty:** The mass margin at D 3.38-3.383 is only 0.001-0.003 and the linear fit could be off by that much, so those designs may violate heatshield_mass_fraction. The g margin at gamma -3.56/-3.568 is under 0.1%, and the local slope in gamma is only roughly known. b of 1.205-1.21 may hit the cd_fore hull failure. Flux and T predictions come from eyeballed local fits (D^-1.3 for flux, about -16 K/m and about 1 K per 0.1 deg for T). They are less certain at shallow gamma, where the T slope is steeper (about 1.3-1.6 K per 0.1 deg).

## ai_agent seed_37 call_05  (21 proposals, 0 ask fidelity 1)

**observation:** The feasible front is a one-dimensional curve traced by flight-path angle at D~3.375-3.38 m, bluntness 1.2, cone 70 deg (the variable upper bounds). Flux runs 228k to 275k W/m2 and bondline T runs 418 to 391 K. Two hard limits bind: heatshield mass fraction and max_g. Mass-fraction margin scales as D^2 and does not depend on b, cone or gamma. Margin is 0.006044 at D=3.375, 0.0207 at 3.35 and 0.0013 at 3.383, which puts the ceiling near D=3.385. Peak g depends almost only on gamma (about 1.7 g/deg near -3.56), with a weak rise with D (about 0.43 g/m). It hits 12 g at about gamma=-3.57. Larger D lowers both flux (about -119k W/m2 per m) and T (about -18 K/m). Lower b is worse on both objectives. Bluntness 1.205 and above at cone 70 fails the cd_fore convex-hull check, and b>=1.3 gives invalid geometry. So the remaining gains are pushing D to the mass-fraction ceiling, pushing gamma to the g limit, and filling the front. I also run a few probes of b and cone below their bounds.

**evidence:**
- C-e6bfb3db2b24, C-465478728e6f, C-799a5eaff9e3, C-4749105a6ed4 and C-f3e186a3d6a9: mass margin follows 0.99396*(D/3.375)^2. Ceiling is D~3.385.
- C-e6bfb3db2b24 and C-4749105a6ed4: g is 11.981 at (3.38, -3.56) and 11.982 at (3.35, -3.568), so g barely depends on D. g reaches 12 at about gamma=-3.57.
- C-72093e041d67 to C-f3e186a3d6a9: T falls about 11 K/deg and flux rises about 24k W/m2 per deg as gamma steepens.
- C-4749105a6ed4 vs C-e6bfb3db2b24: smaller D raises both flux and T, so D at its cap is best.
- C-d4ad05ba9bb6 vs C-f3e186a3d6a9: b=1.19 is slightly worse than b=1.2 on both objectives.
- C-207a027e9dd5, C-4d9cd4c2b38d, C-1b507004c89c and C-de929f2046c9: b>=1.205 at cone 70 fails the cd_fore hull check.
- C-f986776067bd, C-9c1cc1a27672, C-e88bc745fe3b and C-51a1525266f1: cone too small for the given b makes the geometry invalid.
- C-114b79b08144 (3.2, 1.1, 69, -3.7) has T 393.8 K and flux 307k, worse than the extrapolated D~3.38 line. This confirms that lower D and b are worse.

**mechanism:** Stagnation heating falls with nose radius (b*D/2) and with lower ballistic coefficient (larger D), so D and b are best at their caps. Bondline temperature follows heat load, which drops for steeper, shorter pulses. Peak g is set mainly by gamma, so the front is traced by gamma up to the g=12 limit. The D cap comes from mass fraction, which scales with D^2. Moving D from 3.375 to 3.384 lowers flux by about 1.1k W/m2 and T by about 0.16 K at every gamma. This shifts the whole front down slightly. The front is convex, so the intermediate gammas add small hypervolume. Probes at b<1.2 and cone<70 check whether any lever beyond this 1-D curve exists. I expect them to be dominated (this relies partly on prior physical reasoning, since the data only covers b=1.1 at cone 69).

**uncertainty:** The g margin near gamma=-3.57 is only about 0.0003 at D=3.384, so the boundary probes may be infeasible. The mass-fraction ceiling at D=3.385 leaves a 0.00014 margin and depends on my D^2 fit. The b and cone probes may hit an extrapolation or geometry failure, since the cd_fore hull boundary and the overlap boundary are not mapped. Flux and T predictions come from linear interpolation and scaling of the D=3.375 line, with errors of a few hundred W/m2 and a few tenths of a K.

## ai_agent seed_37 call_06  (19 proposals, 0 ask fidelity 1)

**observation:** The front is a one-dimensional gamma sweep at the corner D~3.384, bluntness 1.2, cone 70. Along it, flux runs from 227k W/m2 (gamma -1.5) to 275k (gamma -3.57) and bondline T from 417.9 K to 391.1 K. Every other variable is pinned by a limit: D by heatshield mass fraction (margin ~0 at D~3.385), cone at its 70 deg bound, bluntness by the aero-surrogate hull and geometry limit near b=1.2, and gamma by max_g=12 near -3.57. Round 2 (20 geometry failures) shows the danger of leaving this corner, so I stay on it and fill gaps and push the edges.

**evidence:**
- C-636b6aeca4e0 (gamma -3.57, g 11.999) and C-4176038753c7 (-3.568) sit at the g limit, so the steep end of the front is g-limited.
- C-4141cc258747 (D 3.385, mass margin 1.4e-4) and C-636b6aeca4e0 (D 3.384, margin 7.4e-4) give a margin slope of about 5.9e-4 per mm of D, so the D cap is ~3.3852.
- C-099cae65259a (b 1.1), C-8efdd90862a0 (b 1.15, cone 69) and C-26610a6c01d5 (b 1.0, cone 68) violate mass fraction and have higher flux and T than b 1.2, cone 70, so lower b or cone is worse.
- C-de929f2046c9, C-207a027e9dd5, C-4d9cd4c2b38d (b 1.205-1.22) fail hull extrapolation, and C-f986776067bd, C-9c1cc1a27672 (b 1.3-1.35) fail geometry, so b cannot exceed ~1.2.
- C-114b79b08144 (D 3.2, b 1.1, gamma -3.7) has T 393.8 K and is g-infeasible, so smaller D costs T and buys little g.

**mechanism:** Flux falls with nose radius (b*D/2) and with lower ballistic coefficient (larger D). T falls with a shorter, steeper entry pulse and with larger D. g is set almost entirely by gamma, at roughly 1.66 g/deg, with only a weak dependence on D. The feasible optimum therefore lies at the D, b and cone bounds, and the front is traced by gamma from -1.5 to -3.57. Extra hypervolume can only come from filling gaps between existing gamma points and from tiny D increases up to the mass cap (about 0.02% in flux). This rests partly on prior knowledge of the ~1/sqrt(Rn) heating scaling, which I did not check against the data.

**uncertainty:** Interpolated flux and T values along gamma are accurate to a few hundred W/m2 and about 0.3 K. The D=3.3851-3.3852 points sit within 1e-4 of the mass-fraction limit and the gamma=-3.568 points within 4e-4 of the g limit, so they may flip to infeasible if the margin is slightly nonlinear. Gains are small because the front is essentially converged, and some proposed gammas may duplicate rows not shown to me.

## ai_agent seed_37 call_07  (21 proposals, 0 ask fidelity 1)

**observation:** The feasible front is a one-dimensional curve traced by flight-path angle at the corner D≈3.384–3.3852 m, bluntness 1.2, cone 70 deg. Flux runs from 227k to 275k W/m2 and bondline temperature from 391 to 418 K. The corner is set by hard limits. Diameter is capped by heatshield mass fraction, which behaves like 1-k·D^2, so the margin hits zero near D≈3.38524. Bluntness is capped near 1.2 by the aero-surface hull, since 1.205, 1.21 and 1.22 all failed. Cone is at its 70 deg bound. Peak g is set almost entirely by gamma and reaches 12 g near -3.570 deg. The last two rounds added only 0.0001 of hypervolume, so the front is saturated. What remains is a small diameter push and filling gaps along the gamma sweep.

**evidence:**
- C-4bd90cfc37e5 (D 3.3851, gamma -3.568) has mass margin 8.6e-5 and g margin 3.2e-4. C-f76375e28006 (D 3.3852) has mass margin 2.7e-5. That gives about 5.9e-5 of margin lost per 1e-4 m of D, so the zero crossing is near D≈3.38524.
- C-636b6aeca4e0 (gamma -3.57, D 3.384) has g margin 8e-5, so the g=12 limit is near gamma -3.5705.
- C-8efdd90862a0, C-099cae65259a and C-26610a6c01d5 show that lowering bluntness or cone reduces the mass margin and raises flux. Bluntness 1.2 with cone 70 is therefore the best corner.
- C-114b79b08144 (D 3.2) has mass margin 0.103. C-fdb02e4f3a4f (D 3.2, b 0.5, cone 45) is infeasible on mass fraction and has flux 425k. Small or slender designs are dominated.
- C-de929f2046c9, C-207a027e9dd5 and C-4d9cd4c2b38d show that pushing bluntness above 1.2 fails on hull extrapolation, and C-9c1cc1a27672 and C-f986776067bd show that it also fails on geometry.

**mechanism:** Stagnation heating falls with nose radius (b·D/2) and with lower ballistic coefficient (larger D), so D and b should sit at their caps. Bondline temperature follows heat load, which falls for a steeper and shorter pulse, so gamma should sit just inside the g=12 limit. Flux rises and temperature falls as gamma steepens, which traces the trade-off front. Moving D from 3.384 to 3.38522 gives about 120 W/m2 less flux and about 0.03 K less temperature at fixed gamma. That shifts the whole front very slightly and can only lift hypervolume marginally. Shallow-gamma points at D 3.38522 fill the gaps between the existing front points.

**uncertainty:** The gains are tiny, of order 1e-4 in normalised hypervolume. The D cap estimate assumes the mass margin is linear in D. If it is not, the D=3.38522 designs could fail the mass constraint by about 1e-5, and they would all fail together. The predicted flux and temperature come from linear interpolation between neighbouring evaluated gammas. The D effect is a correction extrapolated from only three D values. The g margin near -3.570 deg is a few 1e-4 and could flip.

## ai_agent seed_37 call_08  (20 proposals, 0 ask fidelity 1)

**observation:** The front is a one-parameter curve. Every non-dominated point sits at the corner D≈3.3852 m, bluntness 1.2, cone 70°, and only gamma varies from -1.5 to -3.5702 deg. The three limits box the corner in. Mass fraction caps D at about 3.3852 m, with a margin of 1.5e-5. Bluntness above 1.2 fails geometry or aero-hull checks. Cone is at its 70 deg bound. Peak g is about 12 at gamma -3.5702. Moves off the corner are dominated or infeasible: lower bluntness or cone violates mass fraction, and smaller D raises flux and temperature. Round 6 and 7 gains were about 1e-4 in normalised hypervolume, so only gap-filling along gamma remains.

**evidence:**
- C-895ab2d00f94 (gamma -1.5) to C-3da19764396f (gamma -3.5702): flux rises 227.2k to 274.6k W/m2 and bondline T falls 417.9 to 391.1 K, all at D=3.3852, b=1.2, cone 70.
- C-3da19764396f has g margin 1.2e-5 and mass-fraction margin 1.5e-5, so the corner is bounded on both.
- C-8efdd90862a0, C-099cae65259a and C-26610a6c01d5: lower b or cone at D=3.384 gives negative mass-fraction margin and no flux gain.
- C-114b79b08144 (D 3.2, gamma -3.7) violates g at 12.14, and C-7e930f570744 shows that smaller D with steeper gamma does not reduce T.
- C-f986776067bd, C-9c1cc1a27672, C-207a027e9dd5 and C-4d9cd4c2b38d: b above 1.2 at cone 70 fails on geometry or surrogate extrapolation.
- Sparse gamma spans remain at -2.72 to -2.95, -2.95 to -3.16, -2.36 to -2.56, -1.92 to -2.08 and -3.16 to -3.34.

**mechanism:** Flux falls with nose radius (b*D/2) and lower ballistic coefficient. Bondline T follows heat load, so it falls with larger D and a steeper, shorter pulse. Peak g is set almost entirely by gamma at about 1.67 g/deg, so gamma at the g=12 limit traces the trade-off. With D, b and cone pinned at their bounds, the remaining hypervolume comes from densifying the gamma sweep. I interpolated flux and T between neighbouring evaluated points, since both vary smoothly and monotonically with gamma at fixed geometry. This is data-driven interpolation, not prior physics.

**uncertainty:** Each proposal changes only gamma from a parent with the same D, b and cone. Feasibility is safe except at the g limit, where -3.57026 is within about 1e-4 g of the boundary. Interpolated values are probably good to a few 100 W/m2 and a few tenths of a K. Gains will be tiny because the curve is smooth. I have not found a different region that could shift the front, and the data does not indicate one.

## ai_agent seed_37 call_09  (20 proposals, 0 ask fidelity 1)

**observation:** The feasible front is a one-parameter curve: D=3.3852 (pinned by mass fraction, margin 1.5e-5), b=1.2 and cone=70 are all at their limits, and only gamma varies. Flux rises from 227k to 274.6k W/m2 and bondline T falls from 417.9 K to 391.1 K as gamma steepens from -1.5 to -3.5703, where max_g reaches 12. Moving off the corner has not paid: lower b or cone violates mass fraction (C-8efdd90862a0, C-099cae65259a, C-26610a6c01d5), smaller D raises flux and T (C-114b79b08144), and b>1.2 fails on geometry or surrogate extrapolation (C-f986776067bd, C-de929f2046c9, C-207a027e9dd5, C-4d9cd4c2b38d). The only remaining hypervolume is in the gaps of the gamma sweep, so all 20 proposals change gamma only.

**evidence:**
- C-ee7fb6bb3da7 (gamma -3.5703): g=12.0 with margin 1.1e-5, so the steep end is saturated.
- C-5f4e033c35a8 (gamma -1.55) and C-895ab2d00f94 (gamma -1.5): the shallow end is at the gamma bound.
- Mass-fraction margin is 1.496e-5 for every D=3.3852 row regardless of gamma, so a gamma-only change keeps the parent's D and mass-fraction margin.
- Gaps in the gamma sweep: -2.46 to -2.64, -2.64 to -2.84, -2.15 to -2.29, -1.85 to -1.99, -2.9 to -3.05 and -3.26 to -3.38.
- C-114b79b08144 (D=3.2, gamma -3.7) is worse in T at a given g and infeasible on g, so trading D for steeper gamma does not help.
- Front spacing is roughly linear in gamma: about 24k W/m2 per deg in flux and about -10 K per deg in T, so linear interpolation gives good predictions.

**mechanism:** The two objectives trade off along gamma through the entry pulse: a steeper entry gives a higher peak flux and a shorter, lower-load pulse, so bondline T is lower. Peak g is set almost entirely by gamma (about 1.67 g/deg) and caps gamma near -3.5703. D, b and cone sit at their bounds, so they minimise flux and T together. The remaining hypervolume comes from filling gaps in the front with midpoints, weighted toward the largest gaps. This relies on the data plus standard stagnation-heating and ballistic-coefficient scaling.

**uncertainty:** Expected gains are tiny, at most about 1e-4 in normalised hypervolume, because the front is already dense. Interpolated flux and T should be accurate to about 0.2 K and about 300 W/m2. The -3.57035 point sits about 5e-5 deg beyond the last feasible point, so its g margin is nearly zero and it could fail. I cannot exclude some of these gammas having been evaluated in unseen rows, though I used three-decimal values ending in 5 to reduce that risk.

## ai_agent seed_41 call_01  (20 proposals, 0 ask fidelity 1)

**observation:** No feasible design exists yet. 10 of 20 evaluations failed on geometry and none of the 10 valid ones is feasible. The geometry failures fit a closed-form rule: the fore-cone length is (R - Rs(1-cos t) - Rn cos t)/tan t, with Rn = bluntness*D and Rs = 0.1*D. This is equivalent to (bluntness - 0.1)*cos(cone_half_angle) <= 0.4, independent of D. I reproduced the reported negative lengths of -48.9 mm (C-0e7ec9742f84) and -22.8 mm (C-2e989122c857), and it separates every valid row from every invalid row. I keep this quantity <= ~0.38 in every proposal. The limits implied by the margins are max_g 12.0 and bondline 450 K. Heatshield mass fraction scales roughly as 0.09*D^2 in units of its limit, which puts D at about 3.3 or below. Max_g is mainly set by flight-path angle, so gamma should be about -3.0 to -3.8 deg. On the valid points, flux falls with larger D and larger bluntness, and bondline temperature falls with larger D, steeper gamma and larger bluntness. So I target D ~3.0-3.3, high bluntness, cone angle 60-70 deg and gamma ~-3.5 deg.

**evidence:**
- Geometry rule check: C-cf5ade290acc (b=1.076, cone 33.9) gives 0.98*0.83=0.81 > 0.4, invalid. C-63aaa0985529 (b=0.523, cone 29.7) gives 0.37 <= 0.4, valid. C-7fd3f4505944 (0.65*0.80=0.52) is invalid and C-f97dae207371 (0.26) is valid. All 20 rows are consistent.
- Max_g limit is 12.0: C-50a0a474d0f6 has 12.059 with margin -0.0049. The limit for bondline temperature is 450 K, from C-ee99f55de428 (455.54 with margin -0.0123).
- Max_g vs gamma: 9.4 g at -1.85 (C-f97dae207371), 10.2 g at -2.64 (C-ee99f55de428), 12.5 g at -4.10 (C-63aaa0985529), 13.1 g at -4.26 (C-ab9827dc6929), 16.2-17.2 g at about -6 (C-baa2f9e65f32, C-26bc5a06b4e4, C-12010dd082dd). Small D looks slightly worse: C-50a0a474d0f6 reaches 12.06 g at only -3.1 deg. I therefore stay at gamma >= -3.9.
- Mass fraction divided by D^2 is about 0.089-0.091 for cone >= 62 (C-36f9165b9496, C-baa2f9e65f32, C-c72c38c9187a, C-12010dd082dd), 0.097-0.101 for cone 42-53, and 0.11 for cone 30-38 (C-63aaa0985529, C-f97dae207371). The margin is 0.028 at D=2.985 with cone 29.7 and -0.004 at D=3.21 with cone 52.8, so high cone angle allows a larger D.
- Bondline temperature fit on the valid rows: T-300 ~ 103*(D/3.21)^-0.8*(sin|gamma|/0.0743)^-0.4*(b/0.399)^-0.2, anchored on C-ab9827dc6929. It reproduces C-f97dae207371 (444.7), C-36f9165b9496 (398), C-26bc5a06b4e4 (373) and C-baa2f9e65f32 (373.6) to within a few K.
- Flux fit anchored on C-ab9827dc6929 (479 kW/m2): q ~ 479k*(D/3.21)^-1.5*(b/0.399)^-0.5*(sin|gamma|/0.0743)^0.3. It matches C-26bc5a06b4e4, C-baa2f9e65f32 and C-c72c38c9187a within ~10%. C-63aaa0985529 (cone 29.7) is ~15% above the fit, which suggests small cone angles raise flux.
- C-36f9165b9496 (b=0.87, cone 65) has the lowest bondline temperature of the mid-size designs (398 K at D=2.55) and fails only max_g (gamma -4.86). Raising D to ~3.1 and easing gamma to ~-3.6 should make it feasible.

**mechanism:** Peak heating falls as ballistic coefficient falls (larger D, higher drag from a blunter and wider cone) and as nose radius grows. Bondline temperature follows the integrated heat load, which is lower for steeper entry and higher for shallow entry, where the soak time is long. Peak deceleration is set mainly by entry angle, so shallow gamma protects max_g but raises bondline temperature. The best compromise is the largest D the mass-fraction limit allows, high bluntness with a cone wide enough to keep the geometry valid, and gamma of about -3.5 deg. High cone angle also reduces heatshield area, which buys diameter.

**uncertainty:** The scalings are my own fits to only 10 valid points, plus a physics prior for exponents. The bluntness effect beyond b=0.87 is extrapolated, since no valid point has b above 0.87. The g dependence on D and cone is poorly constrained. The mass-fraction limit near D=3.3 rests on a ~0.089*D^2 fit. The flux dependence on cone angle is only hinted at by C-63aaa0985529.

## ai_agent seed_41 call_02  (20 proposals, 2 ask fidelity 1)

**observation:** All 16 feasible designs sit in a narrow cluster: D 2.9-3.35 m, cone 55-70 deg, bluntness 0.5-1.15, gamma -3.0 to -3.9. C-11dcf14fd72e is the only feasible non-dominated point (287250 W/m2, 393.73 K). The hypervolume is about 0.885*0.375 = 0.332, so it is set entirely by that one point. With a 2.5e6 W/m2 reference against a 450 K one, 1 K of bondline temperature is worth roughly 40,000 W/m2 of peak flux. I should therefore push bondline temperature down first, then flux. Three limits bind: max_g (12 g), heatshield mass fraction (large D), and a geometry-validity boundary.

**evidence:**
- Mass fraction: 1 - margin divided by D^2 is nearly constant at 0.0877-0.0889 (C-11dcf14fd72e 0.0877, C-4f7f664531cd 0.0874, C-14caae5709dc 0.0889). It falls slightly with higher bluntness and cone angle. The mass limit is therefore D of about 3.37-3.38 m at b >= 1.15 and cone 70.
- max_g: at gamma -3.5 it is 11.87 for D >= 3.25 (C-11dcf14fd72e, C-a687c9db7052, C-deeb5fd5f24a) and 11.77 for D 3.1 (C-cb5b9b5d5a6b). The slope is about 1.7 g/deg (C-dc1d6416cb31 to C-22c8ef75dedb to C-0be4678d643c). Gamma of about -3.57 is therefore the g limit at D 3.35.
- Gamma trade: C-dc1d6416cb31 (gamma -3.0) vs C-e964c99bacf1 (gamma -3.4) at the same b, cone and D shows +11100 W/m2 and -4.56 K for 0.4 deg steeper. A steeper gamma is the cheapest way to lower bondline temperature.
- Bluntness at D 3.1, cone 70: C-cb5b9b5d5a6b (b 1.1) 315290 W/m2, 397.73 K; C-4f7f664531cd (b 1.15) 312530 W/m2, 397.39 K. Lower b is worse: C-6e14665f4a23 (b 0.7) 402.47 K and C-6c22d4ab2deb (b 0.5) 408.52 K. Cone angle has little effect at fixed b (C-14caae5709dc vs C-7105f85b6659).
- Geometry failures fit a rule with all 8 failed rows and the valid rows: cos(cone)*(2*b - 0.2) must be below 0.8. For example C-2e989122c857 gives 0.872, which predicts -22 mm against the reported -22.8 mm. C-de1dd6ca3952 gives -716 mm predicted and -715.7 mm reported. At cone 70, b must be at most about 1.24; at cone 68, at most about 1.14; at cone 69, at most about 1.19. I keep all proposals inside this rule with a margin.
- C-63aaa0985529 (cone 29.7, b 0.52) and C-62348c286fc5 (cone 40, b 0.5) have bondline temperatures of 409.6 K and 418.35 K. Low bluntness and low cone are clearly worse, so the search should stay at high b and cone.

**mechanism:** Peak flux falls with larger nose radius (bluntness times D) and lower ballistic coefficient (larger D). Bondline temperature follows the integrated heat load, which is lower for steeper entry and for lower flux. Peak g is set mainly by gamma, with a weak dependence on D. The best design is therefore the largest D that the mass-fraction limit allows (about 3.36-3.38 m), the highest valid bluntness at cone 70 (about 1.2-1.24), and the steepest gamma with g under 12 (about -3.5 to -3.57). Shallower-gamma points at the same geometry add lower-flux, higher-temperature points for front coverage. The D^-1.4 flux scaling and the linear gamma slopes are empirical fits to this data. The soak-time argument is prior physical knowledge.

**uncertainty:** The g dependence on D and b is poorly resolved; D3.25, D3.3 and D3.35 give the same g at gamma -3.5, but D3.1 is lower. Points within 0.02 of g = 12 may fall either way. The mass-fraction coefficient at b > 1.15 is extrapolated, so the D 3.38 probe could go infeasible. The flux and temperature at gamma shallower than -2.6 are extrapolations; the temperature may rise nonlinearly. The b 1.24 and cone 70 geometry sits close to the validity boundary (predicted fore-cone length about 12 mm), so a failure is possible if my fitted rule is slightly off.

## ai_agent seed_41 call_03  (20 proposals, 2 ask fidelity 1)

**observation:** The feasible front is essentially a one-dimensional gamma sweep at D≈3.36-3.37 m, bluntness 1.2, cone 70 deg. Flux rises about 24 kW/m2 per degree of steeper entry and bondline temperature falls about 10-14 K per degree. The front is closed on the steep side by max_g (limit about 12.0, reached near gamma -3.58) and on the large-D side by heatshield mass fraction (margin near 0 at D≈3.385). Cone 70 is the upper bound. Bluntness above about 1.2 at cone 70 returns 'no geometry' from surrogate extrapolation (4 failures at 1.22-1.24).

**evidence:**
- C-af5b99c2201c through C-df105fb625ce: at D 3.36-3.37, bluntness 1.2, cone 70, flux runs 243.6k to 277.1k and bondline 407.4 K to 391.7 K as gamma goes from -2.2 to -3.55. Both trends are smooth and near-linear.
- C-2a109f1c4205 (gamma -3.58) has max_g margin -0.0005, and C-df105fb625ce (gamma -3.55) has margin +0.0037. The g limit therefore sits near gamma -3.57 at D 3.36.
- C-ba7e63c2eae5 (D 3.2), C-757eacb03d61 (D 3.3) and C-77cd7361eded (D 3.1) all have higher flux and bondline temperature than D 3.36 at similar gamma. Larger D is better, and it is capped by mass fraction: margin 0.0149 at D 3.36 and 0.0090 at 3.37, extrapolating to zero near 3.385.
- C-de59f8abeee6, C-ae614eb129f2, C-fc8f94cd132b and C-d5f231dc1870: bluntness 1.22-1.24 at cone 70 fails on the cd_fore hull. C-0a3bfd5f8237 (b 1.15, c 69) and C-19b8d4ea2ba7 (b 1.1, c 68) are slightly worse than b 1.2, c 70 at the same gamma.
- C-ee99f55de428 and C-50a0a474d0f6 (small D, low bluntness) have flux of 0.75-1.5 MW/m2 and bondline above the 450 K limit. Only the large, blunt, high-cone corner is competitive.

**mechanism:** Peak flux falls with larger nose radius and lower ballistic coefficient (larger D, higher drag). Bondline temperature follows the integrated heat load, which falls for steeper entry and lower flux. Peak g rises with gamma steepness, and slightly with D at fixed gamma. The best trade-off is the largest D the mass limit allows, bluntness and cone at their buildable maxima, and gamma at the g limit. In hypervolume terms 1 K of bondline temperature is worth about 0.006, while 10 kW/m2 of flux is worth only about 0.004. So this round nudges D up to 3.38 (about -1.3 kW/m2 and -0.3 K versus 3.37), pushes gamma toward the g limit, and extends the shallow-gamma flux end. Small bluntness, cone and D probes are included to check whether the corner can move.

**uncertainty:** The g and mass-fraction limits are extrapolated linearly. The D 3.38 mass margin is estimated at about +0.003, and D 3.385 is nearly zero. Gamma -3.565 at D 3.38 is within about 0.001 in g of the limit. The hull boundary for bluntness above 1.2 is unknown and b 1.21 may fail. Predictions for shallow gamma below -2.2 extrapolate the flux and temperature slopes, and curvature could shift them by a few kelvin.

## ai_agent seed_41 call_04  (20 proposals, 1 ask fidelity 1)

**observation:** Every non-dominated point comes from one family: D≈3.38 m, bluntness 1.2, cone 70 deg, with only flight-path angle varied. Along it flux rises from 228k to 275k W/m2 and bondline temperature falls from 418 K to 391 K as entry steepens. max_g (about 12 at gamma≈-3.57) and the mass-fraction limit (D<~3.3855 m) are the binding constraints. Bluntness and cone are pinned at the edge of the aero surrogate's hull. Bluntness 1.21 or more fails at cone 70, and cone 69 fails at bluntness 1.2. Smaller-D, lower-bluntness, lower-cone designs are clearly dominated. The remaining gains are small: a slightly larger D and a denser gamma sweep.

**evidence:**
- C-733cdcb996ae (D 3.385, gamma -3.5) gives 272900 W/m2 / 391.77 K, against 273480 / 391.85 for C-41b2ddb7397c (D 3.38, same gamma). Larger D dominates slightly, and its mass margin is only 0.000145.
- Mass margin is independent of gamma (0.003097 across the D 3.38 sweep) and falls about 0.59 per metre of D. That puts the limit near D≈3.3855, so I keep D=3.385.
- max_g at D 3.38 is 11.881 at -3.5, 11.963 at -3.55 and 11.989 at -3.565. C-2a109f1c4205 (D 3.36, -3.58) gives 12.006 and is infeasible, so the g limit sits near gamma≈-3.57. D changes g only weakly (about +0.4 per m).
- C-3d41ce848a30, C-98457c6f78bd, C-ae614eb129f2 and others show that bluntness above 1.2 or cone below 70 at bluntness 1.2 hits surrogate extrapolation and returns no metrics.
- Off-family designs such as C-22c8ef75dedb (322k, 395.7 K, infeasible), C-960c10206981 and C-ee99f55de428 are worse in flux or temperature than the D 3.38 family.

**mechanism:** Peak flux falls with larger nose radius and lower ballistic coefficient, so the largest D that meets the mass limit is best. Peak g is set almost entirely by gamma, so it caps steepness at about -3.57. Bondline temperature falls with steeper entry, so the best designs sit at the g limit. I have no data suggesting another geometry beats this family, so I refine it: D=3.385 for a small uniform gain, and a denser gamma sweep including points just inside the g limit. Interpolated values come from the D 3.38 sweep with a D correction of about -0.2% flux and -0.08 K.

**uncertainty:** The main risk is the g margin near gamma -3.56 to -3.568, where I estimate g at 11.99-11.996 against a limit of 12. Whether bluntness 1.205 lies inside the surrogate hull is unknown, and that probe may return no geometry. Gains per point are tiny (about 0.2% flux, 0.1 K). The reduced-order model's own noise or discreteness could exceed them. No other region has been shown to be promising.

## ai_agent seed_41 call_05  (19 proposals, 0 ask fidelity 1)

**observation:** Every non-dominated feasible design lies on one curve: D about 3.385 m, bluntness 1.2, cone 70 deg, with only the flight-path angle varying from -1.5 to -3.568 deg. Steeper entry lowers bondline temperature (418 K to 391 K) and raises peak flux (227k to 275k W/m2) and max_g, which reaches the 12 limit at about -3.570 deg. Bluntness 1.2 and cone 70 sit at the corner of the region the aero surrogate can evaluate. Every probe beyond it (bluntness 1.205 to 1.24, or cone 69 at bluntness 1.2) failed with an extrapolation error. D is capped by the heatshield mass fraction, whose margin at D=3.385 is only 1.4e-4. The front is therefore nearly converged, and the remaining gains are small: fill gaps in gamma, push right up to the g limit, and probe a few interior points.

**evidence:**
- C-e008d92646a9 (gamma -3.568) has max_g margin 0.00036, and C-2a109f1c4205 (D 3.36, gamma -3.58) has margin -0.0005. The g limit is therefore crossed near gamma -3.570.
- C-99ca3bd26693, C-19d0802140ac and C-e008d92646a9 give a local slope of about 1.7-1.8 g per deg. C-50a0a474d0f6 and C-960c10206981 suggest g falls with D by about 0.44 g per m.
- D 3.38 has mass margin 0.003097 and D 3.385 has 0.0001449, a slope of about -0.59 per m. The limit is therefore near D 3.3852.
- C-ea0e387c4c00, C-98457c6f78bd, C-ae614eb129f2 and C-de59f8abeee6 all failed on cd_fore extrapolation. Probes beyond bluntness 1.2 or below cone 70 at bluntness 1.2 are unsafe.
- C-22c8ef75dedb (D 3.2, bluntness 0.87, cone 65) has flux 322k and T 395.7 K. This is dominated by the D 3.385 family at similar gamma, so lower bluntness and smaller D cost flux.
- Front gaps at D 3.385 remain between the evaluated gammas -1.6/-1.8/-2.0/-2.2, -2.3/-2.6/-2.8, -2.95/-3.1/-3.25 and -3.25/-3.35/-3.42.

**mechanism:** Peak flux falls with nose radius (bluntness x D) and with ballistic coefficient. This is prior knowledge, as I fit the exponents only roughly: flux is roughly proportional to D^-1.5 times bluntness^-0.5 to -0.7. Bondline temperature falls with steeper gamma because the soak is shorter. Peak g depends almost only on gamma, with a weak positive dependence on D. The front is therefore a one-parameter curve in gamma. It ends at the g limit on the steep side and at the -1.5 deg bound on the shallow side. Bluntness, cone and D sit at their buildable maxima. About half of this batch densifies the curve, two proposals push to the g limit and D limit, and the rest probe interior bluntness and D values to check that nothing off the curve is better.

**uncertainty:** The flux and T interpolations between evaluated gammas are reliable. The exponents for bluntness and D are from prior knowledge and are rough. The bluntness 1.0-1.15 probes could hit the surrogate convex-hull limit or have different mass-fraction behaviour. Near-limit proposals at the g and mass limits could flip to infeasible by rounding, since their margins are about 1e-5.

## ai_agent seed_41 call_06  (20 proposals, 0 ask fidelity 1)

**observation:** The front is a one-parameter family at D=3.385, bluntness 1.2, cone 70, swept in flight path angle. It runs from gamma -1.5 (flux 227k W/m2, bondline 417.9 K) to the g limit at gamma about -3.57 (flux 274.6k, 391.1 K). D is capped by the mass-fraction limit at about 3.3852. Bluntness and cone are at the edge of the region where the cd_fore surrogate can be evaluated. Hypervolume has barely moved over the last three rounds (0.3545, 0.3554, 0.3555), so only small gains remain. I use this round to fill gaps along the family and to test tiny D and gamma refinements at the g and mass limits.

**evidence:**
- C-81e40e27ff03 (gamma -3.57) has g margin 4.7e-5 and mass margin 1.4e-4. C-96e48a93fd32 (D 3.3852, gamma -3.5695) has mass margin 2.7e-5 and g margin 1.2e-4. Together they put the D ceiling near 3.38524 and the gamma cap near -3.570.
- C-2a109f1c4205 (D 3.36, gamma -3.58) and C-363a563b3536 (D 3.3, gamma -3.58) are dominated by the D=3.385 family. Flux rises by about 10k for a 0.085 m drop in D, roughly a D^-1.5 dependence, while the g limit allows only a very small gamma gain.
- C-7112b6b29bcf, C-14444dd6b10a, C-9961e7e6987c and C-67c6047be079 show that lowering bluntness or cone both raises flux and breaks the mass-fraction limit.
- C-ea0e387c4c00, C-ae614eb129f2, C-3d41ce848a30 and C-98457c6f78bd fail on cd_fore extrapolation for bluntness above 1.2 or cone below 70 at bluntness 1.2, so (1.2, 70) is the corner of the valid region.
- Rows from C-948029610632 (gamma -1.5) to C-81e40e27ff03 (gamma -3.57) form a smooth, convex flux-vs-bondline curve. About 0.001 deg of gamma near the cap trades about 10 mK for about 22 W/m2.

**mechanism:** Peak flux falls with nose radius (bluntness x D) and with ballistic coefficient (larger D), so D, bluntness and cone are pushed to their limits. Peak g depends mainly on gamma, with a weak positive dependence on D of about 0.4 g/m. Bondline temperature falls as entry gets steeper because the soak time is shorter. The trade-off is therefore set by gamma alone, from shallow (low flux, hot bondline) to the g cap (higher flux, cooler bondline). Physics here is from the data plus prior knowledge: in Allen-Eggers theory peak g is independent of ballistic coefficient. I expect more gamma points to add only a small hypervolume gain, and the D and gamma micro-tweaks to add almost none.

**uncertainty:** Some proposed gamma values may already have been evaluated in the truncated rows I cannot see. The micro-tweaks near the mass and g limits could fall just over either limit, since I am extrapolating locally linear slopes to about 1e-5 relative margin. The interpolated flux and temperature values are linear estimates. The true curve is convex, so actual values should sit slightly below them. I have no data on any geometry outside this family that could beat it.

## ai_agent seed_41 call_07  (21 proposals, 0 ask fidelity 1)

**observation:** The feasible front is a one-parameter curve in flight_path_angle_deg. Every front point has D≈3.385, bluntness 1.2 and cone 70, and only gamma varies. It runs from (227k W/m2, 417.9 K) at gamma -1.5 to (274.6k, 391.1 K) at the max_g limit near gamma -3.570. HV has stalled at about 0.3555 for the last three rounds. The other limits are also hit. Mass fraction caps D at about 3.3852, since the margin is about 1.4e-4 at D=3.385. Bluntness above 1.2 and cone below 70 return extrapolation failures. Lower bluntness gives negative mass margin.

**evidence:**
- C-948029610632 to C-bdc4c0de77cb: the front runs from gamma -1.5 to -3.5702 at fixed D, bluntness and cone, with flux rising about 47k and temperature falling about 27 K.
- C-bdc4c0de77cb and C-4440e1af7d55: D=3.3852 sits at both the max_g and mass_fraction limits, so there is no room left in D or gamma.
- C-363a563b3536 (D=3.3) and C-2a109f1c4205 (D=3.36): smaller D raises flux and does not help temperature. g rises about 0.4 g/m with D and about 1.65 g/deg with gamma.
- C-7112b6b29bcf, C-14444dd6b10a, C-9961e7e6987c: lowering bluntness raises flux and makes the mass margin negative.
- C-de59f8abeee6, C-ae614eb129f2, C-98457c6f78bd, C-ea0e387c4c00: bluntness above 1.2 or cone below 70 at bl 1.2 are outside the cd_fore hull, so the corner (bl 1.2, cone 70) is the buildable optimum.
- C-960c10206981 and C-3edf701da501: smaller D with steeper gamma gives 356-372k flux with about 399-402 K, dominated by the front.

**mechanism:** Peak flux falls with nose radius and with ballistic coefficient, which is why D, bluntness and cone are pushed to their limits. Mass fraction caps D. Bondline temperature falls with steeper gamma through a shorter soak, and max_g caps how steep gamma can go. The trade-off is therefore set by gamma alone. The flux exponent in D of about -1.5 is fitted from C-363a563b3536 against the D=3.385 rows. The remaining HV gain is small, from filling gaps on the curve and from pushing D from 3.385 to 3.3852. The interpolated outcomes below are between neighbouring front rows; the exploratory D=3.2 row is an extrapolation, and that flux rests on my fitted exponent.

**uncertainty:** The gains are tiny because the front is saturated. The D=3.3852 rows sit about 1e-5 from the mass-fraction limit, and the tiny margin differences between C-4440e1af7d55 and C-bdc4c0de77cb suggest a slight gamma dependence, so some of them could turn out infeasible. The interpolated values are accurate to about 0.5 K and about 500 W/m2. The D=3.2 point is a probe and I expect it to be dominated.

## ai_agent seed_41 call_08  (24 proposals, 0 ask fidelity 1)

**observation:** The feasible front is a one-parameter curve in flight-path angle. Every non-dominated design sits at D≈3.385, bluntness 1.2 and cone 70, which is the corner of the buildable set. Steeper entry raises peak flux (227k to 274.5k W/m2) but lowers bondline temperature (417.9 K to 391.1 K). The curve ends at the max_g limit of 12 g near gamma -3.5702. D is capped by heatshield_mass_fraction: margin is 1.45e-4 at D=3.385 and 1.50e-5 at D=3.3852, so the limit is near D≈3.38522. Bluntness above 1.2 or cone below 70 at bluntness 1.2 returned aero-surface extrapolation failures (8 recent failures). Lower bluntness or a smaller cone makes the mass fraction worse and the flux higher. Seven rounds have moved hypervolume only from 0.35549 to 0.35556, so the front is nearly saturated.

**evidence:**
- C-bdc4c0de77cb and C-4440e1af7d55: D=3.3852 at gamma -3.5702 and -3.5701 give max_g margin 1.4e-5 and 2.6e-5, with mass margin 1.5e-5 to 2.1e-5. The g and mass limits are both tight there.
- C-82835f5d20dc (D=3.385, margin 1.449e-4) versus C-2e083001bf4e (D=3.3852, margin 1.496e-5): mass margin falls about 0.65 per metre of D, and it does not depend on gamma across the D=3.3852 rows. This puts the D limit near 3.38522.
- C-7112b6b29bcf, C-14444dd6b10a, C-9961e7e6987c: bluntness 1.15, 1.10 and 1.0 at D=3.385 all violate mass fraction (-0.0013, -0.0027, -0.0053), and flux rises. Bluntness 1.2 is best.
- C-ae614eb129f2, C-3d41ce848a30, C-ea0e387c4c00, C-98457c6f78bd: bluntness 1.205 to 1.22, or cone 69 at bluntness 1.2, fail the cd_fore convex hull. Bluntness 1.2 with cone 70 is a hull vertex, so no direction beyond it is available.
- C-8f7d32450d14 (D=3.2, gamma -3.61): T=394.0 K and flux 298.9k are worse than the D=3.385 front, and the g gain from a smaller D is only about 0.3 g/m. A smaller D does not pay for a steeper gamma.

**mechanism:** Flux falls with larger nose radius and lower ballistic coefficient, so D, bluntness and cone go to their limits (D by mass fraction, bluntness and cone by the geometry hull). Bondline temperature falls as gamma steepens, which shortens the soak, and max_g caps gamma near -3.5703. Peak g is set almost entirely by gamma, with a weak D dependence I estimated at about 0.3 g/m. What remains is to fill the gamma curve at the largest D the mass limit allows (about 3.385215 to 3.38522). This gives tiny but strictly non-dominated gains over the D=3.3852 points, and it also places designs in the gaps between existing gamma values. Flux and T values below are interpolated from neighbouring rows on the same curve. I have no data for anything outside this family.

**uncertainty:** Expected hypervolume gain is very small (on the order of 1e-5 in normalised terms). The two D=3.38522 proposals and the gamma -3.5703 proposals sit within about 2e-6 of the mass or g limit, so a small nonlinearity could make them infeasible. My mass-margin slope of 0.65 per metre comes from two points. I cannot rule out a better region elsewhere (for example a different bluntness/cone pair inside the hull), but 153 evaluations show nothing better than this corner.

## ai_agent seed_41 call_09  (24 proposals, 0 ask fidelity 1)

**observation:** The front is a one-parameter curve in flight_path_angle_deg. Every good design sits at D=3.3852, bluntness=1.2, cone=70. D is capped by heatshield_mass_fraction, which has near-zero margin (1.5e-5 to 1.8e-5) at D=3.3852. Bluntness and cone are capped by the aero-surface convex hull, since the 1.205 to 1.24 bluntness and cone=69 probes all failed extrapolation. Peak g is capped at 12 by gamma near -3.5703. Normalised hypervolume has plateaued at 0.3556 over the last five rounds. With one round and 24 evaluations left, the remaining gain is filling the gaps along the gamma line.

**evidence:**
- C-9af34480dd37 and C-42bf20532268: gamma=-3.5703 gives g=12.0 with margin ~1.4e-5 to 2e-5, so this is the steep end of the front.
- C-895ab2d00f94: gamma=-1.5 is the shallow bound, with flux 227200 and T=417.87.
- Consecutive front points at gamma -1.5, -1.8, -1.9, -2.15, -2.3, -2.4 and -2.72 leave gaps of 0.1 to 0.32 deg. Flux and temperature vary smoothly and nearly linearly between them.
- C-2a109f1c4205 (D=3.36) has flux 277780 against 274560 at D=3.3852. Smaller D therefore costs flux and gives no compensating g benefit, so the D=3.3852 line stays dominant.
- C-7112b6b29bcf, C-14444dd6b10a, C-9961e7e6987c and C-67c6047be079: lowering bluntness or cone raises flux and violates the mass fraction, so they are dominated.
- Rows C-de59f8abeee6, C-ae614eb129f2, C-3d41ce848a30, C-98457c6f78bd and C-ea0e387c4c00 (geometry failures): stepping outside the hull wastes evaluations.

**mechanism:** Flux falls with nose radius and lower ballistic coefficient, and bondline temperature falls with steeper entry because the soak is shorter. This is partly prior knowledge and partly fitted to the front rows. Since D, bluntness and cone are all at their limits, only gamma trades the two objectives. Filling gaps in gamma with linearly interpolated flux and temperature adds small but certain non-dominated points, and every proposal stays at the known-feasible D=3.3852.

**uncertainty:** The interpolated values assume smooth, near-linear variation. The true curve is slightly convex, so actual values may sit a little below the linear estimates, which would only help. Some gamma values may already have been evaluated in rows I cannot see. Gains per point are tiny because the front is nearly saturated. No exploratory off-line designs are included, since the data give no evidence that any beats this family.

## ai_agent seed_41 call_10  (1 proposals, 0 ask fidelity 1)

**observation:** Only one evaluation remains. All 85 front members appear to lie on a one-parameter family: D=3.3852 (mass-fraction limit), bluntness 1.2 and cone 70 (edge of the aero surrogate hull) held fixed, with flight-path angle setting the trade-off. Flux rises and bondline temperature falls as gamma steepens. Gamma is capped at about -3.5703 by max_g and at -1.5 by the variable bound. Changing D, bluntness or cone has failed repeatedly, through a mass-fraction violation, a geometry failure or surrogate extrapolation, so I leave them alone. The widest visible gap in the listed gamma coverage is between -1.5 and -1.73, so I fill it.

**evidence:**
- C-895ab2d00f94 (gamma -1.5): flux 227200, Tb 417.87, feasible, max_g margin 0.2317.
- C-9fa328647bb7 (gamma -1.73): flux 231790, Tb 414.12, feasible.
- C-adca91e5651d (gamma -1.77) and C-e187d3d3634a (gamma -1.85) show the local slope: about 20000 W/m2 per deg in flux and about -16 K per deg in temperature.
- Every off-family neighbour was either infeasible or failed: bluntness at or below 1.15 gives a mass-fraction violation (C-7112b6b29bcf), and bluntness above 1.2 or cone below 70 with D near 3.38 gives surrogate extrapolation failures (C-ae614eb129f2, C-98457c6f78bd).

**mechanism:** Bluntness, cone and D are pinned at their limits, so only gamma trades the two objectives. Shallower entry gives lower peak flux and a longer soak, hence a hotter bondline. Peak g is about 9.2 to 9.4 here, well inside the 12 g limit. A point at gamma -1.62 lies between two known front points. Flux and temperature vary smoothly and slightly convexly with gamma, so it should sit just below the linear chord in both objectives. That makes it weakly non-dominated and a small certain hypervolume gain.

**uncertainty:** Rows not shown may already cover gamma near -1.62, in which case the gain is negligible. The list of non-dominated points is truncated (12 shown of 85). The interpolated values could be off by a few hundred W/m2 or about 0.3 K. Feasibility is very likely, because all margins are comfortable except the mass fraction, which does not depend on gamma.

## ai_agent seed_59 call_01  (20 proposals, 0 ask fidelity 1)

**observation:** Only 3 of 20 evaluated designs are feasible and 12 return no geometry. Every geometry failure has high bluntness_ratio combined with low cone_half_angle. Every valid geometry satisfies roughly (2*b - 0.1)*cos(theta) <= 0.86, and every failure is at or above 1.0. This is my own inference from the ids and the failure messages, not a stated rule. Feasible max_g is capped at 12 (C-1a25df448e6f sits at 11.99), and g rises with steeper flight_path_angle. Heat-shield mass fraction is roughly 1 - m ~ 0.09*D^2, so diameter must stay at or below about 3.2 m (C-c97855c2d790 at 4.27 m fails). The hypervolume is dominated by lowering bondline temperature, since the 300-450 K range is small. The current front point C-924ebfff660f is at 422 K and 363 kW/m2. Bluntness, diameter and flight-path angle are the levers still unexplored.

**evidence:**
- C-924ebfff660f (D=2.81, b=0.72, theta=69.6, gamma=-2.43) is the only front point: q=362.8k, T=422.0, g=10.1.
- C-954afbe3d7da (b=0.396, theta=66.3, gamma=-1.79) has T=443 and q=418k. It is dominated by C-924ebfff660f, which has larger bluntness and a steeper angle, so higher bluntness and steeper entry lower T.
- C-1a25df448e6f (gamma=-3.88, theta=36.4, D=2.39) sits at g=11.99, essentially on the g limit. Steeper angles (C-02335773e828 at -6.0 gives g=15.9, C-2d91d8d713d7 at -7.4 gives g=19.2) are clearly infeasible.
- Steep, big-D designs reach low T but violate g: C-c97855c2d790 gives T=375, C-2d91d8d713d7 gives T=381 and C-02335773e828 gives T=394. Bondline temperature falls with a larger b*D^3*sin(gamma) product.
- Geometry failures: C-1fdb98d93248 (b=1.32, theta=63.9), C-0c229251fec4 (b=1.26, theta=59.1), C-f97de340f655 (b=0.79, theta=47). Valid: C-c76d29c9a126 (b=0.515, theta=22.8) and C-924ebfff660f (b=0.72, theta=69.6). Large theta allows larger b.
- Mass-fraction margins: 0.30 at D=2.81, 0.23 at D=2.92, 0.037 at D=3.22 (C-2d91d8d713d7), -0.83 at D=4.27.

**mechanism:** This relies on prior Allen-Eggers-type scaling, calibrated to the data. Peak stagnation heat flux scales as sqrt(sin(gamma)/(Rn*CdA)), so it falls with larger nose radius and larger diameter. Heat load, and hence bondline temperature rise, scales roughly as (b*D^3*sin(gamma))^-0.5. A fit to eight evaluated points gives T-300 ~ 122*(X/1.218)^0.65, with X = (b*D^3*sin(gamma))^-0.5. Larger bluntness and diameter therefore lower both objectives at once, and a steeper angle lowers T at some cost in q and g. Peak g is set mainly by gamma and stays below 12 for |gamma| up to about 3.6-3.9 deg at large D. A high cone angle (about 70 deg) lets a very blunt nose (b about 1.1-1.3) stay geometrically valid, gives a low area-to-mass ratio, and keeps the shield mass fraction low. The plan is to push b up to about 1.1-1.3 at theta about 70, D up to about 3.0-3.2, and gamma to -3 to -3.8, while probing the g limit, the mass limit and the geometry boundary.

**uncertainty:** The geometry boundary is inferred from 20 samples. My fit of the nose-radius factor was inconsistent (about 1.8-1.95 times b*D/2), so designs with b >= 1.25 at theta=70 could still be invalid. The g model is extrapolated for large D and high theta. The T and q predictions come from a power-law fit to 8 points and may be off by 10-20%. The mass-fraction margin near D=3.2-3.3 depends on shield area, which I estimate only roughly.

## ai_agent seed_59 call_02  (20 proposals, 0 ask fidelity 1)

**observation:** Feasible front has only 2 points (C-a129e2c3933f, C-bbf9cdb0a525), both at the corner D~3.1-3.3, bluntness 1.2, cone 69.9. Reference spans (2.5e6 W/m2, 150 K of bondline temperature), so a 1 K drop in T is worth about 5x more hypervolume than the flux changes reachable here. Improvement must come from lowering bondline T while keeping max_g < 12 (limit inferred from margins) and mass margin >= 0. 14 of 40 evaluations returned no geometry. Failures cluster at bluntness >= 1.25 with cone <= 69.9, and at low cone angles for their bluntness.

**evidence:**
- max_g limit is 12: C-a129e2c3933f g=11.055, margin 0.0787. At D~3.0-3.3, g rises about 1.5-1.7 per deg of |gamma|: C-1e7b6fd1901c gamma -3.6 g=11.886 (margin 0.009), C-602600f85327 gamma -4.2 g=13.0 (infeasible). g depends only weakly on D (about +0.35 per m).
- Bondline T falls with steeper gamma at fixed geometry, about 8-12 K/deg: C-602600f85327 (D3.2, gamma -4.2) 388.6 K vs C-a129e2c3933f (D3.3, gamma -3.0) 398.6 K. Shallow gamma is worse: C-eae9b8e0689a gamma -2.2 is 418 K.
- Larger bluntness and cone lower T and flux at fixed D and gamma: C-8fd56d301a14 (b0.6, cone 45) 413.5 K/411k; C-b5d3475ab118 (b0.9, cone 62) 407.4 K; C-c12000ea6fcb (b1.0, cone 66.3) 406.4 K; C-5bc1f1f05670 (b1.1, cone 69.9, gamma -3.2) 403.1 K.
- Mass-fraction margin depends on D and slightly on b/cone, not on gamma: D3.1 0.161 (C-bbf9cdb0a525), D3.2 0.106 (C-602600f85327), D3.3 0.0497 (C-a129e2c3933f), about -0.055 per 0.1 m. It hits zero near D~3.39. C-c97855c2d790 (D4.27) is -0.83.
- Bluntness 1.25 (C-a554636d8035) fails the cd_fore convex-hull check. Bluntness 1.3 (C-ed967979f72a) gives an invalid geometry. Bluntness 1.2 at cone 69.9 is valid at D3.1-3.3 (C-a129e2c3933f, C-bbf9cdb0a525, C-602600f85327), and geometry validity looks independent of D since all lengths scale with D.

**mechanism:** This relies partly on prior Allen-Eggers-type scaling, calibrated to the data above. Stagnation flux scales about as sqrt(sin(gamma)/(Rn*CdA)), so larger D and bluntness lower flux, and shallower gamma lowers flux too. Bondline T follows the integrated heat load, which falls with larger nose radius, larger area (lower ballistic coefficient) and steeper gamma (shorter pulse). Steeper gamma costs peak deceleration g, capped at 12. D is capped by the heatshield mass fraction near 3.38. So the T-optimal region is max b/cone, D~3.3-3.38, and gamma near the g=12 boundary (about -3.55 to -3.6). Shallower-gamma variants at the same geometry extend the front toward lower flux with higher T.

**uncertainty:** The g boundary is tight: predicted g at gamma -3.55 to -3.6 is 11.9-12.0, so some of these will probably be infeasible. The mass-fraction edge near D3.37-3.38 is extrapolated linearly. The sqrt(sin gamma) flux scaling is approximate, and the C-602600f85327 point suggests flux may be about 3-5% lower than the scaling predicts. T-vs-gamma slope is about 8 K/deg near -3.5 but 12+ K/deg at shallow angles. Whether bluntness 1.22 at cone 70.0 passes the hull check is unknown. Effects of cone 70.0 vs 69.9 are unknown.

## ai_agent seed_59 call_03  (20 proposals, 1 ask fidelity 1)

**observation:** All 9 feasible non-dominated designs sit on one ridge: bluntness 1.2, cone 69.9 deg, D 3.3-3.38 m, entry angle -2.2 to -3.58 deg. Hypervolume is dominated by the bondline temperature axis, because flux is only about 0.1 of the 2.5 MW/m2 reference range while T spans 392-408 K of a 150 K range. The binding limit is max_g <= 12, reached at about -3.58 deg, and the heatshield mass-fraction margin runs out near D of about 3.385 m. In the data, T falls with steeper angle (about -10 K/deg), falls with larger D (about -18 K/m) and falls slightly with higher bluntness. Flux rises with steeper angle (about +24 kW/m2 per deg) and falls with larger D (about -120 kW/m2 per m). The ridge is therefore best pushed to D = 3.38 (the largest D with a verified positive mass margin) across the whole angle range.

**evidence:**
- C-3dfb47a1c8a3: D 3.38 has mass margin 0.003 (D 3.35: 0.0207, D 3.37: 0.0089), so D 3.38 is the largest verified buildable diameter; the extrapolated zero crossing is near 3.385.
- C-d8198ec304c5: D 3.33, -3.58 deg gives g = 11.994 (margin 0.0005) and T = 391.96 K. Fitting the 3.3 m rows (C-158e05f9d36e, C-5dab03f5d001, C-2cf973a097ba) gives dg/d|gamma| of about 1.65 per deg and dg/dD of about +0.38 per m.
- C-f07c60fdbdae vs C-0c6e47855b5e vs C-944b08da02c1: lowering bluntness from 1.2 to 1.1 raises T by about 0.65 K and flux by about 5 kW/m2 and lowers the mass margin, so b = 1.2 is best.
- C-bcce2808c9b8 and C-a554636d8035 (b 1.22-1.25) fail the cd_fore convex hull, and C-ed967979f72a (b 1.3, cone 69.9) fails geometry, so b > 1.2 is not reachable.
- C-404e4e066a3e and C-b76a72930094: the shallow end (-2.2, -2.4 deg) gives 246-250 kW/m2 at 405-408 K. Extending to -1.5 deg has not been tried.
- C-02335773e828, C-2d91d8d713d7 and C-c97855c2d790: steeper angles (-6 to -7.4 deg) reach lower T but have g of 16-19, so they are infeasible and not competitive.

**mechanism:** This relies partly on prior Allen-Eggers-type reasoning, calibrated to local linear fits of the data. A larger D at fixed mass lowers the ballistic coefficient, so the vehicle decelerates higher in the atmosphere and its heat pulse is smaller. A larger nose radius (bluntness and D) lowers stagnation flux. A steeper angle shortens the heat pulse and lowers integrated load and bondline T, but raises peak g and flux. Peak g is set mainly by entry angle, with a weak D dependence, so the g <= 12 wall caps the steepness. Mass fraction depends on D, bluntness and cone angle but not on entry angle. The best achievable points therefore have D just under the mass limit, b = 1.2, cone near 70 deg, and entry angle chosen along the trade-off curve. I propose to shift the whole known front to D = 3.38 (about 0.5 K lower T and 3-4 kW/m2 lower flux at each angle), extend it shallow to -1.5 deg, and spend four slots probing bluntness and cone sensitivity.

**uncertainty:** The linear fits for g, T and flux were calibrated on D 3.2-3.38 and s = 2.2-3.6. Predictions at -1.5 to -2.1 deg extrapolate beyond the measured shallow end, and T there may be off by a few K. The g margin at -3.55 deg is only about 0.2%, and I am relying on the fitted slope. The four exploratory points (lower cone or bluntness) may fail geometry or the hull check, since the buildable cone/bluntness boundary is only known coarsely. I have not used the higher-fidelity simulator, so high-fidelity effects such as real-gas heating and ablation are not represented.

## ai_agent seed_59 call_04  (20 proposals, 0 ask fidelity 1)

**observation:** Every non-dominated point comes from one family: D=3.38, bluntness 1.2, cone 69.9, with only flight-path angle varying. Flux runs from 227.7k to 274.7k W/m2 and bondline temperature from 418 K down to 391.4 K. The front ends where max_g hits its limit of about 12 (margin 0.003 at gamma -3.55). Diameter is capped near 3.385 m by the heatshield mass fraction (margin 0.003 at 3.38, 0.0089 at 3.37, 0.106 at 3.2). Bluntness and cone are pinned by the aero surrogate hull and the geometry validity limit. Cone 69.0 with b 1.2, b 1.25 with cone 69.9, and b 1.22 with cone 70 all failed on extrapolation. Smaller-b, lower-cone points such as C-ba66a1b43adf and C-e96a6ca1ed89 have higher flux at the same gamma and are dominated. Steep-gamma points are all g-infeasible.

**evidence:**
- C-e4bcd37fa904: gamma -3.55, flux 274.7k, T 391.37, g margin 0.003, mass margin 0.003. This is the low-T corner of the front.
- C-2ca095c82fd6 (D 3.37) has slightly worse flux and T than the D 3.38 curve, so larger D is better and only the mass limit stops it.
- C-ba66a1b43adf and C-e96a6ca1ed89 at gamma -3.5 have flux 282k and 294k against 273.5k for b 1.2, so lower bluntness raises flux.
- C-2375647d7e43, C-a554636d8035 and C-bcce2808c9b8 failed on cd_fore extrapolation, so the safe (b, cone) region is narrow around (1.2, 69.9).
- C-602600f85327 (D 3.2, gamma -4.2) has g 13.0 and C-2d91d8d713d7 has g 19.2, so g is set mostly by gamma and any gamma steeper than about -3.6 is infeasible.

**mechanism:** This draws on data and on prior Allen-Eggers-type reasoning. Peak flux scales roughly as sqrt(sin(gamma)/(Rn*CdA)), so large D and large bluntness are best. Bondline T falls as the pulse shortens at steeper gamma. Peak g rises with gamma, which caps gamma near -3.57. The front is therefore a one-parameter curve in gamma. It is convex, so extra points between existing ones add a little hypervolume. The remaining gains are the last few hundredths of a degree of gamma, D just under the mass-fraction limit, and a small (b, cone) probe at the edge of the hull, where cone 70 or b 1.21 might lower flux.

**uncertainty:** I cannot see the hull of the cd_fore surrogate, so the cone 70 and b 1.21 probes may fail with an extrapolation error. Peak g at gamma -3.57 has only about 0.3% margin, so those points may fall just over the limit. Mass-fraction margin versus D is extrapolated linearly. Predicted values are linear interpolations along the gamma curve.

## ai_agent seed_59 call_05  (19 proposals, 2 ask fidelity 1)

**observation:** The feasible front is a one-parameter curve in flight_path_angle at the corner D≈3.38, bluntness 1.2, cone 70. Along it, peak flux runs 227.7k to 275.2k W/m2 and bondline T runs 418.0 K to 391.1 K. Three limits pin that corner. Peak g <= 12 caps gamma near -3.572. Heatshield mass fraction caps D near 3.385. The cd_fore surrogate hull caps bluntness at about 1.2 for cone about 70. Every other explored region is either dominated or infeasible on max_g or mass fraction. Little hypervolume is left to gain, so I fill the remaining gaps on the curve with a slightly larger D and probe the edges.

**evidence:**
- C-d67ebd910866 to C-fe69bc352dbe: the D=3.38, b=1.2, cone 69.9-70 family, gamma -1.5 to -3.57, is the whole front. T falls monotonically and flux rises with steeper gamma.
- C-fe69bc352dbe versus C-32c1a76f8425: D 3.380 to 3.383 lowers flux 275180 to 274820 and T 391.18 to 391.12. g rises about 0.002. The mass margin falls 0.003055 to 0.001284, about -0.59 per metre of D, so D is capped near 3.385.
- C-41b2ddb7397c, C-43b18404f13e, C-6cbef4d15c79: lowering b from 1.2 to 1.1 raises flux 273.5k to 278.2k and cuts the mass margin to 0.00015. Bluntness 1.2 is best.
- C-3d41ce848a30, C-dcc9bfd9f503, C-2375647d7e43, C-bcce2808c9b8, C-a554636d8035: b=1.21 at cone 70 or 69.9, and b=1.2 at cone 69.0, fail the cd_fore hull. The usable corner is roughly b<=1.2, cone>=69.5.
- C-602600f85327: D=3.2, gamma -4.2 gives g 13.0, so g is driven mainly by gamma with only a weak D effect. C-02335773, C-2d91d8d713d7, C-c97855c2d790 show steeper gamma is infeasible on g.

**mechanism:** This relies partly on prior Allen-Eggers-type reasoning, calibrated to the data. Peak g in a ballistic-type entry is set mainly by gamma and hardly by geometry, so gamma is capped near -3.57. Flux falls with nose radius and area (about D^-1.4 here, from the C-fe69bc352dbe/C-32c1a76f8425 pair), and bondline T falls with heat load, which is lower for larger D and steeper gamma. The mass-fraction constraint stops D growing past about 3.385, and the hull stops b growing past about 1.2. The best design therefore stays at the corner and moves along gamma. Raising D to 3.384-3.385 gives about -0.17 to -0.2% flux and -0.07 K everywhere, a small gain. The remaining slots sample gamma gaps and probe hull edges.

**uncertainty:** The gains available are small, about 1e-4 to 1e-3 of normalised hypervolume. The mass margin at D=3.384-3.385 is only about 0.0001-0.0008, and the g margin at gamma about -3.57 is about 1e-4, so feasibility is marginal. I extrapolate the D dependence of g and mass margin linearly from two or three close points. The hull probes at b=1.205 and cone 69.6 could return a no-geometry failure. Predicted flux and T are interpolations of the front, with an assumed -0.17% flux and -0.07 K shift for D=3.384.

## ai_agent seed_59 call_06  (21 proposals, 2 ask fidelity 1)

**observation:** The front is a one-parameter curve in flight-path angle at D≈3.384 m, bluntness 1.2, cone 70°. It runs from (227k W/m2, 417.9 K) at gamma -1.5 to (274.6k, 391.1 K) at gamma -3.57. Three limits pin it in place. Peak g reaches its 12 g cap at about gamma -3.57. Heatshield mass margin falls to about 0 at D≈3.385 m. Bluntness above 1.2 (and cone below about 69.6 at b=1.2) gives 'aero surface extrapolation' or invalid geometry, so the buildable region ends near b=1.2, cone 70. Little hypervolume is left, so I mostly fill small gaps in the gamma sweep at the largest allowed D (3.385) and add a few cheap probes of bluntness and cone in the valid region.

**evidence:**
- C-92f6aed905e3 to C-636b6aeca4e0: at D=3.384, b=1.2, cone=70, flux rises 227k to 275k W/m2 while bondline T falls 417.9 to 391.1 K as gamma goes -1.5 to -3.57. The curve is convex and smooth.
- C-636b6aeca4e0 (max_g margin 8e-5) and C-112b974177e0 (max_g margin -6.5e-5 at gamma -3.572, D 3.38): gamma is capped near -3.57.
- C-81e40e27ff03 (D 3.385, mass margin 1.4e-4), C-636b6aeca4e0 (D 3.384, 7.4e-4) and C-112b974177e0 (D 3.38, 3.1e-3): mass-fraction margin drops about 0.6 per metre of D, so D is capped near 3.385 m.
- C-166a3a760ccb, C-3d41ce848a30, C-bcce2808c9b8, C-a554636d8035 (b 1.205 to 1.25) and C-2375647d7e43 (cone 69.0) all fail on surrogate extrapolation. C-ed967979f72a (b 1.3) fails on invalid geometry. Bluntness cannot rise above 1.2 at cone 70.
- C-ebb96199c3d5 (b 1.1, cone 68.5, D 3.35): flux 282k at gamma -3.5, higher than the b=1.2 curve (about 273k). C-d94e2f4145b9 (cone 69.6): flux and T lie on the same front.
- Designs at steeper gamma or small D (C-c76d29c9a126, C-02335773e828, C-2d91d8d713d7) are infeasible on max_g and have much higher flux, so they cannot improve the front.

**mechanism:** This relies partly on prior Allen-Eggers-type reasoning, calibrated to the data. Peak g in a ballistic entry is set mainly by gamma, which caps gamma near -3.57. Flux falls with nose radius and area (roughly D^-1.4 here) and has a weaker dependence on bluntness. Bondline T falls with a shorter heat pulse at steeper gamma. The mass-fraction limit caps D near 3.385 m, and the surrogate's valid range caps bluntness at about 1.2 when cone is 70. The front is therefore one-dimensional in gamma, and proposals are interpolations at D=3.385 (which lowers flux and T by about 0.03% versus 3.384) plus small probes of cone and bluntness.

**uncertainty:** Interpolated values should be accurate to about 0.3%. The b=1.15 and b=1.1 probes carry hull-extrapolation and mass-margin risk (lower b appears to reduce mass margin). D=3.3851 sits within about 1e-4 of the mass-fraction limit, so rounding could make it infeasible. The dependence of g on D and geometry is estimated from very few points.

## ai_agent seed_59 call_07  (20 proposals, 0 ask fidelity 1)

**observation:** The feasible front is essentially a one-parameter curve in flight_path_angle at D=3.385 m, bluntness=1.2, cone=70 deg. It runs from gamma=-1.5 (227k W/m2, 417.9 K) to gamma=-3.57 (274.6k W/m2, 391.1 K), where max_g reaches its 12 g limit. The other design variables are pinned by constraints. Mass-fraction margin at D=3.385 is only 1.4e-4. Bluntness above 1.2 or cone below 70 (except about 69.8-69.9) hits the aero-surrogate hull failures. Hypervolume has plateaued at 0.3555 over the last three rounds. The remaining gain is from filling gaps along the front, so I place all 20 points at gamma values not yet evaluated, on the safe D/b/cone.

**evidence:**
- C-948029610632 (gamma -1.5), C-bbe53564e0b7 (-1.95) and C-f32ce283f0ee (-2.2) show flux rising and bondline T falling smoothly with steeper gamma. The gap between -1.5 and -1.95 is the widest in the front.
- C-81e40e27ff03 (-3.57, g=11.999) and C-112b974177e0 (-3.572, g=12.001, infeasible) locate the g cap. C-0265d5374015 (-3.5695) is already feasible at the boundary.
- C-3b86cbfeed06 and C-7799f09f0eed (b=1.15, 1.10) give slightly higher flux and lower mass margin than b=1.2, so lowering bluntness does not help.
- C-2375647d7e43, C-3d41ce848a30, C-dcc9bfd9f503, C-166a3a760ccb, C-bcce2808c9b8 and C-a554636d8035 fail on surrogate extrapolation. Moving D, b or cone off the current corner risks wasting slots.
- C-602600f85327 (D=3.2, mass margin 0.106) versus C-948029610632 (D=3.385, margin 1.4e-4) shows mass fraction is very sensitive to D. D cannot be raised, and gamma does not change the mass margin.

**mechanism:** This is partly from the data and partly from prior Allen-Eggers-type reasoning. Peak flux rises with sqrt(sin(gamma)) and the heat pulse shortens at steeper gamma, so bondline T falls. Peak g is set mainly by gamma. With D, b and cone at their constraint-limited corner, gamma is the only free trade-off parameter. The front is a smooth convex monotone curve, so interpolating between neighbouring evaluated points gives accurate predictions. Since gamma does not affect mass fraction and the geometry is unchanged, these points should be feasible and not hit geometry or hull failures. The gain is small but positive.

**uncertainty:** The expected hypervolume gain per point is small, since the front is already densely sampled. Interpolation errors should be about 0.2-0.5% in flux and under 0.3 K in T. The near-limit points at -3.54 and -3.565 depend on max_g, which reads 11.98-11.999 near the cap. I have not explored other regions such as smaller D or lower cone angle, because they are dominated or fall outside the surrogate hull based on the data shown.

## ai_agent seed_59 call_08  (21 proposals, 0 ask fidelity 1)

**observation:** The front is a one-parameter curve in flight-path angle at the corner D=3.385, b=1.2, cone=70. D is capped by heatshield mass fraction (margin 1.4e-4), b and cone are capped by the aero-surrogate hull and the geometry limit, and gamma is capped near -3.57 by max_g. The only trade-off found beyond gamma is cone slightly below 70: C-8e1547b9ec46 (cone 69.8) is non-dominated. Round 7 added only 1.8e-5 of hypervolume, so the remaining gain is small refinement.

**evidence:**
- C-81e40e27ff03 (gamma -3.57) has max_g margin 4.7e-5, and C-112b974177e0 (gamma -3.572, D 3.38) violates max_g. Gamma is therefore capped near -3.5703.
- C-8e1547b9ec46 (cone 69.8, D 3.384, gamma -3.5) gives 273030 W/m2 and 391.79 K. Interpolating the cone-70 curve at -3.5 gives about 272890 and 391.91, so lower cone trades slightly more flux for slightly lower T.
- C-7799f09f0eed (b 1.1) is worse in both objectives than the b 1.2 curve, and hull failures at b 1.205-1.25 or cone 69.0 (C-166a3a760ccb, C-2375647d7e43) show b 1.2 and cone near 70 are the boundary.
- Mass margin: D 3.384 gives 7.4e-4 and D 3.385 gives 1.4e-4 (C-385f3798bd45, C-81e40e27ff03). The margin falls about 4e-4 per degree of cone reduction (from C-8e1547b9ec46), so cone below 69.8 needs D of about 3.384.
- g is nearly independent of geometry: 13.0 at gamma -4.2 (C-602600f85327) and 11.88 at -3.5 (C-8e1547b9ec46) give a slope of about 1.6 g/deg. There is no way to get lower T through steeper gamma.

**mechanism:** This relies partly on prior Allen-Eggers-type scaling and partly on the data. Flux falls with nose radius and area, and T falls with a shorter heat pulse at steeper gamma. D, b and cone are pinned at their constraint corner, and gamma is pinned by g. The remaining freedoms are gamma along the curve and small cone reductions, which add a little drag-area and mass-margin trade. The cone-69.8 offset (about +0.05% flux, -0.12 K) gives non-dominated points spaced along the gamma range. Gamma gap-fillers at cone 70 raise coverage of the convex front. Cone probes at 69.2-69.7 test where the hull edge lies.

**uncertainty:** The hull edge in cone at b=1.2 is unknown, since cone 69.0 failed and 69.8 passed, so the cone 69.2-69.7 probes may fail. The cone offset effect at other gammas is inferred from one point. Predictions for gap-fillers are linear interpolation. Feasibility at gamma -3.5703 is marginal.

## ai_agent seed_59 call_09  (25 proposals, 0 ask fidelity 1)

**observation:** The feasible front is effectively a one-parameter curve in flight_path_angle at D=3.385, bluntness=1.2, cone=70. Flux rises from 227k W/m2 at -1.5 deg to 274.6k at -3.5703 deg, and bondline T falls from 417.9 K to 391.1 K. Diameter is capped by heatshield_mass_fraction (margin about 1.4e-4). Gamma is capped by max_g at about -3.5703 deg. Bluntness above 1.2, or cone or D below the corner, hits the cd_fore convex-hull refusal or a geometry failure. Hypervolume gains have fallen to about 1e-5 per round, so the last 25 evaluations fill gaps in the curve and probe the tiny remaining D and b headroom.

**evidence:**
- C-948029610632 to C-8efe13d24286: at D=3.385, b=1.2, cone=70, gamma from -1.5 to -3.5703 gives flux 227k to 275k W/m2 and T 417.9 to 391.1 K, with max_g reaching 12.0 at -3.5703.
- C-8efe13d24286 has max_g margin 3.2e-5, and C-112b974177e0 (D=3.38, gamma -3.572) violates max_g. Gamma is therefore pinned near -3.570.
- C-948029610632 has mass margin 1.449e-4 and C-013d6de46fd0 (D=3.384) has 7.356e-4. That slope puts the mass limit near D=3.38525, so D=3.3851 to 3.3852 should stay feasible.
- C-a554636d8035, C-bcce2808c9b8, C-2375647d7e43, C-3d41ce848a30, C-dcc9bfd9f503 and C-166a3a760ccb all fail on cd_fore extrapolation. b>1.2 or cone<70 combined with D away from 3.385 is unsafe, so I keep the corner values.
- Gamma gaps on the curve with no evaluated point at D=3.385 and cone=70: -1.5 to -1.7, -1.95 to -2.35, -2.35 to -2.7, -2.7 to -3.05 and -3.1 to -3.4 (C-13574164271b, C-2f9f349729bd, C-af77f965ad8e).

**mechanism:** This relies partly on prior Allen-Eggers-type reasoning and partly on the data. At the mass-limited corner (D, b, cone), flux and bondline T depend mainly on gamma. Steeper entry raises peak flux through sqrt(sin gamma) and shortens the heat pulse, which lowers the integrated load and bondline T. The g limit caps steepness. Local linear interpolation of the neighbouring evaluated points gives the predicted flux and T. Since D, b and cone are pinned by constraints, the only remaining upside is interpolation in gamma and a tiny D increase (about +0.0002 m).

**uncertainty:** The main uncertainty is whether D=3.3851 to 3.3852 or b=1.201 triggers the cd_fore hull refusal or violates the mass fraction. The gain from either is negligible. Predictions from interpolation should be accurate to about 0.1 percent in flux and 0.1 K in T. Max_g near -3.57 deg is marginal.

## ai_agent seed_59 call_10  (11 proposals, 0 ask fidelity 1)

**observation:** The front is a one-parameter curve in flight_path_angle_deg at the corner D≈3.385 m, bluntness 1.2, cone 70°. Peak g caps gamma near -3.5703, and the heatshield mass fraction caps D at about 3.3852 m (margin 2.7e-5). The bluntness and cone perturbations near the corner all failed: 'cd_fore' surrogate extrapolation, or overlapping nose sphere and shoulder torus. With 11 evaluations left, the only safe hypervolume gain is to fill gaps along the gamma curve at the D=3.3852 corner, since the rest of the front is already dense.

**evidence:**
- C-6daecae7b30e (-1.5°): flux 227200 W/m2, T 417.87 K. C-c2d1addc0c7e (-1.75°): 232230 W/m2, 413.81 K. The gap between them is the largest on the front and has no evaluated points at D=3.3852.
- C-7fa59b50781c (-2.0°): 237570 W/m2, 409.98 K. C-60b626663373 (-2.5°): 248980 W/m2, 403.04 K. The interval from -2.0 to -2.5 is sparsely sampled at D=3.3852.
- C-8efe13d24286 (-3.5703°, D=3.385) has max_g 12.0000, margin 3.2e-5. C-96e48a93fd32 (-3.5695°, D=3.3852) has margin 1.2e-4. C-112b974177e0 (-3.572°) is infeasible on max_g, so gamma is capped near -3.5703.
- C-4e45b26ae0a9, C-166a3a760ccb, C-3d41ce848a30, C-dcc9bfd9f503, C-bcce2808c9b8 and C-2375647d7e43 all failed on cd_fore extrapolation. C-ed967979f72a failed on geometry. No bluntness or cone change should be attempted.
- D=3.3852 shows a mass-fraction margin of 2.677e-5 against 1.449e-4 at D=3.385, and flux and T are marginally better at the larger D. Every proposal therefore keeps D=3.3852, inherited from the parent.

**mechanism:** This relies on the data and on prior Allen-Eggers-type reasoning. Peak flux scales roughly as sqrt(sin(gamma)) and rises with steeper entry. The heat pulse shortens with steeper entry, so bondline T falls. Peak g rises with gamma and sets the steep limit. Locally, flux and T are smooth and nearly linear in gamma. The proposals interpolate between evaluated neighbours at D=3.3852 (slopes about +20 to +24 kW/m2 per degree in flux and -12 to -16 K per degree in T). This adds coverage of the trade-off curve without any surrogate-hull or geometry risk.

**uncertainty:** Interpolated flux and T should be accurate to well under 0.3% because the curve is smooth. The main risk is the two points nearest the g limit (-3.565°, -3.57°), where max_g margin is around 1e-4. This is a reduced-order model and I have not seen behaviour beyond the evaluated range. Expected hypervolume gain is very small (about 1e-5).

## ai_agent seed_67 call_01  (20 proposals, 2 ask fidelity 1)

**observation:** No feasible design exists yet: 11 of 20 evaluations were geometry failures, and the rest fail max_g (limit 12 g), heatshield mass fraction, or both. All 11 geometry failures fit one rule: fore-cone length = D*(0.5 - 0.1*(1-cos(theta)) - b*cos(theta))/tan(theta), which must be >= 0. This reproduces the reported lengths for C-d03a6d571826, C-e0d635fd334b and C-c28d2aecc04e, so high bluntness needs a high cone angle. The feasible window looks like: flight-path angle no steeper than about -3.3 deg (g <= 12), diameter no larger than about 3.0 m (mass fraction), and a high cone angle with the largest bluntness the geometry allows. The hypervolume reference is 450 K in temperature, so bondline temperature dominates the hypervolume: one Kelvin is worth far more than tens of kW/m2 of heat flux. The proposals therefore cluster near the g and mass limits, with a few shallower or smaller probes for trade-off coverage.

**evidence:**
- C-e0059024652c: gamma -2.69 gives g 10.56 (margin 0.1201, so the g limit is 12). C-316c5e108e1a: gamma -3.40 gives g 11.97 (margin 0.002). Steeper entries fail g: C-9b459669aa7c gives 12.9 at -3.52 and C-029296252ff3 gives 13.6 at -4.41.
- Mass-fraction margin falls with diameter: C-a6b969cef0a0 at D 3.07 gives +0.008, C-e0059024652c at 3.39 gives -0.128, C-029296252ff3 at 3.63 gives -0.19, C-316c5e108e1a at 4.30 gives -0.83. Small diameters pass easily, for example 0.83 at D 1.24 in C-9b459669aa7c. The diameter ceiling is therefore about 3.0 m.
- Peak heat flux q roughly follows q^2 = K*sin(gamma)/(b*D^3), with K about 5e13 at theta 42-49 and about 3.2-3.6e13 at theta 55-65, fitted across the 9 valid rows. Higher cone angle, larger D and larger bluntness therefore all lower q and the heat load.
- Bondline temperature rises with heat-load proxy Q = q/sin(gamma), roughly dT = 76 + 3.9*Q[MW/m2]. Examples: C-316c5e108e1a has Q 4.8 and T 393; C-9b459669aa7c has Q 28 and T 484. Shallow entry adds a few K (C-e0059024652c is about +9 K above trend at -2.69 deg).
- Geometry-failure rows C-c28d2aecc04e, C-69ef29176b15 and C-5a78f6504d22 all combine bluntness above 0.96 with theta at or below 53 deg. Valid rows with b*cos(theta) below about 0.48 all built.

**mechanism:** Peak heating scales roughly with sqrt(rho/Rn)*V^3 (Sutton-Graves, prior knowledge). It falls with larger nose radius (Rn = b*D) and with lower ballistic coefficient (larger D and higher-drag blunt, high-angle cones). Bondline temperature follows integrated heat load, which falls with the same levers and rises as the entry gets shallower and the heating pulse lengthens. Peak deceleration is set mainly by entry angle, plus a small bump for small, high-ballistic-coefficient bodies. The best region is therefore large D within the mass limit, theta 62-70 deg, b near the geometry ceiling b <= (0.4 - margin)/cos(theta) + 0.1, and gamma near -3.1 to -3.3 deg. Shallower gamma trades higher T for lower q.

**uncertainty:** Diameter and gamma are extrapolated: the mass-fraction dependence on theta and b is unmeasured, and the 3.0 m ceiling comes from only three rows. g for large-D, high-drag blunt shapes at gamma -3.2 to -3.4 sits within about 0.4 g of the limit, so several proposals may fail g. K(theta) and the T-vs-Q fit come from 9 points with confounded variables. Predicted temperatures below 393 K are extrapolation. The 0.02-0.09 geometry margins are computed from the fitted rule and should be safe, but a minimum cone length may exist that the data does not show.

## ai_agent seed_67 call_02  (19 proposals, 0 ask fidelity 1)

**observation:** Hypervolume is dominated by bondline temperature. The reference is 450 K, so a 1 K reduction is worth about 4x more area than a 10 kW/m2 heat-flux reduction. The feasible front sits at D=3.0-3.05 m, b=0.95-1.1, cone 68-70 deg, FPA -2.0 to -3.25 deg. From the margins, the limits are max_g = 12.0 and bondline = 450 K. Constraint behaviour: (1) Peak g is set almost only by FPA, about 9.63 at -2.0, 11.56 at -3.4, roughly 1.5 g/deg, so g reaches 12 near -3.7 deg. (2) Heatshield mass-fraction usage scales as D^2: margin is 0.21 at D=3.0, 0.41 at 2.6, 0.186 at 3.05, so it hits zero near D~3.37 at high cone angle. (3) Geometry failures match cos(cone) <= 0.4/(b-0.1), with Rn=b*D and shoulder radius 0.1*D. This reproduces the failing lengths for C-c28d2aecc04e and C-d03a6d571826. Larger D lowers both heat flux (roughly D^-1.4) and bondline temperature (about -20 K/m). Higher b and cone help slightly. The best unexplored region is D~3.2-3.37, b~1.17-1.25, cone 70, FPA -3.4 to -3.65. It pushes toward the g and mass limits, with a few shallower-FPA points to spread the front.

**evidence:**
- C-f5cd2c404e61 (D2.6,b1.1,c70,-3.3): T 411.3, HF 399.7k. C-2a1f2582e86f (D3.05, same b/c, -3.25): T 401.5, HF 315.8k. Larger D lowers both objectives at the same FPA.
- C-a21c8a3f8776 (-2.0): g 9.63, T 420.6. C-764eef2a20fc (-3.4): g 11.56, T 401.6, g margin 0.036. Steeper FPA lowers T at about 10-14 K/deg and raises g at about 1.5 g/deg, so g=12 is reached near -3.7 deg.
- C-0fb9b23734ce (D3.0,b1.17,c70,-3.15): HF 316.6k, T 403.2, mass margin 0.214. Compared with the b=1.0 rows, higher b is slightly better on both objectives and geometry is valid.
- Mass margin vs D: 0.408 at 2.6 (C-f5cd2c404e61), 0.208 at 3.0 (C-a21c8a3f8776), 0.186 at 3.05 (C-2a1f2582e86f). This fits usage proportional to D^2 and gives zero margin near D~3.37. C-e0059024652c (D3.39) and C-029296252ff3 (D3.63) violate mass fraction.
- Geometry failures C-d03a6d571826 (b1.34, cone 69.6) and C-c28d2aecc04e (b0.965, cone 46) match the rule cos(cone) <= 0.4/(b-0.1), with negative fore-cone length = deficit/tan(cone). So b<=1.25 at cone 70 is valid.

**mechanism:** Heating follows a Sutton-Graves law (from prior knowledge) that falls with nose radius (b*D) and with ballistic coefficient. A larger, blunter, high-drag capsule decelerates higher in the atmosphere and has a lower heat load, so bondline temperature falls. A steeper entry shortens the heating pulse and lowers bondline temperature, at the cost of higher peak g and heat flux. Mass fraction limits D, and g limits how steep the entry can be. The optimum for temperature should sit on both limits: D~3.3 m, cone 70 deg, b~1.2, FPA~-3.5 to -3.6. Shallow-FPA designs at the same D give lower heat flux and higher T, which fills the left side of the front.

**uncertainty:** The D and FPA trends are extrapolated beyond the explored range (D up to 3.37 vs 3.05 measured, FPA -3.65 vs -3.4). The mass-fraction margin near D 3.37 and the g margin near FPA -3.65 are thin, so several proposals may come out infeasible. The b=1.25 point sits close to the geometry boundary (rule derived from the failure messages). The bondline-temperature dependence on D is probably diminishing, so my T predictions may be a few K optimistic.

## ai_agent seed_67 call_03  (20 proposals, 0 ask fidelity 1)

**observation:** Peak g is set almost entirely by flight-path angle and binds at a limit of 12 g. At D=3.3, b=1.17 and cone 70, g is 11.85 at -3.5 deg and 12.01 at -3.6 deg. Changing bluntness, cone angle or D by small amounts moves g by less than 0.05. Every point on the feasible front sits at the corner of the bounds: cone 70 (max), bluntness about 1.17, D about 3.3-3.37. That corner is capped by the heatshield mass fraction, whose margin falls about 0.58 per metre of D and does not depend on gamma. Larger D and slightly higher b lower both heat flux and bondline temperature. Bluntness 1.22 and 1.25 at cone 70 fail on aero surrogate extrapolation, while 1.20 works. The remaining headroom is D up to about 3.38 with b=1.2, cone 70, swept along the gamma trade-off from about -1.5 to -3.55 deg.

**evidence:**
- C-d3a7fa99fcee (D3.3) vs C-d706f33c18bc (D3.35), both b1.17 at -3.5 deg: heat flux 284.5k -> 278.4k, bondline 393.5 -> 392.6 K. Larger D helps both objectives.
- C-70f28f0eabf2 (D3.1), C-cde6c1e46d6d (D3.2), C-c050b796618a (D3.3) at -3.6 deg: heat 314k / 300k / 287k, bondline 396.2 / 394.3 / 392.5 K. Larger D is better on both axes.
- Mass margin vs D at b1.17: 0.0489 at 3.3, 0.0199 at 3.35, 0.0081 at 3.37 (C-a8aec30c684b). The extrapolated zero is about D=3.384. b1.2 gives a slightly higher margin (0.0497 at 3.3, C-cbb67c388863).
- C-cbb67c388863 (b1.2, -3.55) beats the interpolated b1.17 series at the same gamma: 284.4k / 392.8 K vs about 285.8k / 393.0 K.
- Same-D gamma sweep at D3.3/b1.17: C-5644bff69a09 (-1.6) 239k / 418 K to C-d3a7fa99fcee (-3.5) 284.5k / 393.5 K. g reaches 12.0 at about -3.59 deg (C-c050b796618a, margin -0.001).
- C-425c523a5086, C-5b57439845df and C-e605b64e0636 (b1.22-1.25, cone 70) are rejected for extrapolation. The b limit at cone 70 lies between 1.20 and 1.22.

**mechanism:** This relies on the data plus prior Sutton-Graves reasoning. Peak heating falls as nose radius (b*D) grows, and the heat load falls as ballistic coefficient drops, so a larger D at high b and cone 70 helps both objectives. Steeper entry shortens the heating pulse and lowers bondline temperature, but raises peak heat flux and g, and g caps gamma near -3.57 deg. The geometry is therefore pushed to the mass-fraction edge (D about 3.38) and gamma is swept along the g limit. That shifts the whole front toward lower heat flux and lower temperature. A few probes test cone angle, b just above 1.2, and the mass edge.

**uncertainty:** The mass-fraction edge near D=3.384 is extrapolated linearly from three points. The D3.38 points near -3.55 deg have about 0.03 g of margin, and g may rise slightly with D. The cone-angle probes are not backed by data at high b, and mass or aero behaviour may differ. The b>1.2 probes may hit the surrogate hull and fail. Predicted heat-flux and temperature gains from D use an exponent fitted only on D 3.1-3.35.

## ai_agent seed_67 call_04  (21 proposals, 0 ask fidelity 1)

**observation:** The feasible front is one geometry (D≈3.38, b=1.2, cone=70) swept in flight-path angle. Heat flux runs from 227.7k W/m2 at gamma=-1.5 to 274.7k at -3.55, and bondline temperature falls from 418 K to 391.4 K. Three constraints pin this corner. The g limit (about 12) caps gamma near -3.57. The heatshield mass fraction caps D near 3.385. The surrogate hull blocks b>1.2 at cone 70, and cone<70 at b=1.2 gives invalid geometry. Steeper gamma is infeasible (g margins go negative from -3.6), and smaller D or other geometries are dominated. The remaining gains are small refinements of the corner and denser coverage of the front.

**evidence:**
- C-d67ebd910866 to C-27aed1c1ecfd: the front is monotone in gamma (HF 227.7k to 274.7k W/m2, T 418.0 K to 391.4 K) at D=3.38, b=1.2, cone=70.
- C-27aed1c1ecfd has g margin 0.003 at gamma=-3.55, and C-c050b796618a is infeasible on max_g at -3.6, so gamma must be no steeper than about -3.57.
- C-a201e4576c17 (D=3.384) has mass margin 0.00074, against 0.0031 for D=3.38 and 0.0149 for D=3.36. Extrapolating, the mass limit is at D≈3.385.
- C-a201e4576c17 vs C-d20e6439cf38 (same gamma -3.4): D=3.384 gives HF 270620 vs 271070 and T 392.78 vs 392.85. A slightly larger D marginally improves both objectives.
- C-3d41ce848a30, C-425c523a5086, C-5b57439845df and C-e605b64e0636 (b>1.2) fail on surrogate extrapolation. C-c708a99f10f1, C-17a9b770e63c and C-a55828a3ab03 (cone 62-67 at D=3.3) fail on geometry. The corner is boxed in.
- C-e0059024652c (cone 42, b 0.59), C-029296252ff3 and C-a6b969cef0a0 are dominated or violate mass or g. Moving away from the corner hurts.

**mechanism:** This relies on the data plus prior Sutton-Graves reasoning. Peak heating falls with nose radius (b*D) and with ballistic coefficient. Bondline temperature falls with heat load, which shrinks with larger D and steeper entry. Cone 70 and b=1.2 minimise heatshield area, so they allow the largest D under the mass limit. Peak g is set mainly by gamma. The front is therefore traced by gamma at the largest allowed D, and the best available moves are D=3.384 (marginally lower HF and T) and denser gamma sampling.

**uncertainty:** Gains from D=3.384 are tiny (about 0.15% HF, about 0.07 K) and the mass and g margins are razor thin, so a few points could be marginally infeasible. The two exploratory points (b=1.15, cone=69.5) risk geometry or hull failure and probably will not beat the front. Interpolated predictions could be off by roughly 0.5 K or 1k W/m2.

## ai_agent seed_67 call_05  (20 proposals, 0 ask fidelity 1)

**observation:** The front is a one-dimensional gamma sweep at a single geometry corner: D=3.384, b=1.2, cone=70. Peak heat flux runs 227k to 275k W/m2 and bondline temperature 418 K to 391 K. The steep end is capped by max_g at gamma of about -3.57 deg. D is capped by heatshield mass fraction (margin 0.00074 at D=3.384). b is capped at about 1.2 by the cd_fore surrogate hull, and cone is capped at 70 deg by the variable bound. No other region of the data comes close to the front. Small or blunt-poor designs have flux of 330k to 1.7M W/m2 and are dominated. I therefore spend this round on filling gamma gaps at a marginally larger D, and I rely on data-fitted local sensitivities rather than new physics.

**evidence:**
- C-92f6aed905e3 through C-f71f4a44911d: same D, b and cone with gamma from -1.5 to -3.565. Flux rises about 12k per deg and T falls about 10 K per deg. g reaches 11.991 at -3.565, a margin of 0.00078.
- Heatshield mass margin is 0.0007356 at D=3.384 (C-f71f4a44911d) and 0.003097 at D=3.38 (C-3976a1ed5e2c). That slope puts the D limit near 3.3852.
- C-fbfc374c65e1 (D=3.36, cone 69.5) gives 263720 W/m2 at gamma -3, against 260980 for the corner. This matches flux proportional to D^-1.5 with almost no cone effect. T is about 19 K per m of D, so a slightly larger D is a small gain in both objectives.
- C-ea8a7098ba1b (b=1.15, D=3.37) has higher flux and T and only a slightly larger mass margin. Lower b is therefore worse.
- C-425c523a5086, C-5b57439845df, C-e605b64e0636 and C-3d41ce848a30 (b of 1.21 to 1.25 at cone 70) fail the cd_fore hull. C-c708a99f10f1, C-17a9b770e63c and C-a55828a3ab03 (cone 62 to 67) fail on geometry. Neither corner can be pushed further.

**mechanism:** Peak flux follows a Sutton-Graves-like law (prior knowledge). It falls with nose radius b*D and rises with ballistic coefficient, giving roughly D^-1.5 in the data. Bondline temperature follows heat load, which falls with steeper entry and larger D. Larger D is limited by the mass fraction, larger b by the surrogate hull, and steeper gamma by max_g. The design is boxed in at D=3.3848, b=1.2, cone=70, so the only free direction is gamma. The D increase from 3.384 to 3.3845 or 3.3848 is a tiny but dominating improvement, kept inside the estimated mass-fraction limit.

**uncertainty:** The mass-fraction margin at D=3.3845 to 3.3848 is a linear extrapolation of about 0.0004 to 0.0003. It could be slightly nonlinear, so I keep D no higher than 3.3848. The gamma interpolations are accurate to about 0.3 K and 0.3%. The g margin near gamma -3.567 is thin, at about 0.0005 by extrapolation. I have no data on how the hull behaves at b above 1.2 with cone below 70, so I do not probe it here.

## ai_agent seed_67 call_06  (19 proposals, 0 ask fidelity 1)

**observation:** The feasible front is a one-dimensional curve at the corner D≈3.3845 m, b=1.2, cone=70 deg, traced by flight-path angle from -1.5 to -3.567 deg. Flux runs 227k to 275k W/m2 and bondline temperature 418 to 391 K. Three limits box this corner in: the mass-fraction margin is only 0.0003 to 0.0007, the max_g margin is 0.0005 at gamma=-3.567, and the aero-surface hull rejects b>=1.21 at cone 70. Hypervolume gains have stalled (0.35365, 0.35505, 0.35531 over rounds 3 to 5). Other regions are dominated: small D or low b gives higher flux and higher bondline temperature.

**evidence:**
- C-092723c51b5a: gamma=-3.567 gives g=11.994 (margin 0.0005) and mass margin 0.00026. D and gamma are both pinned at their limits.
- C-a565d31e5d1c to C-092723c51b5a: flux rises ~23k W/m2 per degree of steepening while bondline temperature falls ~9.7 K/deg. Any gamma between two front points lies on the non-dominated staircase.
- Mass margin vs D: 3.384 gives 7.4e-4, 3.3845 gives 4.4e-4, 3.3848 gives 2.6e-4. That is ~0.59 per m, consistent with mass ∝ D^2, so D can exceed 3.3848 by only ~4e-4 m.
- C-c050b796618a (D=3.3, b=1.17, cone 70): mass margin 0.049 and g=12.014 at gamma=-3.6, so b has little effect on area and g. Flux is 287k, worse than the D=3.38 curve.
- C-425c523a5086, C-5b57439845df, C-e605b64e0636, C-3d41ce848a30: b>=1.21 at cone 70 fails the cd_fore hull. The edge lies between b=1.2 and 1.21.
- C-c708a99f10f1, C-17a9b770e63c: cone<=67 at b=1.2 gives a negative fore-cone length, so cone 70 is both the limit and the optimum.

**mechanism:** This relies on the data plus prior Sutton-Graves reasoning. Flux falls with nose radius (bD) and with ballistic coefficient, and bondline temperature falls with heat load, so the best designs have the largest D that the mass fraction allows. A larger b and cone 70 give the flattest forebody with the least area per D^2. Steeper entry lowers bondline temperature at the cost of flux and g, so the corner is set by mass fraction, max_g and the hull. The remaining gains are small: (1) probing b just above 1.2, where a 0.4 to 1 percent larger nose radius trims flux by ~0.2 to 0.5 percent; (2) pushing gamma to the g limit; (3) filling gaps along the curve, since every interpolated gamma is non-dominated; (4) two cheap probes of whether lower b or smaller D lowers g enough to allow steeper gamma.

**uncertainty:** The hull edge for b at cone 70 is unknown, so b=1.202 to 1.208 may return an extrapolation failure. Mass margin at D=3.385 is ~1e-4, so it may flip to infeasible. Predicted g near the limit is uncertain by about 0.01 g. Interpolated flux and temperature values are linear and should be accurate to about 0.3 percent. The two exploration probes are expected to be dominated.

## ai_agent seed_67 call_07  (21 proposals, 0 ask fidelity 1)

**observation:** The front has converged onto one corner: D~3.385, b=1.2, cone=70, with flight-path angle (gamma) as the only free variable. Three walls box it in. The mass-fraction margin is about 0 at D~3.3852 (cone 70 is the flattest, lightest forebody). The cd_fore surrogate hull refuses b>1.2 at cone 70. Peak g reaches 12 at gamma~-3.570. Along the front, steeper gamma raises flux (227k to 275k W/m2) and lowers bondline T (418 to 391 K). The last three rounds added only about 0.0002 hypervolume each.

**evidence:**
- C-4d63379171a2 (gamma -3.57, g margin 5e-5, mass margin 2.6e-4) and C-1a745bbcb46d, C-092723c51b5a show the corner is boxed in by both the g and mass walls.
- C-507815483127, C-e6aafb4787d2, C-b31977b067c2, C-b59eb448d6ee and C-3d41ce848a30 show b>1.2 at cone 70 fails on the surrogate hull.
- C-c708a99f10f1, C-17a9b770e63c and C-a55828a3ab03 show cone<=67 at b>=1.2 is an invalid geometry (nose and shoulder overlap).
- C-71f892c85980 (D 3.2) and C-c050b796618a (D 3.3, b 1.17) are worse in T at the g wall, so smaller D is dominated. C-1d2c34a68964 (b 1.1) is slightly worse than b 1.2.
- Mass margin fits 1-k*D^2 at D=3.384/3.3845/3.3848/3.385, and reaches 0 near D=3.3852.

**mechanism:** Peak g is set mainly by gamma (about 1.67 g/deg), so gamma is capped near -3.570. Bondline T follows heat load, which falls with larger nose radius b*D and lower ballistic coefficient. Both are capped by the mass wall (D) and the hull wall (b). Flux falls roughly as D^-1.5, so the largest feasible D dominates. What is left is small: push D to the mass limit across the gamma sweep, and probe cone angles just under 70 and lower b to see whether the hull, geometry and mass walls leave any room. This relies on the data plus prior Sutton-Graves reasoning.

**uncertainty:** The mass margin near D=3.3852 is extrapolated linearly, so a few D-max proposals may fail on mass. Whether the hull admits cone<70 at b~1.2, and how much mass and area a lower cone adds, is untested. Effects of b and cone on T are only inferred from a few points. The predicted gain from the D-refinement points is very small.

## ai_agent seed_67 call_08  (19 proposals, 2 ask fidelity 1)

**observation:** The search has saturated at a corner of the design space. Every non-dominated point I can see is in one family: b=1.2, cone=70, D≈3.385, with only flight_path_angle_deg varying from -1.5 to -3.57. Three walls box it in: (1) max_g reaches 12 g at gamma≈-3.570; (2) heatshield_mass_fraction is linear in D at 0.59 per m and reaches zero at D≈3.385245; (3) the cd_fore surrogate hull blocks b>1.2 at cone 70 and cone<~69.5 at b=1.2. Smaller-D or lower-b designs are worse in both objectives.

**evidence:**
- C-96e48a93fd32 (D=3.3852, gamma=-3.5695): g margin 1.2e-4, mass margin 2.7e-5. C-166904f3a01f (D=3.3851, gamma=-3.57): g margin 4.4e-5, so the g limit is at gamma≈-3.5703.
- Mass margin vs D at b=1.2, cone=70: 3.384 gives 7.356e-4, 3.3845 gives 4.403e-4, 3.385 gives 1.449e-4, 3.3851 gives 8.585e-5, 3.3852 gives 2.677e-5. That is exactly linear, so the zero crossing is D≈3.385245.
- C-507815483127, C-e6aafb4787d2, C-b31977b067c2, C-b59eb448d6ee (b=1.202-1.208, cone=70) and C-d0f9b054a40c (cone=69, b=1.2) all failed on the surrogate hull.
- At gamma=-3.5, the b=1.0 (C-018291ba5cb8), b=0.9 (C-ea6fa32467e5) and D=3.36 (C-3eaa6889bf91) variants all have higher flux and bondline T than the D≈3.385, b=1.2, cone=70 point (C-4254ac4b3c28).
- T falls about 10 K/deg toward steeper gamma and flux rises about 1.6 kW per 0.1 deg. Adjacent front points such as C-bc0407b5b99a (-2.0) and C-6162f3ab3eef (-2.2) have visible staircase gaps.

**mechanism:** This relies on the data plus prior Sutton-Graves reasoning. Peak flux falls with nose radius (b*D) and ballistic coefficient. Bondline T follows heat load, which falls with steeper entry and larger D. Peak g is set almost entirely by gamma, at about 1.65 g/deg. The best D, b and cone sit at the mass and hull walls, so the only remaining move is along the gamma curve at D≈3.3852. Extra points on that curve fill staircase notches in the dominated region, and the corner point at the g limit adds a little extra. Expected gains are small, on the order of 1e-5 to 1e-4 of normalised hypervolume in total.

**uncertainty:** The mass-margin extrapolation to D=3.38523 is linear, so it is tight (predicted margin about 8e-6). I did not model the hull edge, so I kept b=1.2 and cone=70 exactly, since those values are known to pass. The g margin at gamma=-3.5702 is only about 1.6e-5, so that point could be marginally infeasible. Predicted flux and T come from linear interpolation between neighbouring front points and should be accurate to about 0.3 K and 0.3 kW/m2.

## ai_agent seed_67 call_09  (21 proposals, 0 ask fidelity 1)

**observation:** The front is a single one-parameter curve. Every non-dominated point sits at D~3.385, b=1.2, cone=70 and differs only in flight-path angle. Flux runs from 227k W/m2 at gamma=-1.5 to 274.5k at -3.5702, while bondline T falls from 417.9 K to 391.1 K. Each of the other three variables is pinned by a wall: D by the mass fraction (margin ~3e-5), b and cone by the surrogate hull (b=1.202 and cone 69 both fail), and gamma by max_g=12 (about 1.7 g/deg). Other geometries such as C-ea6fa32467e5 (b 0.9, cone 66) are dominated. Only 21 evaluations remain, so I fill the gaps in the gamma sweep at fixed geometry. This should trim the staircase area under the front with almost no risk of geometry failure.

**evidence:**
- C-b8e5f12114a1 (gamma -1.5) and C-a21e478c2d2d (gamma -3.5702, max_g margin 1.2e-5) are the two ends of the feasible front; all 12 listed non-dominated points share D=3.385, b=1.2, cone=70.
- Flux and T are smooth and nearly linear in gamma between neighbours, e.g. C-255298c956e9 (-2.58: 250860, 402.02) and C-74cfdfd96a8c (-2.78: 255600, 399.55). Linear interpolation should therefore be accurate.
- Hull and geometry failures at b=1.202-1.208 (C-507815483127 etc.), cone 69 (C-d0f9b054a40c) and cone 62-64 (C-17a9b770e63c) show that b, cone and D cannot be pushed further.
- C-ea6fa32467e5 (b 0.9, cone 66, gamma -3.5) gives 294k W/m2 and 394.6 K, dominated by C-8d69d1842e32 (272.9k, 391.76 K). Lower b or cone gives no gain.
- Peak g of 11.88 at -3.5 and 12.0 at -3.5702 (C-a21e478c2d2d) confirm gamma is capped near -3.5702.

**mechanism:** This relies on the data plus prior Sutton-Graves reasoning. Peak flux falls with nose radius b*D and with ballistic coefficient, so the largest D that meets the mass fraction, with maximal b and cone, is best. Steeper entry shortens the heating pulse, which lowers bondline T at the cost of higher peak flux and g. Peak g is nearly independent of D and depends on gamma. The trade-off is therefore traced only by gamma at the box corner, and the remaining gain is from denser sampling of that curve, especially the g-limited end.

**uncertainty:** The predictions are interpolations between measured neighbours. The main risks are the max_g margin at gamma about -3.565 to -3.5703, which is under 1e-4 g from the limit, and the mass margin, which is untouched because D is not changed. The hypervolume gain from these points is expected to be very small (~1e-4 or less).

## ai_agent seed_73 call_01  (20 proposals, 2 ask fidelity 1)

**observation:** Only 1 of 20 evaluated designs is feasible (C-ee454ee3df8f: 578.9 kW/m2, 432.1 K). 11 of 20 failed geometry. Constraint limits back-calculated from the margins: max_g 12, bondline temperature 450 K. Heatshield mass fraction grows steeply with diameter and is binding by about D 3.3 m. The geometry failures fit a single rule. Taking nose radius as roughly bluntness*D, the fore cone goes negative when bluntness*cos(cone_half_angle) is above about 0.5. Every valid row has B*cos(theta) <= 0.46 and every failed row has >= 0.53. Peak flux scales roughly as D^-1.65 * B^-0.5 * sqrt(sin|gamma|). Bondline temperature falls with lower flux and with steeper entry. max_g rises with steeper entry, about 10.8 g at -3.1 deg and 13.2 g at -4.1 deg, so gamma is capped near -3.6 deg.

**evidence:**
- Geometry-valid rows have B*cos(theta): ee454 0.41, 63010 0.18, fae3 0.22, f84c 0.37, b545 0.35, 4cf8 0.23, 0942 0.31, 23d5 0.46, 9465 0.33. Failed rows: ad22 0.53, 7e34 0.56, 2e54 0.56, 3348 0.52, 2ffd 0.60, b4b6 0.60, 9f9d 0.70, 709f 0.86, 6cb2 0.92, 8a28 1.09, e079 1.08. The threshold sits between 0.46 and 0.52.
- Flux scaling: 63010 (B 0.315, D 2.08) has 900 kW/m2 against 579 kW/m2 for ee454 (B 0.674, D 2.23) at nearly the same gamma, which fits flux ~ 1/sqrt(nose radius). Larger D gives much lower flux: f84c (D 3.34) 349 kW/m2 at -5.5 deg, 4cf8 (D 4.05) 302 kW/m2 at -4.1 deg.
- g limit: ee454 10.8 g at -3.12 deg, 63010 10.96 g at -3.18 deg, 4cf8 13.16 g at -4.07 deg, fae3 9.24 g at -1.75 deg. About 2.5 g per degree puts the 12 g limit near -3.6 deg.
- Bondline temperature: fae3 at -1.75 deg is 470.7 K (infeasible) while 4cf8 at -4.07 deg is 387 K. Shallow entry means a long heat pulse and a hot bondline.
- Mass fraction margin: 4cf8 (D 4.05) -0.52, 23d5 (D 4.2) -0.98, 9465 (D 4.49) -0.77, f84c (D 3.34) +0.010, b545 (D 3.19) +0.007. Keep D at or below about 3.2-3.3.
- Current hypervolume is 0.092. That equals the feasible point's (1-579/2500)*(1-132/150). The bondline-temperature axis has a lot of headroom to gain.

**mechanism:** Stagnation heating falls with nose radius (~Rn^-0.5). Nose radius here is roughly B*D, and larger D also lowers the ballistic coefficient, so flux drops strongly with D. Bondline temperature follows the heat load: lower flux and steeper, shorter entries both cool it. The g limit caps steepness at about -3.6 deg and the mass-fraction limit caps D near 3.2 m. The best region is therefore large D (2.8-3.3 m), large bluntness paired with a large cone angle so that B*cos(theta) stays about 0.42-0.44 (geometry-valid), and gamma about -3.3 to -3.6 deg. The flux, temperature and g scalings come from fitting the 9 valid rows plus general hypersonic-heating knowledge (stagnation-point heating ~ Rn^-0.5).

**uncertainty:** The geometry rule is fitted from 20 rows. The exact nose-radius definition is not verified, because the reported negative lengths only partly match my formula. The flux exponent on D and the temperature model are extrapolations from few points. Whether max_g depends on D or cone angle is unknown, so the g boundary near -3.6 to -3.8 deg is uncertain. The mass-fraction dependence on cone angle and bluntness is only roughly inferred.

## ai_agent seed_73 call_02  (20 proposals, 1 ask fidelity 1)

**observation:** Only 1 of 16 feasible designs is non-dominated (C-ea2223901bd4: 295k W/m2, 396.2 K). The normalised hypervolume of 0.316 is almost entirely set by bondline temperature: reference span is 150 K and about 0.0059 of hypervolume is gained per kelvin, versus about 0.0014 per 10k W/m2 of flux. Temperature falls with larger D, higher bluntness and cone angle, and steeper entry. Feasibility is capped by max_g (about 12, reached near gamma -3.6) and by heatshield mass fraction (margin near zero at D of about 3.35). Bluntness of 1.25 with cone of 70 deg, and B=1.2 with cone 69 at D=3.0, returned extrapolation failures. Low cone angles at high bluntness return invalid geometry.

**evidence:**
- C-94a9f7a46f9b (D3.2, B1.2, c69.5, -3.8) reaches 392.2 K but max_g is 12.309, so it is infeasible. C-1618bda1fac0 at -3.7 gives 12.139. This implies about 1.7 g per degree and a gamma limit near -3.6 at D of about 3.2.
- g at fixed gamma rises about 0.45 per metre of D. C-ea2223901bd4 (D3.3, -3.4) gives 11.686 and C-963d4cdbada1 (D3.2, -3.5) gives 11.816. This supports about -3.55 as the limit at D of about 3.3.
- Temperature falls about 2.2 K per 0.1 m of D. C-c0f89c462bd0 (D3.1) is 400.8 K and C-963d4cdbada1 (D3.2) is 398.0 K at the same gamma. C-7ef0b45caabb (D3.1) is 398.4 K and C-2b74a3ea4aeb (D3.0) is 399.2 K.
- Mass-fraction margin shrinks about 0.06 per 0.1 m of D. It is 0.209 at D3.0 (C-2b74a3ea4aeb), 0.097 at D3.2 (C-1618bda1fac0) and 0.035 at D3.3 (C-ea2223901bd4). C-f84c59a3cc23 at D3.34 has 0.010. D of about 3.36 is therefore near the limit.
- B/cone effect: C-94a9f7a46f9b (B1.2, c69.5) is about 1.4 K cooler and about 7k lower in flux than C-1618bda1fac0 (B1.0, c66), after correcting for gamma.
- Shallower gamma lowers flux slightly but raises temperature about 1 K per 0.1 deg. C-d2c4b79f3796 (-3.3) is 402.9 K and C-2b74a3ea4aeb (-3.6) is 399.2 K, at similar D.
- Extrapolation failures: C-40f2342796ee (3.0,1.2,69), C-0202524b57fd (2.6,1.25,70) and C-1d24bfa5f84e (2.8,1.25,70). C-94a9f7a46f9b (3.2,1.2,69.5) evaluated fine, so B of 1.2 at cone 69.5 is the edge of the known-safe region.

**mechanism:** Heat flux and bondline temperature both fall as ballistic coefficient falls and effective nose radius rises. Larger D, higher B and larger cone angle all do this, since drag coefficient and nose radius grow. Steeper entry shortens the heat pulse and lowers temperature, but raises peak g. The optimum is therefore pinned at three corners at once: D near the mass-fraction limit (about 3.35), gamma near the g limit (about -3.5 to -3.6), and B/cone near the edge of the aero-surrogate hull (B1.1-1.2, cone 67-69.5). This is largely inferred from the 40 rows, with standard entry-heating physics only as background. The simple additive sensitivities I use are local linear fits and may be off near the constraint edges.

**uncertainty:** The margins on max_g (about 0.003 to 0.02) and mass fraction (about 0 to 0.05) are within my model error, so several proposals near the edge may come back infeasible. Hull behaviour for B of 1.2 or more is unclear because it may depend on D. The effect of gamma on the mass fraction is not separated from the effect of D. The shallow-gamma flux gain is extrapolated from few points.

## ai_agent seed_73 call_03  (20 proposals, 0 ask fidelity 1)

**observation:** The feasible front is 3 points clustered at D~3.34, B=1.2, cone=69.5, gamma -2.8 to -3.5, with normalised HV 0.347. Fitting the near-front rows gives limits set by three constraints. Peak g is about 12 (margin 0.01 at 11.879), and it depends mainly on gamma, rising about 1.64 g/deg, with a weak D effect of about +0.375 g/m. Heatshield mass-fraction margin falls linearly with D at about 0.58 per m, reaching zero near D~3.385 at B=1.2, cone=69.5. Bondline temperature is far below its 450 K limit. Flux and temperature improve slightly with larger D, and the (B=1.2, cone=69.5) corner is the best of the points tested. The g limit puts the steep end near gamma ~ -3.57 at D 3.38. Shallower gamma lowers flux and raises T (about 24 kW/m2 and 11 K per deg). 17 of 60 evaluations returned no geometry. Failures are either a cone angle too small for the bluntness (B=1.2 with cone 66) or cd_fore hull extrapolation at cone 69-70 with B=1.25, or at D 3.0 to 2.8. I therefore stay near the known-good (B, cone) corner and make only three small probes.

**evidence:**
- C-8809880a095e (D3.38, gamma -3.5) has lower flux (273.5k) and lower T (391.86 K) than C-37807858716a (D3.34: 278.3k, 392.57 K). Larger D helps on both objectives, and its mass margin is only 0.0029.
- Mass margin vs D at B=1.2, cone=69.5: 3.2 -> 0.1063, 3.3 -> 0.0496, 3.34 -> 0.0264, 3.36 -> 0.0147, 3.38 -> 0.0029. This gives a linear extrapolation to zero at D~3.385.
- g at gamma -3.5, B=1.2, cone=69.5: 11.849 (D3.3), 11.864 (D3.34), 11.879 (D3.38). g vs gamma: -2.8 -> 10.769, -3.2 -> 11.379, -3.5 -> 11.864, -3.8 -> 12.309 (C-94a9f7a46f9b, infeasible). C-dc8f61b27df5 (D3.2, gamma -3.59) has g 11.957 and is feasible.
- C-681765084fb2 (gamma -2.8) has 261k / 400.2 K, C-eabe3605e502 (gamma -3.2) has 270.9k / 395.7 K. Shallower gamma trades higher T for lower flux, so the front can be extended toward gamma -1.5.
- C-f84c59a3cc23 (gamma -5.54) reaches T=378.9 K but g=15.6, so steeper entry is unreachable under the g limit.
- Failures: C-40f2342796ee (D3.0, B1.2, cone 69), C-5b57439845df (B1.25, cone 70) and C-4b1b4e110042 (B1.25, cone 70) are hull-extrapolation failures. C-3cd51d4bc9fc (B1.2, cone 66) is an invalid geometry. Successful corner points are (1.2, 69.5), (1.15, 68.5), (1.1, 67) and (0.95, 69.5).

**mechanism:** Peak g depends mostly on entry angle, so it is nearly geometry-independent. The g limit therefore caps gamma near -3.57, and the mass fraction caps D near 3.385. Within those caps, larger D lowers ballistic coefficient, so flux and T fall. A larger nose radius (higher B) and a larger cone angle also lower flux and T slightly. The best design is at the corner D~3.38, B=1.2, cone~69.5, gamma just shallower than -3.57. Moving to that corner at each gamma should dominate the D3.34 front points. Shallower gamma at D=3.38 adds coverage of the low-flux, higher-T end. This is fitted from the data; the extrapolation to gamma of about -1.6 relies on smooth trends and is less certain.

**uncertainty:** The gamma-to-g edge is within about 0.01 g of the limit, so the -3.56 and -3.57 points may violate max_g. The mass margin at D=3.384 is about 0.0006, which is also marginal. The T(gamma) curve beyond gamma -2.8 is extrapolated and may be more convex than assumed. The B/cone probes (B 1.22, cone 70, cone 69.8) may hit cd_fore hull extrapolation failures, since the hull shape near the corner is unknown and (1.2, 69) failed at D3.0.

## ai_agent seed_73 call_04  (19 proposals, 1 ask fidelity 1)

**observation:** All 16 front members lie on one curve: D=3.38, B=1.2, cone 69.5, varying only flight_path_angle. Three caps pin this corner. Peak g is 12.0 and depends almost only on gamma, with slope about 1.65 g/deg, so gamma stops near -3.57. The heatshield mass-fraction margin is only about 0.003 at D=3.38, which caps D near 3.385. B=1.2 and cone 69.5-70 are at the edge of the region the cd_fore surrogate covers. Seven of the eight recent geometry failures are extrapolation refusals or too-small-cone overlaps at high B or low cone. The extrapolation refusals are B=1.22, B=1.25, and the D=3.0, cone 69 point. Round 3 gained only 0.007 hypervolume, so the design is converged and further gains are small. What remains is (a) filling gaps along the gamma curve, (b) nudging D from 3.38 to 3.384 with cone 70, and (c) a few probes of B and cone sensitivity.

**evidence:**
- C-fc1968c6c49e (gamma -3.56): g=11.979, margin 0.0017. C-929cd2a6f018 (D=3.36, gamma -3.57): g=11.988, so g is nearly geometry-independent and the g limit is 12.0.
- C-c39a84c0e158 (D=3.384, cone 69.5): mass margin 0.00056, against 0.0029 at D=3.38. That gives a slope of about 0.59 per m, so D is capped near 3.385. Flux is about 115k W/m2 lower per metre of D.
- C-41b2ddb7397c (cone 70) has mass margin 0.0031, against 0.0029 at cone 69.5. Flux and T are essentially unchanged by cone (273480 vs about 273500 interpolated), so cone 70 buys slightly more D headroom at no cost.
- C-1618bda1fac0 (D=3.2, B=1.0, cone 66) against C-94a9f7a46f9b (D=3.2, B=1.2, cone 69.5): lower B and cone raise flux by about 4% and T by about 1.5 K. That argues for B at its maximum.
- C-68332aab55f2 (B=1.22), C-5b57439845df, C-4b1b4e110042 and C-40f2342796ee (D=3.0, cone 69) all failed on cd_fore extrapolation, so the safe region ends near B=1.2, cone 69.5-70. C-3cd51d4bc9fc (D=3.3, B=1.2, cone 66) is an invalid geometry.
- The front's gamma spacing has gaps of 0.2-0.4 deg around -1.6..-2.0, -2.6..-3.0 and -3.3..-3.4. Flux runs from 229.7k to 275k and T from 416 K to 391 K along it.

**mechanism:** Stagnation heating scales roughly with Rn^-0.5 (prior knowledge, consistent with the flux-vs-B and flux-vs-D data). A larger D lowers the ballistic coefficient and raises nose radius, so both flux and T fall. A steeper gamma shortens the heat pulse and lowers T by about 10 K/deg, while raising g by about 1.65/deg. The optimum therefore sits at the corner: D at the mass-fraction cap, gamma at the g cap, and B and cone at the surrogate/geometry boundary. Reducing D relaxes g slightly (about 0.37 g per m) but raises T more than the steeper gamma removes it, so it does not help. Relative to the 450 K reference, T is the more valuable objective. The remaining gains are tiny gap-filling in gamma, a 0.004 m D increase using cone 70, and possibly a slightly higher B if the surrogate allows it.

**uncertainty:** The size of the B effect on mass fraction and on the hull boundary is unknown. The B=1.205 and B=1.21 probes may return a cd_fore extrapolation failure, which costs a slot. The D=3.384 designs have mass margin below 0.001, so a small model nonlinearity could push them infeasible. The g limit at gamma -3.565 has a margin of about 0.001, and my estimates of the D and B effects on g are extrapolated from few points. Flux and T predictions for the lower-B and lower-D probes are extrapolated from single points at different gamma.

## ai_agent seed_73 call_05  (21 proposals, 1 ask fidelity 1)

**observation:** Progress has stalled: normalised hypervolume went 0.3161 to 0.3469 to 0.3540 to 0.3550 over rounds 1-4. All 25 front points are one curve along flight_path_angle at the corner D~3.38, B=1.2, cone 69.5-70. Peak g caps the steepness at about -3.57 deg. The mass-fraction margin caps D at about 3.385 (margin 0.0007 at D=3.384). Bluntness above 1.2 fails with the aero-surface extrapolation error, and cone 66 at B=1.2 gives an invalid geometry. Every off-corner design I have is dominated: C-c2876c011ef7 (B=1.1), C-df6184e17083 (B=0.88), and the small-D or low-B rows.

**evidence:**
- C-f71f4a44911d (D 3.384, cone 70, gamma -3.565): g margin 0.00078, mass margin 0.00074, flux 274.6k, T 391.15 K. This is the corner, pinned by g and mass.
- C-2b5fe1686946 and C-06ef682a7ce9 (gamma -1.5 and -1.7): flux 227.7k and 231.7k, T 418.0 and 414.7 K. The front is a smooth curve in gamma, about 10 K/deg and 24k W/m2 per deg, with gaps of 2-3 K between neighbours.
- Mass-fraction margin is 0.0029 at D=3.38 and 0.00074 at D=3.384. That is a slope of about -0.55 to -0.6 per m, so the margin reaches zero near D=3.385. Cone changes it negligibly (C-e2aaf4242e38 at cone 69.8: 0.0030).
- C-c2876c011ef7 (B 1.1, D 3.36) and C-df6184e17083 (B 0.88, D 3.3) at gamma -3.5 have flux 280.7k and 302.6k and T 392.9 and 395.7 K, both worse than C-e2aaf4242e38 (273.5k, 391.9 K). Lower B and lower D are dominated.
- Extrapolation failures at B 1.205, 1.21, 1.22 and 1.25 (C-05beb8f06d5f, C-3d41ce848a30, C-68332aab55f2, C-5b57439845df). B=1.2 is the effective ceiling of the aero surrogate.
- Large-D or steep-gamma designs (C-4cf8bee56534, C-f84c59a3cc23) violate g or mass and gain little T. g rises about 1.7 per deg of steepness.

**mechanism:** Peak g is set almost entirely by entry angle (about 1.7 per deg of steepness). Bondline T falls about 10 K/deg as the entry steepens, so g caps T near 391 K. Mass fraction caps D near 3.385. Larger D, higher B and larger cone lower flux and T, but all three are at their ceilings (B by the surrogate hull, cone by the variable bound). The remaining lever is the position along gamma. Given the corner is saturated, the reliable gain is to densify the front, since hypervolume is a staircase and each intermediate point adds a small area. I do this at the proven mass-safe D=3.384. Two points at D=3.385 probe the last sliver of D and gamma next to the g and mass limits. This relies on local interpolation of the existing series, plus the roughly linear g(gamma) trend.

**uncertainty:** Each expected gain is small, at most about 1e-5 in normalised hypervolume. The D=3.385 points depend on my estimate of the mass-margin slope; the margin should be about +0.0001 to +0.0002, but could be slightly negative. The -3.567 point sits within about 0.005 of the g limit. I have not found a way past the g and mass corners; a different region would need new information, such as a larger B-cone surrogate hull. Flux and T predictions are interpolations and should be accurate to about 1k W/m2 and 0.3 K.

## ai_agent seed_73 call_06  (20 proposals, 0 ask fidelity 1)

**observation:** The feasible front is one line of designs at D~3.384, B=1.2, cone=70, spread over gamma from -1.5 to -3.567. Flux runs 227k to 275k W/m2 and bondline T runs 418 to 391 K. The front is pinned at three limits: D by heatshield mass fraction (margin ~0 at D=3.385), gamma by max_g (margin 0.0005 at -3.567), and B and cone by the surrogate hull and the variable bound. Eight of the ten geometry failures came from trying B>1.2, so B=1.2 is the practical ceiling. Hypervolume gains have shrunk to about 0.0003 per round, so the front is near saturation. The fixed 2.5e6 flux reference means a real hypervolume gain would need lower T at similar flux, and I found no lever for that in the data.

**evidence:**
- C-78a9a956afab (gamma -3.567) has max_g margin 0.0005 and mass margin 0.00014. C-733cdcb996ae (D=3.385) has mass margin 0.00014 against 0.00074 at D=3.384, so the D cap is about 3.3852.
- C-1618bda1fac0 (D=3.2, gamma -3.7, g=12.139) and C-94a9f7a46f9b (D=3.2, gamma -3.8, g=12.309) sit about 0.07 below the D=3.384 g-vs-gamma line. So g falls only ~0.4 per metre of D, which lets gamma steepen by only ~0.24 deg per metre. Meanwhile flux and T rise strongly as D falls (C-94a9f7a46f9b: 304k W/m2 and 392.2 K, worse than the corner), so shrinking D does not pay.
- Along the D=3.384 line, T falls about 10-13 K/deg of steepening and flux rises about 24k W/m2/deg (e.g. C-6a031c8b7ef2 to C-78a9a956afab). Both are nearly linear, so interpolated gamma values are predictable.
- C-0202524b57fd, C-1d24bfa5f84e, C-5b57439845df, C-4b1b4e110042, C-68332aab55f2, C-3d41ce848a30 and C-05beb8f06d5f all failed the cd_fore convex-hull check. That confirms B>1.2 is unreachable; the sixth failure, C-3cd51d4bc9fc, is a cone-angle geometry failure. So I keep B<=1.2 and cone=70.
- Off-corner designs such as C-f84c59a3cc23, C-b545729400dd and C-4cf8bee56534 are infeasible on max_g or mass fraction, so they give no route to a lower T.

**mechanism:** Peak g depends almost entirely on gamma, with a weak D dependence, which caps gamma near -3.57. Flux and T fall as D, B and cone rise, because ballistic coefficient drops and nose radius grows. That pushes D, B and cone to their caps (mass fraction, hull, bound). This is my physical reading of the data, partly informed by the general Rn^-0.5 stagnation-heating scaling from prior knowledge. Little hypervolume is left, so I spend most of the slots on gamma values not yet evaluated, including gaps in the front where flux steps by 3-5k. I also push gamma and D to the g and mass limits, and add two low-cost probes: one near the mass cap and one on the D-g tradeoff.

**uncertainty:** The main risk is duplicates of the 19 front points I cannot see; I used non-round gamma values to reduce that. Interpolated T and flux should be good to about 0.1 K and 0.3k W/m2. The limit-pushing points (gamma near -3.57, D near 3.3852) may cross g or mass-fraction margins of ~1e-4. The B=1.19 and D=3.3 probes rely on extrapolating the mass-fraction and g dependence on D and B from only a few points.

## ai_agent seed_73 call_07  (19 proposals, 1 ask fidelity 1)

**observation:** The feasible front is essentially one line: D=3.384-3.385, B=1.2, cone=70 (all at their caps), with flight path angle gamma swept from -1.5 to -3.57. Peak g reaches 12 at gamma near -3.57. Heatshield mass fraction caps D near 3.3853, and the cd_fore surrogate hull caps B near 1.2. Normalised hypervolume has stalled at about 0.3555 over rounds 4-6 (gains of 1e-3, 3e-4, 2e-4). Because the flux reference is 2.5e6 and front fluxes are 227k-275k, hypervolume is driven almost entirely by bondline temperature. Fine spacing along gamma and the corner point matter more than any other region.

**evidence:**
- C-d091f610d31f (D 3.385, gamma -3.5695): flux 274560, T 391.09, g margin 1.3e-4, mass-fraction margin 1.4e-4. This is the corner design, pinned by g and mass fraction.
- C-c3f9f333f061 and C-9690b44cafcb: mass-fraction margin goes 8.6e-5 to 2.7e-5 as D goes 3.3851 to 3.3852, so the D cap is about 3.38525.
- C-3da7d9bac3e7 and C-eed229743768: g rises about 1.6-1.7 per deg near -3.5, and T falls about 10 K/deg.
- C-363a563b3536 (D 3.3): flux 285110, T 392.49 against 274.5k and 391.1 at D 3.385. Smaller D is worse in both objectives.
- C-94a9f7a46f9b and C-1618bda1fac0: g is close to independent of B and cone, and rises only about 0.4 per metre of D. Stepping to smaller D therefore buys almost no extra gamma.
- C-0202524b57fd, C-5b57439845df, C-3d41ce848a30 and C-05beb8f06d5f: B above 1.2 at cone 70 falls outside the surrogate hull. C-3cd51d4bc9fc: cone 66 with B 1.2 is invalid geometry. Both are cap-like limits.
- C-7a7d7f365bcc (D 3.38, B 1.19): mass-fraction margin 0.0028 against about 0.0031 expected at B 1.2, so lower B slightly raises mass. It also gives a slightly higher flux and T.

**mechanism:** Peak g depends almost entirely on gamma (about 1.65 per deg near -3.57, less at shallow angles). That sets a fixed steepness cap, which in turn sets the minimum T reachable. Larger D lowers ballistic coefficient and raises nose radius, so flux and T both fall, but the mass-fraction limit stops D at about 3.385. Higher B and cone have the same helpful effect and sit at the hull and variable bounds. Mass fraction scales roughly as D squared and worsens slightly as cone or B drop. The optimum is therefore a fixed corner. Remaining improvement is limited to filling gamma gaps on the line, nudging gamma to the g cap, and a few probes of cone and B near the corner. This is based on the data; the Rn^-0.5 stagnation scaling is prior knowledge and was not needed for these picks.

**uncertainty:** Line-interpolated predictions are reliable to a few hundred W/m2 and a few tenths of a K. The corner points (gamma -3.5700) sit within about 1e-4 of the g and mass-fraction limits, so a feasibility flip is possible. The cone and B probes could trigger a geometry or hull failure, since the boundary between cone 66 (invalid) and cone 69.5 (valid) is unknown. The cone and B sensitivities are only weakly identified from confounded rows. I do not expect any hidden basin, but I cannot rule one out in unexplored corners.

## ai_agent seed_73 call_08  (26 proposals, 0 ask fidelity 1)

**observation:** The front is a one-dimensional curve. It comes from designs at D~3.384, B=1.2, cone=70 with flight_path_angle_deg swept from -1.5 to -3.57 (flux 227k-275k W/m2, bondline T 418-391 K). Three caps pin it. Peak g is about 1.7/deg of steepness and reaches the 12 limit at gamma~-3.57. Heatshield mass margin scales as D^2 and reaches zero at D~3.38524. B and cone are at the surrogate-hull and variable bounds. Hypervolume gains have fallen to ~1e-4 per round.

**evidence:**
- C-25994855d0b4 (D=3.3852, gamma=-3.57): g margin 4e-5 and mass margin 2.7e-5, so both caps are active at once.
- C-92f6aed905e3 to C-eed229743768: T falls ~10-16 K/deg and flux rises ~20-24k W/m2/deg along gamma at fixed geometry. Spacing gaps remain at gamma -3.0 to -3.3, -2.1 to -2.3 and -1.5 to -1.65.
- C-363a563b3536 (D=3.3, gamma=-3.58) has flux 285k and T 392.5, worse than the D=3.384 points. Smaller D therefore does not help.
- C-02209f2ea644 (B=1.15) has a lower mass margin than B=1.2, so lower B is worse. C-3d41ce848a30 and C-05beb8f06d5f (B=1.21 and 1.205 at cone 70) fail the surrogate hull, so the B bound lies between 1.2 and 1.205.
- Round-7 hypervolume 0.355471 to 0.355514 shows the front is saturated.

**mechanism:** Flux and T fall with ballistic coefficient and nose radius, which favours large D, B and cone. The mass fraction (~D^2, slightly worse at lower B) caps D. Peak g depends almost only on gamma and caps steepness. This is my reading of the data, plus the general Rn^-0.5 heating scaling from prior knowledge. Little remains except filling gamma gaps and adding the last 0.0012 m of D, which trims flux by ~150 W/m2 and T by ~0.02 K. Two probes test whether B can rise slightly above 1.2 at cone 70, which would relieve the mass cap.

**uncertainty:** The interpolated predictions are linear and could be off by a few hundred W/m2 or ~0.3 K. The g boundary at gamma=-3.5702 is within ~1e-4 of the limit. The hull probes at B=1.201 and 1.202 may fail as a no-geometry extrapolation. I have no evidence of any un-tried region that beats this corner.

## ai_agent seed_73 call_09  (26 proposals, 0 ask fidelity 1)

**observation:** The feasible front is essentially a one-parameter curve in flight_path_angle. Every non-dominated point sits at D~3.385, B=1.2, cone=70 (flux 227k to 275k W/m2, bondline T 418 to 391 K). Three limits pin the corner. Mass fraction caps D (margin 2.7e-5 at D=3.3852). The surrogate hull blocks B>1.2 (seven hull failures near this corner). The cone is at its variable bound of 70. Peak g caps steepness at about -3.5702 (margin 1.3e-5). Round 8 gained only 4.5e-5 hypervolume, so almost nothing is left. The remaining options are a marginally larger D and denser gamma coverage.

**evidence:**
- C-844c9143a25c: gamma=-3.5702 gives g=12.0000 (margin 1.26e-5), flux 274550, T 391.08. This is the steep-end corner.
- C-6daecae7b30e: gamma=-1.5 (bound) gives flux 227200, T 417.87. This is the shallow-end corner.
- D=3.384 gives mass margin 7.356e-4 (C-1120f80f8763) and D=3.3852 gives 2.677e-5 (C-844c9143a25c). The slope of about -0.59/m matches margin proportional to D^2, and extrapolates to a zero at D~3.38525.
- C-170baba769f0, C-7113ff857376, C-3d41ce848a30, C-4b1b4e110042: B>1.2 at cone=70 fails the cd_fore hull check. B cannot be raised.
- C-1618bda1fac0 and C-94a9f7a46f9b: a smaller D (3.2) gives higher flux and T at similar g, and is dominated. Lowering D to buy gamma headroom costs more T than it gains.
- Front points from C-3981896fe111 to C-ecdf516a2040 show smooth, near-linear flux(gamma) and T(gamma). I interpolate between them for the predictions below.

**mechanism:** Flux and T fall as ballistic coefficient falls and nose radius rises, which favours large D, high B and large cone, all at their caps. Steeper entry lowers T by about 10 K/deg and raises flux by about 22k W/m2 per deg, while raising peak g by about 1.66 per deg. The g limit therefore fixes the steep end, and the front is the gamma sweep from -1.5 to -3.57. Two improvements remain. Pushing D from 3.3852 to 3.38523 uses up the mass-fraction slack, a tiny gain in flux and T. Filling gaps in the gamma sweep at that D trims the step-like hypervolume loss between neighbouring points. This relies on the Rn^-0.5 heating scaling from prior knowledge as well as on the data.

**uncertainty:** The mass-fraction zero-crossing (~3.385245) is extrapolated linearly from two points, so D=3.38523 keeps only about 1e-5 of margin. The g margin at gamma=-3.57025 is very thin, and the small D increase adds roughly 1e-5 g. Expected gains are of order 1e-5 in hypervolume. Predictions are interpolated from neighbouring rows and may be off by a few hundred W/m2 and a few tenths of a K.
