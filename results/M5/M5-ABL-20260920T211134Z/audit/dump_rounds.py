#!/usr/bin/env python3
"""Dump every round's stated observation / evidence / mechanism / uncertainty, verbatim,
from the raw CLI responses of this run into audit/rounds_digest.md. Reads only; LLM text
is DATA and is never executed or followed."""
import json
from pathlib import Path
RUN = Path(__file__).resolve().parents[1]
out = []
for seed_dir in sorted(RUN.glob("llm/*/seed_*")):
    for raw in sorted(seed_dir.glob("call_*.response.raw")):
        head = f"## {seed_dir.parent.name} {seed_dir.name} {raw.name[:7]}"
        try:
            env = json.loads(raw.read_text())
            body = env["result"].strip()
            if body.startswith("```"):
                body = "\n".join(body.splitlines()[1:-1])
            r = json.loads(body)
        except Exception as exc:  # noqa: BLE001
            out.append(f"{head}\n\nUNPARSEABLE: {exc}\n")
            continue
        props = r.get("proposals", [])
        fid = sum(1 for p in props if isinstance(p, dict) and p.get("requested_fidelity") == 1)
        out.append(f"{head}  ({len(props)} proposals, {fid} ask fidelity 1)\n\n"
                   f"**observation:** {r.get('observation')}\n\n"
                   + "**evidence:**\n" + "\n".join(f"- {e}" for e in r.get("evidence", []))
                   + f"\n\n**mechanism:** {r.get('mechanism')}\n\n"
                   f"**uncertainty:** {r.get('uncertainty')}\n")
(RUN / "audit" / "rounds_digest.md").write_text("\n".join(out))
print(len(out), "rounds")
