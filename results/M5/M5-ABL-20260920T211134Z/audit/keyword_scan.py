#!/usr/bin/env python3
"""Count, per LLM method, in how many rounds the stated observation/mechanism/uncertainty
mention given themes. Crude regex counts over persisted text; a reading aid, not a finding."""
import json, re
from pathlib import Path
RUN = Path(__file__).resolve().parents[1]
THEMES = {
 "admits_prior_knowledge": r"prior|Allen|Sutton|textbook|known scaling|standard .* scaling",
 "names_allen_eggers": r"Allen",
 "names_sutton_graves": r"Sutton",
 "front_is_1d_in_gamma": r"one-parameter|one-dimensional|1-D|only gamma|gamma alone|only flight|only the flight|only entry",
 "mass_fraction_caps_D": r"mass[- ]fraction",
 "hull_or_extrapolation_fence": r"hull|extrapolat\w+ (error|failure)|surrogate",
 "cone_is_validity_lever": r"cone .* (valid|geometr)|geometr\w* .* cone",
 "mentions_Cd_or_drag_coefficient": r"\bC_?[dD]\b|drag coefficient|CdA",
 "says_shape_raises_drag": r"higher[- ]drag|high-drag|more drag|raises? drag|increase[sd]? drag",
 "questions_realism_of_a_limit": r"unphysical|unrealistic|not realistic|placeholder|implausib|no real|cannot be built|impractical",
 "mentions_shoulder": r"shoulder",
 "hv_dominated_by_bondline_axis": r"dominated by .*(bondline|temperature)|1 K .* worth|temperature .* matters most",
}
out = {}
for mdir in sorted(RUN.glob("llm/*")):
    n = 0; hits = {k: 0 for k in THEMES}; first = {}
    for raw in sorted(mdir.glob("seed_*/call_*.response.raw")):
        try:
            body = json.loads(raw.read_text())["result"].strip()
            if body.startswith("```"): body = "\n".join(body.splitlines()[1:-1])
            r = json.loads(body)
        except Exception: continue
        n += 1
        text = " ".join([r["observation"], r["mechanism"], r["uncertainty"]])
        call = int(raw.name[5:7])
        for k, pat in THEMES.items():
            if re.search(pat, text, flags=re.I):
                hits[k] += 1
                key = (k, raw.parent.name)
                first.setdefault(k, {}).setdefault(raw.parent.name, call)
    out[mdir.name] = {"rounds_parsed": n, "rounds_mentioning": hits, "first_call_by_seed": first}
(RUN / "audit" / "keyword_scan.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
