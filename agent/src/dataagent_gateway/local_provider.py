"""Local llama.cpp OpenAI-compatible provider for the pinned dsh Harness.

This module only discovers and configures a *local* model. All actual Agent
planning, tool calls, MCP access and Guard enforcement remain in dsh.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

import httpx

PROVIDER_ID = "local-llama"
API_KEY_ENV = "DATACONTROL_LOCAL_MODEL_API_KEY"
DEFAULT_BASE_URL = "http://127.0.0.1:9931/v1"
ROOT = Path(__file__).resolve().parents[3]


class LocalModelError(RuntimeError):
    pass


@dataclass(frozen=True)
class LocalModel:
    id: str
    base_url: str

    @property
    def identity(self) -> str:
        return hashlib.sha256((self.base_url + "\n" + self.id).encode()).hexdigest()[:12]


def validated_base_url(raw: str | None = None) -> str:
    raw = (raw if raw is not None else os.getenv("DATACONTROL_LOCAL_MODEL_BASE_URL", DEFAULT_BASE_URL)).strip().rstrip("/")
    url = urlsplit(raw)
    if (url.scheme != "http" or url.hostname not in {"127.0.0.1", "localhost", "::1"}
            or url.username or url.password or url.query or url.fragment
            or url.path != "/v1" or not url.port):
        raise LocalModelError("Local model URL must be http://127.0.0.1:<port>/v1 (loopback only)")
    return raw


def discover_local_model(*, base_url: str | None = None, requested_id: str | None = None,
                         timeout: float = 4.0) -> LocalModel:
    base_url = validated_base_url(base_url)
    try:
        with httpx.Client(trust_env=False, timeout=timeout) as client:
            response = client.get(base_url + "/models")
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise LocalModelError(f"Local llama.cpp /v1/models unreachable: {type(exc).__name__}") from exc
    raw_models = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(raw_models, list):
        raise LocalModelError("Local /v1/models did not return a data array")
    ids = [str(item["id"]) for item in raw_models if isinstance(item, dict)
           and isinstance(item.get("id"), str) and item["id"].strip()
           and len(item["id"]) <= 200 and all(ord(c) >= 32 for c in item["id"])]
    ids = list(dict.fromkeys(ids))
    selected = requested_id if requested_id is not None else os.getenv("DATACONTROL_LOCAL_MODEL_ID", "").strip()
    if selected and selected not in ids:
        raise LocalModelError("Configured DATACONTROL_LOCAL_MODEL_ID does not match /v1/models")
    if not selected:
        if not ids:
            raise LocalModelError("Local /v1/models returned no model ID")
        if len(ids) != 1:
            raise LocalModelError("Multiple local models detected; set DATACONTROL_LOCAL_MODEL_ID to an exact /v1/models ID")
        selected = ids[0]
    return LocalModel(id=selected, base_url=base_url)


def _positive_int(name: str, fallback: int, minimum: int) -> int:
    try:
        value = int(os.getenv(name, str(fallback)))
    except ValueError as exc:
        raise LocalModelError(name + " must be an integer") from exc
    if not minimum <= value <= 262144:
        raise LocalModelError(name + " is outside the allowed range")
    return value


def render_local_overlay(source: str, model: LocalModel) -> str:
    """Generate a native dsh Headless profile; don't fork the Agent pipeline."""
    old = "    provider: deepseek-official\n    model: deepseek-flash"
    if source.count(old) != 1:
        raise LocalModelError("Headless profile provider anchor has changed")
    context = _positive_int("DATACONTROL_LOCAL_CONTEXT_WINDOW", 8192, 2048)
    tokens = _positive_int("DATACONTROL_LOCAL_MAX_TOKENS", 2048, 128)
    if tokens >= context:
        raise LocalModelError("Local max output tokens must be smaller than context window")
    # JSON quoting is valid YAML scalar syntax and safe for model names with spaces.
    plugin = (
        "- id: llm-pi-ai\n"
        "  config:\n"
        "    providers:\n"
        f"      {PROVIDER_ID}:\n"
        f"        apiKeyEnv: {API_KEY_ENV}\n"
        "        api: openai-completions\n"
        f"        baseURL: {json.dumps(model.base_url)}\n"
        "        compat:\n"
        "          supportsDeveloperRole: false\n"
        "          maxTokensField: max_tokens\n"
        "        models:\n"
        f"          - id: {json.dumps(model.id, ensure_ascii=False)}\n"
        "            name: Local DeepSeek (llama.cpp)\n"
        f"            contextWindow: {context}\n"
        f"            maxTokens: {tokens}\n"
        "            input: [text]\n\n"
    )
    return source.replace(old, f"    provider: {PROVIDER_ID}\n    model: {json.dumps(model.id, ensure_ascii=False)}", 1).replace(
        "- id: agent-default-model\n", plugin + "- id: agent-default-model\n", 1
    )


def source_profile(task_tier: str) -> Path:
    if task_tier not in {"standard", "multi"}:
        raise LocalModelError("Unknown task tier")
    filename = "headless-multi.patch.yml" if task_tier == "multi" else "headless.patch.yml"
    return ROOT / "agent" / "dsh" / "profile" / filename


def expected_overlay(task_tier: str, model: LocalModel) -> str:
    return render_local_overlay(source_profile(task_tier).read_text(encoding="utf-8"), model)


def profile_name(task_tier: str) -> str:
    return "dataagent-headless-local-multi" if task_tier == "multi" else "dataagent-headless-local"


def profile_is_current(profile_dir: Path, task_tier: str, model: LocalModel) -> bool:
    patch = profile_dir / "cordis.patch.yml"
    return (
        (profile_dir / "package.json").is_file()
        and patch.is_file()
        and patch.read_text(encoding="utf-8") == expected_overlay(task_tier, model)
    )


def main() -> int:
    cli = argparse.ArgumentParser(description="Configure the loopback llama.cpp provider")
    cli.add_argument("action", choices=["probe", "write-profile", "check-profile"])
    cli.add_argument("--profile-dir", type=Path)
    cli.add_argument("--task-tier", choices=["standard", "multi"], default="standard")
    args = cli.parse_args()
    try:
        model = discover_local_model()
        if args.action == "probe":
            print(json.dumps({"ready": True, "model": model.id, "baseURL": model.base_url}, ensure_ascii=False))
        elif args.action == "write-profile":
            if not args.profile_dir or not (args.profile_dir / "package.json").exists():
                raise LocalModelError("Create a dsh headless profile before writing the overlay")
            patch = args.profile_dir / "cordis.patch.yml"
            patch.write_text(expected_overlay(args.task_tier, model), encoding="utf-8")
            print(f"Local {args.task_tier} profile configured for model {model.id}")
        else:
            if not args.profile_dir or not profile_is_current(args.profile_dir, args.task_tier, model):
                raise LocalModelError("Local dsh profile is missing or stale; run scripts/setup-local-model.ps1")
            print("Local model profile matches the running llama.cpp model")
        return 0
    except (LocalModelError, OSError) as exc:
        print("LOCAL_MODEL: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
