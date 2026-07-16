"""Validate and gate first-party GPU/HBM runtime snapshots.

This module deliberately performs no network requests. The skill retrieves official
pages, records the final URLs and evidence in a candidate JSON file, and this module
provides deterministic validation, atomic persistence, and single-run authorization.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
import tempfile
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse


ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_RUNTIME_DIR = ROOT_DIR / "output" / "runtime"
REQUIRED_MODULES = {
    "gpu_specs": "fact",
    "nvda_compute_revenue": "fact",
    "gpu_shipments": "estimate",
    "gpu_mix": "estimate",
    "hbm_supply": "estimate",
}
ALLOWED_DOMAIN_ROOTS = (
    "nvidia.com",
    "nvidia.cn",
    "sec.gov",
    "micron.com",
    "micron.cn",
    "skhynix.com",
    "skhynix.com.cn",
    "samsung.com",
    "tsmc.com",
)
SOURCE_FIELDS = {
    "publisher",
    "title",
    "url",
    "region",
    "language",
    "source_type",
    "as_of",
    "accessed_at",
    "verified_at",
    "retrieved_this_run",
    "evidence",
}
ESTIMATE_FIELDS = {"inputs", "formula", "assumptions", "limitations", "confidence"}
AUTHORITY_PRIORITY = {
    "regulatory": 5,
    "company_ir": 4,
    "product_datasheet": 3,
    "company_news": 2,
    "regional_product_page": 1,
}
SUPPORTED_TICKERS = {"MU", "SNDK", "WDC", "STX"}
MANIFEST_LIFETIME = timedelta(hours=2)


class SnapshotValidationError(ValueError):
    """A public-data snapshot failed deterministic validation."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        super().__init__(f"{code}: {detail}" if detail else code)


class RunManifestError(ValueError):
    """A run manifest cannot authorize analysis."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        super().__init__(f"{code}: {detail}" if detail else code)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_datetime(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise SnapshotValidationError("invalid_date", field)
    normalized = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise SnapshotValidationError("invalid_date", field) from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _format_datetime(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def host_is_allowed(host: str | None) -> bool:
    """Return true only for an allowlisted root or its dot-boundary subdomain."""
    if not host:
        return False
    normalized = host.rstrip(".").lower()
    return any(
        normalized == root or normalized.endswith("." + root)
        for root in ALLOWED_DOMAIN_ROOTS
    )


def _validate_url(url: Any, field: str) -> None:
    if not isinstance(url, str):
        raise SnapshotValidationError("source_url", field)
    parsed = urlparse(url)
    if parsed.scheme != "https" or not host_is_allowed(parsed.hostname):
        raise SnapshotValidationError("source_domain", field)


def validate_source(source: Any, now: datetime) -> dict[str, Any]:
    if not isinstance(source, dict):
        raise SnapshotValidationError("source_type", "source must be an object")
    missing = SOURCE_FIELDS - set(source)
    if missing:
        raise SnapshotValidationError("source_fields", ",".join(sorted(missing)))
    for field in ("publisher", "title", "region", "language", "source_type", "as_of", "evidence"):
        if not isinstance(source.get(field), str) or not source[field].strip():
            raise SnapshotValidationError("source_fields", field)
    _validate_url(source["url"], "url")
    _validate_url(source.get("final_url", source["url"]), "final_url")
    if source.get("retrieved_this_run") is not True:
        raise SnapshotValidationError("not_retrieved", source["title"])
    if source.get("published_at") is not None:
        _parse_datetime(source["published_at"], "published_at")
    _parse_datetime(source["accessed_at"], "accessed_at")
    verified = _parse_datetime(source["verified_at"], "verified_at")
    if verified > now + timedelta(minutes=5):
        raise SnapshotValidationError("future_verification", source["title"])
    return copy.deepcopy(source)


def _validate_range_objects(value: Any, path: str = "data") -> None:
    if isinstance(value, dict):
        if {"low", "base", "high"}.issubset(value):
            low, base, high = value["low"], value["base"], value["high"]
            if not all(isinstance(item, (int, float)) and not isinstance(item, bool) for item in (low, base, high)):
                raise SnapshotValidationError("estimate_range", path)
            if not low <= base <= high:
                raise SnapshotValidationError("estimate_range", path)
        for key, child in value.items():
            _validate_range_objects(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _validate_range_objects(child, f"{path}[{index}]")


def _validate_gpu_mix(module: dict[str, Any]) -> None:
    ratios = module.get("data", {}).get("ratios")
    if not isinstance(ratios, dict) or not ratios:
        raise SnapshotValidationError("gpu_mix_ratio", "ratios missing")
    for period, values in ratios.items():
        if not isinstance(values, dict) or not values:
            raise SnapshotValidationError("gpu_mix_ratio", str(period))
        if any(not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0 or value > 1 for value in values.values()):
            raise SnapshotValidationError("gpu_mix_ratio", str(period))
        if abs(sum(values.values()) - 1.0) > 0.001:
            raise SnapshotValidationError("gpu_mix_ratio", str(period))


def validate_snapshot(candidate: Any, previous: dict[str, Any] | None = None,
                      now: datetime | None = None) -> dict[str, Any]:
    """Validate a complete five-module candidate and return a defensive copy."""
    now = (now or _utc_now()).astimezone(timezone.utc)
    if not isinstance(candidate, dict):
        raise SnapshotValidationError("snapshot_type")
    if candidate.get("schema_version") != 1:
        raise SnapshotValidationError("schema_version")
    if not isinstance(candidate.get("refresh_id"), str) or not re.fullmatch(r"[A-Za-z0-9._-]+", candidate["refresh_id"]):
        raise SnapshotValidationError("refresh_id")
    _parse_datetime(candidate.get("created_at"), "created_at")
    modules = candidate.get("modules")
    if not isinstance(modules, dict):
        raise SnapshotValidationError("modules_type")
    missing = set(REQUIRED_MODULES) - set(modules)
    if missing:
        raise SnapshotValidationError("missing_modules", ",".join(sorted(missing)))

    for name, expected_kind in REQUIRED_MODULES.items():
        module = modules[name]
        if not isinstance(module, dict):
            raise SnapshotValidationError("module_type", name)
        if module.get("status") != "fresh" or module.get("kind") != expected_kind:
            raise SnapshotValidationError("module_status", name)
        if not isinstance(module.get("data"), dict) or not module["data"]:
            raise SnapshotValidationError("module_data", name)
        sources = module.get("sources")
        if not isinstance(sources, list) or not sources:
            raise SnapshotValidationError("module_sources", name)
        for source in sources:
            validate_source(source, now)
        if any(item.get("status") == "unresolved" for item in module.get("conflicts", [])):
            raise SnapshotValidationError("source_conflict", name)

        if expected_kind == "estimate":
            missing_estimate = ESTIMATE_FIELDS - set(module)
            if missing_estimate:
                raise SnapshotValidationError("estimate_contract", f"{name}:{','.join(sorted(missing_estimate))}")
            if not isinstance(module["inputs"], dict) or not module["inputs"]:
                raise SnapshotValidationError("estimate_contract", f"{name}:inputs")
            if not isinstance(module["formula"], str) or not module["formula"].strip():
                raise SnapshotValidationError("estimate_contract", f"{name}:formula")
            if not isinstance(module["assumptions"], list) or not module["assumptions"]:
                raise SnapshotValidationError("estimate_contract", f"{name}:assumptions")
            if not isinstance(module["limitations"], list) or not module["limitations"]:
                raise SnapshotValidationError("estimate_contract", f"{name}:limitations")
            if module["confidence"] not in {"low", "medium", "high"}:
                raise SnapshotValidationError("estimate_contract", f"{name}:confidence")
            _validate_range_objects(module["data"], name)
        elif any(field in module for field in ("formula", "assumptions", "limitations", "confidence")):
            raise SnapshotValidationError("fact_contains_estimate", name)

        if module.get("single_source"):
            if name != "gpu_specs" or expected_kind != "fact" or len(sources) != 1:
                raise SnapshotValidationError("single_source_invalid", name)

    _validate_gpu_mix(modules["gpu_mix"])
    return copy.deepcopy(candidate)


def _period_key(value: Any) -> tuple[int, int, str]:
    text = str(value or "")
    match = re.match(r"^(\d{4})-Q([1-4])$", text)
    if match:
        return int(match.group(1)), int(match.group(2)), text
    match = re.match(r"^(\d{4})-(\d{2})-(\d{2})", text)
    if match:
        return int(match.group(1)), int(match.group(2)), text
    match = re.match(r"^(\d{4})", text)
    if match:
        return int(match.group(1)), 0, text
    return 0, 0, text


def select_latest_sources(sources: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort reachable official sources by period, publication date and authority."""
    return sorted(
        (copy.deepcopy(source) for source in sources),
        key=lambda source: (
            _period_key(source.get("as_of")),
            str(source.get("published_at") or ""),
            AUTHORITY_PRIORITY.get(str(source.get("source_type")), 0),
        ),
        reverse=True,
    )


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", newline="\n", delete=False, dir=path.parent,
        prefix=path.name + ".", suffix=".tmp"
    )
    temp_path = Path(handle.name)
    try:
        with handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def _read_json(path: Path, error_type: type[ValueError], missing_code: str) -> dict[str, Any]:
    if not path.is_file():
        raise error_type(missing_code)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise error_type("invalid_json", path.name) from exc
    if not isinstance(payload, dict):
        raise error_type("invalid_json", path.name)
    return payload


def _create_manifest(snapshot: dict[str, Any], ticker: str, mode: str,
                     now: datetime, failed_refresh_id: str | None = None,
                     failed_modules: list[str] | None = None) -> dict[str, Any]:
    ticker = ticker.upper()
    if ticker not in SUPPORTED_TICKERS:
        raise RunManifestError("unsupported_ticker", ticker)
    refresh_id = failed_refresh_id or snapshot["refresh_id"]
    return {
        "schema_version": 1,
        "refresh_id": refresh_id,
        "snapshot_refresh_id": snapshot["refresh_id"],
        "ticker": ticker,
        "mode": mode,
        "snapshot_file": "industry_snapshot.json",
        "created_at": _format_datetime(now),
        "expires_at": _format_datetime(now + MANIFEST_LIFETIME),
        "failed_modules": list(failed_modules or []),
    }


def promote_snapshot(candidate: dict[str, Any], runtime_dir: str | Path,
                     ticker: str, now: datetime | None = None) -> dict[str, Any]:
    """Validate, atomically promote, preserve prior data, and authorize one fresh run."""
    now = (now or _utc_now()).astimezone(timezone.utc)
    validated = validate_snapshot(candidate, now=now)
    runtime = Path(runtime_dir)
    current_path = runtime / "industry_snapshot.json"
    previous_path = runtime / "industry_snapshot.previous.json"
    old_payload = current_path.read_bytes() if current_path.is_file() else None
    if old_payload is not None:
        previous_path.parent.mkdir(parents=True, exist_ok=True)
        temp_previous = previous_path.with_suffix(previous_path.suffix + ".tmp")
        temp_previous.write_bytes(old_payload)
        os.replace(temp_previous, previous_path)
    _atomic_write_json(current_path, validated)
    manifest = _create_manifest(validated, ticker, "fresh", now)
    _atomic_write_json(runtime / "industry_run.json", manifest)
    return manifest


def precheck_run_manifest(manifest_path: str | Path, ticker: str,
                          now: datetime | None = None) -> dict[str, Any]:
    now = (now or _utc_now()).astimezone(timezone.utc)
    path = Path(manifest_path)
    manifest = _read_json(path, RunManifestError, "manifest_missing")
    if manifest.get("schema_version") != 1:
        raise RunManifestError("manifest_schema")
    if manifest.get("ticker") != ticker.upper():
        raise RunManifestError("ticker_mismatch")
    if manifest.get("mode") not in {"fresh", "cached-authorized"}:
        raise RunManifestError("manifest_mode")
    try:
        expires = _parse_datetime(manifest.get("expires_at"), "expires_at")
    except SnapshotValidationError as exc:
        raise RunManifestError("manifest_expiry") from exc
    if expires < now:
        raise RunManifestError("manifest_expired")
    snapshot_path = path.parent / str(manifest.get("snapshot_file", ""))
    snapshot = _read_json(snapshot_path, RunManifestError, "snapshot_missing")
    try:
        validate_snapshot(snapshot, now=now)
    except SnapshotValidationError as exc:
        raise RunManifestError("snapshot_invalid", exc.code) from exc
    if snapshot.get("refresh_id") != manifest.get("snapshot_refresh_id"):
        raise RunManifestError("snapshot_mismatch")
    result = copy.deepcopy(manifest)
    result["snapshot_path"] = str(snapshot_path.resolve())
    result["snapshot"] = snapshot
    return result


def claim_run_manifest(manifest_path: str | Path, ticker: str,
                       now: datetime | None = None) -> dict[str, Any]:
    """Consume a valid manifest so it cannot authorize another analysis."""
    path = Path(manifest_path)
    result = precheck_run_manifest(path, ticker, now=now)
    claimed_path = path.with_name(f"industry_run.{result['refresh_id']}.claimed.json")
    os.replace(path, claimed_path)
    result["claimed_manifest_path"] = str(claimed_path.resolve())
    return result


def authorize_current_snapshot(runtime_dir: str | Path, failed_refresh_id: str,
                               ticker: str, failed_modules: list[str],
                               now: datetime | None = None) -> dict[str, Any]:
    """Create a one-run cached authorization after explicit chat approval."""
    now = (now or _utc_now()).astimezone(timezone.utc)
    runtime = Path(runtime_dir)
    snapshot = _read_json(runtime / "industry_snapshot.json", RunManifestError, "snapshot_missing")
    try:
        validate_snapshot(snapshot, now=now)
    except SnapshotValidationError as exc:
        raise RunManifestError("snapshot_invalid", exc.code) from exc
    if not failed_refresh_id.strip() or not failed_modules:
        raise RunManifestError("authorization_context")
    unknown = set(failed_modules) - set(REQUIRED_MODULES)
    if unknown:
        raise RunManifestError("failed_modules", ",".join(sorted(unknown)))
    manifest = _create_manifest(
        snapshot, ticker, "cached-authorized", now,
        failed_refresh_id=failed_refresh_id, failed_modules=failed_modules,
    )
    _atomic_write_json(runtime / "industry_run.json", manifest)
    return manifest


def apply_runtime_snapshot(base: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
    """Overlay only the five GPU/HBM runtime modules onto a copied static config."""
    result = copy.deepcopy(base)
    modules = snapshot["modules"]
    specs_data = modules["gpu_specs"]["data"]
    revenue_data = modules["nvda_compute_revenue"]["data"]
    shipment_data = modules["gpu_shipments"]["data"]
    mix_data = modules["gpu_mix"]["data"]
    supply_data = modules["hbm_supply"]["data"]
    verified_values = [
        source["verified_at"]
        for module in modules.values()
        for source in module.get("sources", [])
    ]
    runtime_specs = {
        "_note": "Runtime snapshot verified from official sources",
        "_last_updated": max(verified_values) if verified_values else snapshot["created_at"],
        "generations": copy.deepcopy(specs_data["generations"]),
        "nvda_quarterly_revenue": {
            "_note": "Official Compute revenue; legacy model unit: USD 100 millions",
            **{
                period: float(value) * 10
                for period, value in revenue_data["quarterly_revenue_b_usd"].items()
            },
        },
        "asp_per_gpu_k_usd": {
            "_note": "Model assumption; unit: USD thousands",
            **copy.deepcopy(shipment_data["asp_per_gpu_k_usd"]),
        },
        "quarterly_gpu_shipments_k": copy.deepcopy(shipment_data.get("quarterly_shipments_k", {})),
        "gpu_mix_ratios": {
            "_note": "Model estimate; ratios sum to one",
            **copy.deepcopy(mix_data["ratios"]),
        },
        "hbm_supply_params": {
            "_note": "Model estimate anchored to official supplier disclosures",
            **copy.deepcopy(supply_data["parameters"]),
        },
        "_runtime_snapshot": {
            "refresh_id": snapshot["refresh_id"],
            "modules": copy.deepcopy(modules),
        },
    }
    result["gpu_hbm_specs"] = runtime_specs
    return result


def build_industry_snapshot_html(snapshot: dict[str, Any], run_mode: str) -> str:
    """Render escaped, traceable runtime-source metadata for the HTML report."""
    labels = {
        "gpu_specs": "GPU / HBM 规格",
        "nvda_compute_revenue": "NVIDIA Compute 营收",
        "gpu_shipments": "GPU 出货量",
        "gpu_mix": "GPU 型号占比",
        "hbm_supply": "HBM 供给",
    }
    warning = ""
    if run_mode == "cached-authorized":
        warning = (
            "<div style='background:#4a1f1f;border:2px solid #ff7043;padding:12px;"
            "border-radius:8px;margin-bottom:12px;color:#fff3e0;'>"
            "<b>⚠️ 本次使用上一份行业数据</b>：用户已明确授权本轮继续；"
            "相关结论不代表已由最新资料验证。</div>"
        )
    rows = []
    for key, module in snapshot.get("modules", {}).items():
        kind = module.get("kind")
        kind_label = "事实" if kind == "fact" else "模型估算"
        sources = []
        for source in module.get("sources", []):
            url = escape(str(source.get("final_url") or source.get("url") or ""), quote=True)
            title = escape(str(source.get("title") or source.get("publisher") or "官方来源"))
            source_link = f"<a href='{url}' target='_blank' rel='noopener noreferrer'>{title}</a>"
            sources.append(
                f"{source_link}；published_at={escape(str(source.get('published_at')))}；"
                f"as_of={escape(str(source.get('as_of')))}；"
                f"verified_at={escape(str(source.get('verified_at')))}"
            )
        estimate_detail = ""
        if kind == "estimate":
            assumptions = "；".join(escape(str(value)) for value in module.get("assumptions", []))
            limitations = "；".join(escape(str(value)) for value in module.get("limitations", []))
            estimate_detail = (
                f"<div><b>公式：</b>{escape(str(module.get('formula', '')))}</div>"
                f"<div><b>模型假设：</b>{assumptions}</div>"
                f"<div><b>局限：</b>{limitations}</div>"
                f"<div><b>置信度：</b>{escape(str(module.get('confidence', 'unknown')))}</div>"
            )
        rows.append(
            "<div style='border-bottom:1px solid #2a3a4a;padding:8px 0;'>"
            f"<div><b>{escape(labels.get(key, key))}</b> "
            f"<span style='color:{'#81c784' if kind == 'fact' else '#ffb74d'}'>[{kind_label}]</span></div>"
            f"<div>{'<br>'.join(sources)}</div>{estimate_detail}</div>"
        )
    status = "本轮已核验" if run_mode == "fresh" else "经授权使用旧快照"
    return (
        warning
        + "<details open style='background:#17202b;border:1px solid #2a3a4a;border-radius:8px;"
        "padding:10px 14px;margin-bottom:20px;font-size:0.75rem;color:#b0bec5;'>"
        f"<summary style='color:#90caf9;cursor:pointer;'>🔎 GPU/HBM 一手来源快照 — {status}</summary>"
        + "".join(rows)
        + "</details>"
    )


def _load_candidate(path: str | Path) -> dict[str, Any]:
    return _read_json(Path(path), SnapshotValidationError, "candidate_missing")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate first-party GPU/HBM runtime snapshots")
    parser.add_argument("--runtime-dir", default=str(DEFAULT_RUNTIME_DIR))
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--candidate", required=True)

    commit_parser = subparsers.add_parser("commit")
    commit_parser.add_argument("--candidate", required=True)
    commit_parser.add_argument("--ticker", required=True, choices=sorted(SUPPORTED_TICKERS))

    precheck_parser = subparsers.add_parser("precheck")
    precheck_parser.add_argument("--manifest", required=True)
    precheck_parser.add_argument("--ticker", required=True, choices=sorted(SUPPORTED_TICKERS))

    authorize_parser = subparsers.add_parser("authorize-current")
    authorize_parser.add_argument("--refresh-id", required=True)
    authorize_parser.add_argument("--ticker", required=True, choices=sorted(SUPPORTED_TICKERS))
    authorize_parser.add_argument("--failed-module", action="append", required=True, choices=sorted(REQUIRED_MODULES))

    subparsers.add_parser("status")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    runtime = Path(args.runtime_dir)
    try:
        if args.command == "validate":
            snapshot = validate_snapshot(_load_candidate(args.candidate))
            print(f"[INDUSTRY] valid refresh_id={snapshot['refresh_id']}")
        elif args.command == "commit":
            manifest = promote_snapshot(_load_candidate(args.candidate), runtime, args.ticker)
            print(f"[INDUSTRY] committed refresh_id={manifest['refresh_id']} mode=fresh")
        elif args.command == "precheck":
            manifest = precheck_run_manifest(args.manifest, args.ticker)
            print(f"[INDUSTRY] ready refresh_id={manifest['refresh_id']} mode={manifest['mode']}")
        elif args.command == "authorize-current":
            manifest = authorize_current_snapshot(
                runtime, args.refresh_id, args.ticker, args.failed_module
            )
            print(f"[INDUSTRY] authorized refresh_id={manifest['refresh_id']} mode=cached-authorized")
        elif args.command == "status":
            current = runtime / "industry_snapshot.json"
            manifest_path = runtime / "industry_run.json"
            print(f"[INDUSTRY] snapshot={'present' if current.is_file() else 'missing'} manifest={'present' if manifest_path.is_file() else 'missing'}")
    except (SnapshotValidationError, RunManifestError) as exc:
        print(f"[INDUSTRY] blocked error={exc.code}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
