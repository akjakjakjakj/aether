"""M5: the AI engineering agent - an LLM proposing candidates through the same budget meter.

Conceptual anchor
-----------------
The agent is an optimiser whose "mutation operator" is a language model. Each round it is
shown STRUCTURED DATA ONLY - the variable bounds, a table of what has been evaluated so
far (the feasible front, near misses, recent failures, with metrics and constraint
margins), and the budget left - and must answer with JSON in the spec section 23 schema:
what it observed, the evidence, the mechanism it believes in, and a batch of proposals,
each with a PARENT design, the parameter changes from that parent, a rationale, an
expected outcome, its uncertainty, a reason to simulate and a requested fidelity.

Three rules make it auditable and keep it honest:

  * LLM output is UNTRUSTED DATA. It is parsed as JSON and checked field by field against
    a strict schema. Nothing in it is executed, interpolated into a command, or used as a
    path. A malformed answer, an unknown field, a value outside the box, an unknown
    parent: REJECTED and LOGGED, never clipped, never repaired. The rejection count is a
    reported metric of the method.
  * Every design the agent does get evaluated goes through `BudgetedEvaluator`, exactly
    as NSGA-II's offspring do. The agent cannot see a result it did not pay for.
  * Every prompt and every raw response is written verbatim under the run directory.
    `ReplayClient` re-runs the whole pipeline from those files, so the study can be
    reproduced by someone with no LLM access (spec section 50), and the tests never make
    a live call.

LLM access is a subprocess call to the Claude Code CLI in headless mode. No API key is
read, stored or accepted here. The CLI is run in an empty temporary directory with tools,
MCP servers, hooks, skills and CLAUDE.md discovery switched off, so the model sees the
prompt and nothing else - in particular not this repository's M4 report.
"""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
import tempfile
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Protocol

import numpy as np

from ..surrogate.model import MIN_TRAINING_ROWS, DesignSurrogate, has_physics
from .bayes import initial_design_size
from .budget import MARGIN_NAMES, BudgetedEvaluator, BudgetExhausted
from .fidelity import PromotionPolicy
from .pareto import normalised_hypervolume, pareto_front
from .sampling import latin_hypercube

SCHEMA_VERSION = "aether.m5.agent/1"
UNCERTAINTY_LEVELS = ("low", "medium", "high")
_MAX_TEXT = 1500          # characters, per free-text field
_MAX_EVIDENCE = 12
_FALLBACK_GENERATION = 9000

SYSTEM_PROMPT = (
    "You are an engineering optimisation agent inside an automated design loop. You are "
    "given structured data as JSON and must reply with ONE JSON object and nothing else: "
    "no prose before or after it, no markdown fence. You have no tools. Base your "
    "proposals on the data you are shown; say so when you are relying on prior knowledge "
    "rather than on the data."
)


# ---------------------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------------------
def response_schema(variable_names: tuple[str, ...], objectives: tuple[str, ...],
                    n_proposals: int) -> dict[str, Any]:
    """The JSON Schema the agent is shown. Validation is done by `validate_response`
    (hand-written, stricter: it also checks bounds and parents), not by a schema library."""
    text = {"type": "string", "minLength": 1, "maxLength": _MAX_TEXT}
    return {
        "type": "object", "additionalProperties": False,
        "required": ["observation", "evidence", "mechanism", "uncertainty", "proposals"],
        "properties": {
            "observation": text,
            "evidence": {"type": "array", "minItems": 1, "maxItems": _MAX_EVIDENCE,
                         "items": text},
            "mechanism": text,
            "uncertainty": text,
            "proposals": {
                "type": "array", "minItems": 1, "maxItems": n_proposals,
                "items": {
                    "type": "object", "additionalProperties": False,
                    "required": ["parent_id", "rationale", "parameter_changes",
                                 "expected_outcome", "uncertainty", "reason_to_simulate",
                                 "requested_fidelity"],
                    "properties": {
                        "parent_id": {"type": "string"},
                        "rationale": text,
                        "parameter_changes": {
                            "type": "object", "additionalProperties": False, "minProperties": 1,
                            "properties": {name: {"type": "number"}
                                           for name in variable_names}},
                        "expected_outcome": {
                            "type": "object", "additionalProperties": False,
                            "required": [*objectives, "feasible"],
                            "properties": {**{name: {"type": "number"} for name in objectives},
                                           "feasible": {"type": "boolean"}}},
                        "uncertainty": {"enum": list(UNCERTAINTY_LEVELS)},
                        "reason_to_simulate": text,
                        "requested_fidelity": {"enum": [0, 1]},
                    },
                },
            },
        },
    }


class MalformedResponse(ValueError):
    """The response as a whole cannot be used: not JSON, or top-level fields wrong."""


@dataclass(frozen=True)
class Proposal:
    index: int
    parent_id: str
    values: dict[str, float]            # active-variable values after the changes
    parameter_changes: dict[str, float]
    rationale: str
    expected_outcome: dict[str, Any]
    uncertainty: str
    reason_to_simulate: str
    requested_fidelity: int


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _text_ok(value: Any) -> bool:
    return isinstance(value, str) and 0 < len(value.strip()) and len(value) <= _MAX_TEXT


def parse_response(text: str) -> dict[str, Any]:
    """The model's answer as a dict, or `MalformedResponse`. JSON only: `json.loads` on
    the text, after removing at most one enclosing markdown fence. Nothing is evaluated."""
    body = text.strip()
    if body.startswith("```"):
        lines = body.splitlines()
        if len(lines) >= 3 and lines[-1].strip() == "```":
            body = "\n".join(lines[1:-1])
    try:
        obj = json.loads(body)
    except json.JSONDecodeError as exc:
        raise MalformedResponse(f"not valid JSON: {exc.msg} at character {exc.pos}") from exc
    if not isinstance(obj, dict):
        raise MalformedResponse("top level is not a JSON object")
    required = {"observation", "evidence", "mechanism", "uncertainty", "proposals"}
    if set(obj) != required:
        raise MalformedResponse(f"top-level keys {sorted(obj)} != {sorted(required)}")
    for key in ("observation", "mechanism", "uncertainty"):
        if not _text_ok(obj[key]):
            raise MalformedResponse(f"'{key}' must be a non-empty string of at most "
                                    f"{_MAX_TEXT} characters")
    evidence = obj["evidence"]
    if (not isinstance(evidence, list) or not 1 <= len(evidence) <= _MAX_EVIDENCE
            or not all(_text_ok(item) for item in evidence)):
        raise MalformedResponse("'evidence' must be a list of 1 to "
                                f"{_MAX_EVIDENCE} non-empty strings")
    if not isinstance(obj["proposals"], list) or not obj["proposals"]:
        raise MalformedResponse("'proposals' must be a non-empty list")
    return obj


def validate_proposals(response: dict[str, Any], *, bounds: dict[str, tuple[float, float]],
                       objectives: tuple[str, ...], parents: dict[str, dict[str, float]],
                       seen_keys: set[tuple[float, ...]], quota: int
                       ) -> tuple[list[Proposal], list[dict[str, Any]]]:
    """Split a parsed response into accepted proposals and logged rejections.

    `parents` maps every evaluated candidate ID to its active-variable values. A proposal
    inherits its parent's values and overrides the ones in `parameter_changes`.
    Rejection reasons (each is counted in the report):
      schema              wrong type, missing or extra field, empty change set
      unknown_parent      `parent_id` is not an evaluated design of this run
      unknown_variable    a changed variable is not an active design variable
      non_finite          NaN or infinity
      out_of_bounds       outside the box - NOT clipped
      no_change           identical to its parent
      duplicate           identical to an evaluated design or to an earlier proposal
      over_quota          more proposals than were asked for
    """
    names = tuple(bounds)
    proposal_keys = {"parent_id", "rationale", "parameter_changes", "expected_outcome",
                     "uncertainty", "reason_to_simulate", "requested_fidelity"}
    accepted: list[Proposal] = []
    rejected: list[dict[str, Any]] = []
    batch_keys: set[tuple[float, ...]] = set()

    def reject(index: int, reason: str, detail: str, raw: Any) -> None:
        rejected.append({"index": index, "reason": reason, "detail": detail, "proposal": raw})

    for index, raw in enumerate(response["proposals"]):
        if not isinstance(raw, dict) or set(raw) != proposal_keys:
            keys = sorted(raw) if isinstance(raw, dict) else type(raw).__name__
            reject(index, "schema", f"proposal keys {keys} != {sorted(proposal_keys)}", raw)
            continue
        changes, outcome = raw["parameter_changes"], raw["expected_outcome"]
        if not (isinstance(raw["parent_id"], str) and _text_ok(raw["rationale"])
                and _text_ok(raw["reason_to_simulate"])
                and raw["uncertainty"] in UNCERTAINTY_LEVELS
                and raw["requested_fidelity"] in (0, 1)
                and not isinstance(raw["requested_fidelity"], bool)
                and isinstance(changes, dict) and changes
                and isinstance(outcome, dict)
                and set(outcome) == {*objectives, "feasible"}
                and isinstance(outcome["feasible"], bool)
                and all(_is_number(outcome[name]) for name in objectives)):
            reject(index, "schema", "a field has the wrong type or an illegal value", raw)
            continue
        if raw["parent_id"] not in parents:
            reject(index, "unknown_parent", f"'{raw['parent_id']}' was never evaluated", raw)
            continue
        unknown = sorted(set(changes) - set(names))
        if unknown:
            reject(index, "unknown_variable", f"not active design variables: {unknown}", raw)
            continue
        if not all(_is_number(v) for v in changes.values()):
            reject(index, "schema", "parameter_changes values must be numbers", raw)
            continue
        if not all(math.isfinite(float(v)) for v in changes.values()):
            reject(index, "non_finite", "NaN or infinite parameter value", raw)
            continue
        outside = {name: float(v) for name, v in changes.items()
                   if not bounds[name][0] <= float(v) <= bounds[name][1]}
        if outside:
            reject(index, "out_of_bounds",
                   "; ".join(f"{n} = {v:g} outside [{bounds[n][0]:g}, {bounds[n][1]:g}]"
                             for n, v in outside.items()), raw)
            continue
        values = dict(parents[raw["parent_id"]])
        values.update({name: float(v) for name, v in changes.items()})
        key = tuple(values[name] for name in names)
        if key == tuple(parents[raw["parent_id"]][name] for name in names):
            reject(index, "no_change", "identical to its parent", raw)
            continue
        if key in seen_keys or key in batch_keys:
            reject(index, "duplicate", "identical to an evaluated or already proposed design",
                   raw)
            continue
        if len(accepted) >= quota:
            reject(index, "over_quota", f"only {quota} proposals were requested", raw)
            continue
        batch_keys.add(key)
        accepted.append(Proposal(
            index=index, parent_id=raw["parent_id"], values=values,
            parameter_changes={name: float(v) for name, v in changes.items()},
            rationale=raw["rationale"], expected_outcome=dict(outcome),
            uncertainty=raw["uncertainty"], reason_to_simulate=raw["reason_to_simulate"],
            requested_fidelity=int(raw["requested_fidelity"])))
    return accepted, rejected


# ---------------------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------------------
def _sig(value: Any, digits: int = 5) -> Any:
    if isinstance(value, bool) or value is None:
        return value
    value = float(value)
    if not math.isfinite(value):
        return None
    return float(f"{value:.{digits}g}")


def _row_view(row: dict[str, Any], active: tuple[str, ...], objectives: tuple[str, ...]
              ) -> dict[str, Any]:
    view: dict[str, Any] = {
        "id": row["candidate_id"],
        "x": {name: _sig(row[f"x__{name}"]) for name in active},
        **{name: _sig(row[name]) for name in objectives},
        "max_g": _sig(row["max_g"]),
        "feasible": bool(row["feasible"]),
    }
    margins = {name: _sig(row[f"margin__{name}"], 4) for name in MARGIN_NAMES
               if not math.isnan(row[f"margin__{name}"])}
    if margins:
        view["margins"] = margins
    if row["failure_reason"]:
        view["failure_reason"] = str(row["failure_reason"])[:240]
    return view


def _violation(row: dict[str, Any]) -> float:
    deficits = [max(0.0, -row[f"margin__{name}"]) for name in MARGIN_NAMES
                if not math.isnan(row[f"margin__{name}"])]
    return float(sum(deficits))


def build_prompt(rows: list[dict[str, Any]], evaluator: BudgetedEvaluator,
                 objectives: tuple[str, ...], hv_cfg: dict[str, Any], *, quota: int,
                 rounds_left: int, history: list[dict[str, Any]],
                 table_sizes: dict[str, int]) -> str:
    """The complete user prompt: fixed instructions plus one JSON payload. Deterministic
    in its inputs, so a replayed run regenerates it byte for byte."""
    space = evaluator.space
    active = space.active
    paid = [row for row in rows if not row["cache_hit"]]
    feasible = [row for row in paid if row["feasible"]]
    ideal = np.array([hv_cfg["ideal_point"][name] for name in objectives], dtype=float)
    ref = np.array([hv_cfg["reference_point"][name] for name in objectives], dtype=float)

    front_rows: list[dict[str, Any]] = []
    if feasible:
        values = np.array([[row[name] for name in objectives] for row in feasible], dtype=float)
        _, first = np.unique(values, axis=0, return_index=True)   # inert-variable twins
        distinct = [feasible[i] for i in sorted(first)]
        idx = pareto_front(np.array([[row[name] for name in objectives] for row in distinct]))
        front_rows = sorted((distinct[i] for i in idx), key=lambda r: r[objectives[0]])
    n_front = int(table_sizes["front"])
    if len(front_rows) > n_front:   # thin evenly, always keeping both extremes
        keep = np.unique(np.linspace(0, len(front_rows) - 1, n_front).round().astype(int))
        front_shown = [front_rows[i] for i in keep]
    else:
        front_shown = front_rows
    near = sorted((row for row in paid if has_physics(row) and not row["feasible"]),
                  key=_violation)[: int(table_sizes["near_feasible"])]
    recent = paid[-int(table_sizes["recent"]):]
    failures = [row for row in paid if not has_physics(row)][-int(table_sizes["failures"]):]

    violated: dict[str, int] = {}
    for row in paid:
        for name in row["violated_constraints"]:
            violated[name] = violated.get(name, 0) + 1
    hv_now = normalised_hypervolume(
        np.array([[row[name] for name in objectives] for row in feasible], dtype=float)
        if feasible else np.empty((0, 2)), ideal, ref)

    payload = {
        "schema_version": SCHEMA_VERSION,
        "problem": ("Design of an atmospheric-entry capsule and its entry flight-path "
                    "angle. Each design is scored by a reduced-order simulator. Both "
                    "objectives are MINIMISED. A design is feasible only if every "
                    "constraint margin is >= 0; a margin is (limit - value) / limit. Some "
                    "parameter combinations are not a buildable geometry: they return no "
                    "metrics, only a failure_reason, and still cost one evaluation. "
                    "Progress is measured by the hypervolume of the feasible "
                    "non-dominated set against the fixed reference point below (larger is "
                    "better): it rewards both better designs and a well-covered trade-off."),
        "design_variables": [{"name": v.name, "units": v.units, "min": v.lower, "max": v.upper}
                             for v in space.active_variables],
        "fixed_parameters": {v.name: {"value": v.reference, "units": v.units}
                             for v in space.variables if v.name not in active},
        "objectives": [{"name": name, "goal": "minimise",
                        "hypervolume_reference": float(hv_cfg["reference_point"][name]),
                        "ideal": float(hv_cfg["ideal_point"][name])} for name in objectives],
        "constraints": [name for name in MARGIN_NAMES
                        if any(not math.isnan(row[f"margin__{name}"]) for row in paid)],
        "budget": {"total_evaluations": evaluator.budget, "spent": evaluator.used,
                   "remaining": evaluator.remaining, "rounds_remaining": rounds_left,
                   "proposals_requested_now": quota},
        "evaluated_summary": {
            "n_evaluated": len(paid), "n_feasible": len(feasible),
            "n_no_geometry": sum(not has_physics(row) for row in paid),
            "constraint_violation_counts": dict(sorted(violated.items())),
            "feasible_front_size": len(front_rows),
            "hypervolume_normalised": _sig(hv_now, 6),
        },
        "feasible_non_dominated": [_row_view(r, active, objectives) for r in front_shown],
        "nearly_feasible": [_row_view(r, active, objectives) for r in near],
        "most_recent": [_row_view(r, active, objectives) for r in recent],
        "recent_geometry_failures": [_row_view(r, active, objectives) for r in failures],
        "your_previous_rounds": history,
        "response_schema": response_schema(active, objectives, quota),
    }
    instructions = (
        f"Propose exactly {quota} new designs to evaluate next.\n"
        "Rules:\n"
        "- Reply with ONE JSON object matching `response_schema`. No other text.\n"
        "- Every proposal names a `parent_id`: the `id` of a design in the tables below. "
        "It inherits the parent's variable values; `parameter_changes` lists the variables "
        "you change, as NEW ABSOLUTE VALUES (not deltas).\n"
        "- Values must lie inside [min, max] of `design_variables`. Out-of-range, "
        "malformed or duplicate proposals are rejected and the evaluation slot is lost; "
        "nothing is clipped or repaired for you.\n"
        "- `expected_outcome` is your numeric prediction of both objectives and of "
        "feasibility for that design. It will be scored against the simulator.\n"
        "- `requested_fidelity`: 0 = this reduced-order simulator, 1 = you think this "
        "design deserves a higher-fidelity check.\n"
        "- `observation`, `evidence`, `mechanism`, `uncertainty` describe what you see in "
        "the data, which rows support it (cite ids), the physical mechanism you believe "
        "explains it, and what you are unsure of.\n\n"
        "DATA:\n")
    return instructions + json.dumps(payload, indent=1, sort_keys=False)


# ---------------------------------------------------------------------------------------
# LLM clients
# ---------------------------------------------------------------------------------------
class LLMCallLimit(RuntimeError):
    """The hard cap on LLM calls (per run or for the whole study) has been reached."""


class CallBudget:
    """Thread-safe counter enforcing the study-wide cap on live LLM calls."""

    def __init__(self, max_calls: int):
        self.max_calls, self.used = int(max_calls), 0
        self._lock = threading.Lock()

    def take(self) -> None:
        with self._lock:
            if self.used >= self.max_calls:
                raise LLMCallLimit(f"study-wide cap of {self.max_calls} LLM calls reached")
            self.used += 1


@dataclass
class LLMResult:
    text: str | None                    # the model's answer, None if the call failed
    meta: dict[str, Any] = field(default_factory=dict)


class LLMClient(Protocol):
    calls_made: int
    max_calls: int

    def complete(self, prompt: str) -> LLMResult: ...


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _extract(raw_stdout: str) -> tuple[str | None, dict[str, Any]]:
    """Answer text and usage metadata from the CLI's `--output-format json` envelope."""
    try:
        envelope = json.loads(raw_stdout)
    except json.JSONDecodeError:
        return None, {"error": "CLI output is not JSON"}
    if not isinstance(envelope, dict):
        return None, {"error": "CLI output is not a JSON object"}
    usage = envelope.get("usage") if isinstance(envelope.get("usage"), dict) else {}
    models = envelope.get("modelUsage") if isinstance(envelope.get("modelUsage"), dict) else {}
    meta = {
        "models": sorted(str(name) for name in models),
        "input_tokens": int(usage.get("input_tokens") or 0)
        + int(usage.get("cache_creation_input_tokens") or 0)
        + int(usage.get("cache_read_input_tokens") or 0),
        "output_tokens": int(usage.get("output_tokens") or 0),
        "api_duration_s": float(envelope.get("duration_api_ms") or 0.0) / 1000.0,
        "cost_usd_list_price": float(envelope.get("total_cost_usd") or 0.0),
    }
    result = envelope.get("result")
    if envelope.get("is_error") or not isinstance(result, str):
        meta["error"] = f"CLI reported an error (subtype {envelope.get('subtype')!r})"
        return None, meta
    return result, meta


class _PersistingClient:
    """Shared bookkeeping: numbered prompt/response files plus a `calls.jsonl` index."""

    def __init__(self, log_dir: Path, max_calls: int):
        self.log_dir, self.max_calls = Path(log_dir), int(max_calls)
        self.calls_made = 0

    def _paths(self, number: int) -> tuple[Path, Path]:
        return (self.log_dir / f"call_{number:02d}.prompt.txt",
                self.log_dir / f"call_{number:02d}.response.raw")


class ClaudeCLIClient(_PersistingClient):
    """Live calls: `claude -p --output-format json --model <model>`, prompt on stdin."""

    def __init__(self, log_dir: Path, *, model: str, max_calls: int, timeout_s: float,
                 study_budget: CallBudget, executable: str = "claude"):
        super().__init__(log_dir, max_calls)
        self.model, self.timeout_s = model, float(timeout_s)
        self.study_budget, self.executable = study_budget, executable
        self.log_dir.mkdir(parents=True, exist_ok=True)
        (self.log_dir / "system_prompt.txt").write_text(SYSTEM_PROMPT)

    def complete(self, prompt: str) -> LLMResult:
        if self.calls_made >= self.max_calls:
            raise LLMCallLimit(f"per-run cap of {self.max_calls} LLM calls reached")
        self.study_budget.take()
        self.calls_made += 1
        prompt_path, response_path = self._paths(self.calls_made)
        prompt_path.write_text(prompt)
        command = [self.executable, "-p", "--output-format", "json", "--model", self.model,
                   "--safe-mode", "--tools", "", "--strict-mcp-config",
                   "--no-session-persistence", "--disable-slash-commands",
                   "--system-prompt", SYSTEM_PROMPT]
        start = time.perf_counter()
        stdout, error, returncode = "", None, None
        with tempfile.TemporaryDirectory(prefix="aether-llm-") as empty_cwd:
            try:
                done = subprocess.run(command, input=prompt, capture_output=True, text=True,
                                      timeout=self.timeout_s, cwd=empty_cwd, check=False)
                stdout, returncode = done.stdout, done.returncode
                if returncode != 0:
                    error = f"CLI exited {returncode}: {done.stderr.strip()[:500]}"
            except subprocess.TimeoutExpired:
                error = f"timed out after {self.timeout_s:g} s"
            except OSError as exc:
                error = f"could not run '{self.executable}': {exc}"
        wall = time.perf_counter() - start
        response_path.write_text(stdout)
        text, meta = (None, {}) if error else _extract(stdout)
        meta = {"call": self.calls_made, "prompt_sha256": _sha256(prompt),
                "model_requested": self.model, "wall_s": wall, "returncode": returncode,
                **meta}
        if error:
            meta["error"] = error
        with open(self.log_dir / "calls.jsonl", "a") as fh:
            fh.write(json.dumps(meta) + "\n")
        return LLMResult(text=text if "error" not in meta else None, meta=meta)


class ReplayClient(_PersistingClient):
    """Serves the persisted responses of an earlier run, in order, and makes no call.

    Each prompt is compared with the one recorded for the same call number. With
    `strict=True` a difference raises; otherwise it is counted in `prompt_mismatches` and
    the recorded response is still used - the run then reproduces the agent's DECISIONS
    but is no longer a byte-for-byte replay, and the report says so.
    """

    def __init__(self, log_dir: Path, *, max_calls: int, strict: bool = False):
        super().__init__(log_dir, max_calls)
        self.strict, self.prompt_mismatches = bool(strict), 0
        index = self.log_dir / "calls.jsonl"
        if not index.exists():
            raise FileNotFoundError(f"no recorded LLM calls to replay under {self.log_dir}")
        self._recorded = [json.loads(line) for line in index.read_text().splitlines() if line]

    def complete(self, prompt: str) -> LLMResult:
        if self.calls_made >= min(self.max_calls, len(self._recorded)):
            raise LLMCallLimit(f"replay log under {self.log_dir} holds "
                               f"{len(self._recorded)} calls; no more to serve")
        self.calls_made += 1
        meta = dict(self._recorded[self.calls_made - 1])
        if meta.get("prompt_sha256") != _sha256(prompt):
            self.prompt_mismatches += 1
            if self.strict:
                raise ValueError(f"replay call {self.calls_made} under {self.log_dir}: the "
                                 "regenerated prompt differs from the recorded one")
        meta["replayed"] = True
        if meta.get("error"):
            return LLMResult(text=None, meta=meta)
        text, _ = _extract(self._paths(self.calls_made)[1].read_text())
        return LLMResult(text=text, meta=meta)


# ---------------------------------------------------------------------------------------
# The optimiser
# ---------------------------------------------------------------------------------------
@dataclass
class AgentLog:
    """Everything about the agent's behaviour that is not a candidate row."""

    rounds: list[dict[str, Any]] = field(default_factory=list)
    proposals: list[dict[str, Any]] = field(default_factory=list)
    rejections: list[dict[str, Any]] = field(default_factory=list)
    fidelity_decisions: list[dict[str, Any]] = field(default_factory=list)
    fallback_evaluations: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _hypervolume(rows, objectives, hv_cfg) -> float:
    ideal = np.array([hv_cfg["ideal_point"][name] for name in objectives], dtype=float)
    ref = np.array([hv_cfg["reference_point"][name] for name in objectives], dtype=float)
    feasible = [row for row in rows if row["feasible"]]
    if not feasible:
        return 0.0
    return normalised_hypervolume(
        np.array([[row[name] for name in objectives] for row in feasible], dtype=float),
        ideal, ref)


def run_ai_agent(evaluator: BudgetedEvaluator, settings: dict[str, Any],
                 objectives: tuple[str, ...], hv_cfg: dict[str, Any], *, client: LLMClient,
                 log: AgentLog, policy: PromotionPolicy | None = None) -> None:
    """LLM-in-the-loop search. With `policy` it is the 'AI + adaptive fidelity' method:
    identical search, plus a promotion decision per accepted proposal (see fidelity.py)."""
    space, k = evaluator.space, evaluator.space.n_active
    active = space.active
    bounds = {v.name: (v.lower, v.upper) for v in space.active_variables}
    planned_rounds = int(settings["rounds"])
    max_batch = int(settings["max_proposals_per_call"])
    rows: list[dict[str, Any]] = []
    history: list[dict[str, Any]] = []

    def values_of(row: dict[str, Any]) -> dict[str, float]:
        return {name: float(row[f"x__{name}"]) for name in active}

    try:
        init = latin_hypercube(min(initial_design_size(settings, k), evaluator.budget), k,
                               evaluator.seed)
        rows += evaluator.evaluate(space.from_unit(init), generation=0)
        successful = 0
        while evaluator.remaining > 0 and client.calls_made < client.max_calls:
            rounds_left = max(planned_rounds - successful, 1)
            quota = min(max_batch, math.ceil(evaluator.remaining / rounds_left))
            prompt = build_prompt(rows, evaluator, objectives, hv_cfg, quota=quota,
                                  rounds_left=rounds_left, history=history,
                                  table_sizes=settings["tables"])
            try:
                result = client.complete(prompt)
            except LLMCallLimit:
                break
            entry: dict[str, Any] = {
                "method": evaluator.method, "seed": evaluator.seed,
                "call": client.calls_made, "quota": quota,
                "budget_spent_before": evaluator.used, **result.meta}
            if result.text is None:
                entry["outcome"] = "call_failed"
                log.rounds.append(entry)
                continue
            try:
                response = parse_response(result.text)
            except MalformedResponse as exc:
                entry.update({"outcome": "malformed_response", "detail": str(exc)})
                log.rounds.append(entry)
                continue
            parents = {row["candidate_id"]: values_of(row) for row in rows}
            seen = {tuple(v[name] for name in active) for v in parents.values()}
            accepted, rejected = validate_proposals(
                response, bounds=bounds, objectives=objectives, parents=parents,
                seen_keys=seen, quota=quota)
            for item in rejected:
                log.rejections.append({"method": evaluator.method, "seed": evaluator.seed,
                                       "call": client.calls_made, **item})
            entry.update({
                "outcome": "ok", "n_proposed": len(response["proposals"]),
                "n_accepted": len(accepted), "n_rejected": len(rejected),
                "observation": response["observation"], "evidence": response["evidence"],
                "mechanism": response["mechanism"], "uncertainty": response["uncertainty"]})
            hv_before = _hypervolume(rows, objectives, hv_cfg)
            new_rows: list[dict[str, Any]] = []
            if accepted:
                x_batch = np.array([[p.values[name] for name in active] for p in accepted])
                ids = [evaluator.candidate_id(space.values(x)) for x in x_batch]
                if policy is not None:
                    surrogate = None
                    if sum(has_physics(r) for r in rows) >= MIN_TRAINING_ROWS:
                        surrogate = DesignSurrogate(
                            space, objectives, seed=evaluator.seed,
                            transforms=settings.get("transforms")).fit(rows)
                    for decision in policy.decide_batch(
                            x_batch, ids, [p.requested_fidelity for p in accepted], rows,
                            surrogate, space, objectives, hv_cfg):
                        log.fidelity_decisions.append({"method": evaluator.method,
                                                       "seed": evaluator.seed,
                                                       "call": client.calls_made,
                                                       **decision.to_dict()})
                for proposal, cid in zip(accepted, ids, strict=True):
                    log.proposals.append({"method": evaluator.method, "seed": evaluator.seed,
                                          "call": client.calls_made, "candidate_id": cid,
                                          **asdict(proposal)})
                try:
                    new_rows = evaluator.evaluate(
                        x_batch, generation=client.calls_made,
                        parent_ids=[[p.parent_id] for p in accepted])
                except BudgetExhausted:
                    # cannot happen while quota <= remaining, but if it ever does the
                    # round must not vanish from the audit trail
                    entry["outcome"] = "budget_exhausted_mid_batch"
                    log.rounds.append(entry)
                    raise
                rows += new_rows
            successful += 1
            hv_after = _hypervolume(rows, objectives, hv_cfg)
            entry.update({"hv_before": hv_before, "hv_after": hv_after,
                          "n_feasible_new": sum(r["feasible"] for r in new_rows)})
            log.rounds.append(entry)
            history.append({
                "round": successful, "mechanism": response["mechanism"][:400],
                "n_accepted": len(accepted), "n_rejected": len(rejected),
                "n_feasible_new": entry["n_feasible_new"],
                "n_no_geometry_new": sum(not has_physics(r) for r in new_rows),
                "hypervolume_before": _sig(hv_before, 6),
                "hypervolume_after": _sig(hv_after, 6)})
        if evaluator.remaining > 0:
            # The agent ran out of calls with budget left (rejections, failed calls). The
            # budget must still be matched, so the remainder is spent on the LHS floor and
            # reported as such - it is the agent's loss, not hidden.
            log.fallback_evaluations += evaluator.remaining
            fill = latin_hypercube(evaluator.remaining, k, evaluator.seed + 1)
            evaluator.evaluate(space.from_unit(fill), generation=_FALLBACK_GENERATION)
    except BudgetExhausted:
        pass
