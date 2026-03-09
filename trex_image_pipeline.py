#!/usr/bin/env python3
"""
Refactored T-Rex image pipeline (modular prompt + provider adapter + metadata + gallery)
Backward-compatible entrypoint.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from gallery import write_batch_gallery
from prompt_builder import base_structured_prompt, variant_detail_suffixes
from providers import GenerationConfig, OpenAIProvider, ProviderError

BASE_INTENT = "霸王龙，尽量看起来是活的真实的，长方形横图"
OPENAI_GEN_SCRIPT = "/Users/William/.npm-global/lib/node_modules/openclaw/skills/openai-image-gen/scripts/gen.py"


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def planner(user_intent: str) -> dict:
    return {
        "intent": user_intent,
        "provider": "openai",
        "model": "gpt-image-1",
        "size": "1536x1024",
        "quality": "high",
        "default_count": 4,
    }


def build_variant_prompts(count: int) -> list[dict]:
    base = base_structured_prompt()
    suffixes = variant_detail_suffixes()
    prompts: list[dict] = []

    for i, suffix in enumerate(suffixes[:count], start=1):
        full = base.to_full_prompt() + ", " + suffix
        prompts.append(
            {
                "variant_id": i,
                "prompt_full": full,
                "prompt_summary": f"{base.summary()} | {suffix}",
                "structured_prompt": {
                    **base.as_dict(),
                    "variant_detail_suffix": suffix,
                },
            }
        )
    return prompts


def build_variant_prompts_from_request(req: dict[str, Any], count: int) -> list[dict]:
    enhanced_prompt = req.get("enhanced_prompt", "").strip()
    structured = req.get("structured_fields", {}) or {}
    negatives = req.get("negative_constraints", []) or []
    variations = req.get("variation_plan", []) or []

    if not enhanced_prompt:
        enhanced_prompt = structured.get("subject", "") or BASE_INTENT

    if not variations:
        variations = [f"Variation {i}" for i in range(1, count + 1)]

    prompts: list[dict] = []
    for i in range(1, count + 1):
        suffix = str(variations[(i - 1) % len(variations)])
        neg_text = ", ".join([str(x) for x in negatives if x])
        full = enhanced_prompt
        if suffix:
            full += f", {suffix}"
        if neg_text:
            full += f", {neg_text}"
        prompts.append(
            {
                "variant_id": i,
                "prompt_full": full,
                "prompt_summary": f"{structured.get('subject','Generated concept')} | {suffix}",
                "structured_prompt": {
                    "subject": structured.get("subject", ""),
                    "scene": structured.get("scene", ""),
                    "style": structured.get("style", ""),
                    "camera": structured.get("camera", ""),
                    "lighting": structured.get("lighting", ""),
                    "detail_enhancements": [structured.get("mood", "")],
                    "negative_constraints": negatives,
                    "variant_detail_suffix": suffix,
                },
            }
        )
    return prompts


def write_json(path: Path, data: dict | list) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def append_prompttrace_event(event: dict, sink: Path) -> None:
    sink.parent.mkdir(parents=True, exist_ok=True)
    with sink.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def build_prompttrace_event(*, start_ts: str, end_ts: str, latency_ms: int, model: str, prompt: str, status: str, error_message: str | None = None) -> dict:
    prompt_preview = (prompt[:240] + "...") if len(prompt) > 240 else prompt
    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    return {
        "span_id": str(uuid.uuid4()),
        "timestamp_start": start_ts,
        "timestamp_end": end_ts,
        "latency_ms": latency_ms,
        "provider": "openai",
        "model": model,
        "endpoint": "image.pipeline.generate",
        "request_type": "image",
        "prompt_preview": prompt_preview,
        "prompt_hash": prompt_hash,
        "input_tokens": None,
        "output_tokens": None,
        "total_tokens": None,
        "response_preview": "image_generated" if status == "ok" else None,
        "structured_output_ok": status == "ok",
        "status": status,
        "error_category": "permission" if (error_message and "401" in error_message) else ("unknown" if error_message else None),
        "error_message_preview": (error_message[:240] + "...") if error_message and len(error_message) > 240 else error_message,
        "retries": {"count": 0, "finalOutcome": "success" if status == "ok" else "failed"},
        "cache": {"hit": False},
        "estimated_cost_usd": None,
        "pricing_source": "manual-none",
        "redaction_applied": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=4, help="number of variants to generate (max 8)")
    parser.add_argument("--provider", default="openai", choices=["openai"], help="image provider (currently openai)")
    parser.add_argument("--request-file", default="", help="optional studio request JSON file")
    args = parser.parse_args()

    plan = planner(BASE_INTENT)
    plan["provider"] = args.provider
    count = max(1, min(args.count, 8))

    batch_id = f"trex_batch_{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    root_out = Path(f"/Users/William/Desktop/{batch_id}")
    root_out.mkdir(parents=True, exist_ok=True)

    # Required files scaffold
    write_json(root_out / "favorites.json", {"batch_id": batch_id, "favorites": []})

    batch_metadata = {
        "batch_id": batch_id,
        "timestamp": iso_now(),
        "intent": BASE_INTENT,
        "provider": plan["provider"],
        "model": plan["model"],
        "size": plan["size"],
        "quality": plan["quality"],
        "count": count,
        "variants": [],
        "api_tracker": {
            "name": "prompttrace",
            "trace_file": "/Users/William/Desktop/prompttrace/.prompttrace/traces.jsonl"
        }
    }

    request_payload: dict[str, Any] = {}
    if args.request_file:
        req_path = Path(args.request_file).expanduser()
        if req_path.exists():
            request_payload = json.loads(req_path.read_text(encoding="utf-8"))
            controls = request_payload.get("controls", {}) or {}
            plan["provider"] = controls.get("provider", plan["provider"])
            plan["model"] = controls.get("model", plan["model"])
            realism = str(controls.get("realism", plan["quality"]))
            realism_map = {"ultra": "high", "high": "high", "medium": "medium", "low": "low"}
            plan["quality"] = realism_map.get(realism, "high")
            ratio = controls.get("aspect_ratio", "3:2")
            ratio_map = {"3:2": "1536x1024", "16:9": "1536x864", "1:1": "1024x1024", "9:16": "1024x1536"}
            plan["size"] = ratio_map.get(ratio, plan["size"])
            req_count = int(controls.get("num_variants", count) or count)
            count = max(1, min(req_count, 8))

    provider = OpenAIProvider(OPENAI_GEN_SCRIPT)
    config = GenerationConfig(model=plan["model"], size=plan["size"], quality=plan["quality"])

    variants = build_variant_prompts_from_request(request_payload, count) if request_payload else build_variant_prompts(count)

    had_error = False
    prompttrace_sink = Path("/Users/William/Desktop/prompttrace/.prompttrace/traces.jsonl")

    for v in variants:
        variant_id = v["variant_id"]
        out_dir = root_out / f"variant_{variant_id}"
        out_dir.mkdir(parents=True, exist_ok=True)
        start_dt = datetime.now(timezone.utc)

        variant_meta = {
            "batch_id": batch_id,
            "variant_id": variant_id,
            "timestamp": iso_now(),
            "provider": plan["provider"],
            "model": plan["model"],
            "prompt_full": v["prompt_full"],
            "prompt_summary": v["prompt_summary"],
            "structured_prompt": v["structured_prompt"],
            "size": plan["size"],
            "quality": plan["quality"],
            "generation_params": {
                "seed": None,
                "count": 1,
            },
            "output_path": None,
            "status": "pending",
            "error": None,
        }

        try:
            result = provider.generate_image(v["prompt_full"], str(out_dir), config)
            image_path = result["image_path"]
            variant_meta["output_path"] = image_path
            variant_meta["output_rel_path"] = str(Path(image_path).relative_to(root_out))
            variant_meta["status"] = "ok"
        except ProviderError as e:
            had_error = True
            variant_meta["status"] = "error"
            variant_meta["error"] = str(e)
            print(f"[variant {variant_id}] ERROR: {e}")
        except Exception as e:
            had_error = True
            variant_meta["status"] = "error"
            variant_meta["error"] = f"Unexpected error: {e}"
            print(f"[variant {variant_id}] ERROR: Unexpected error: {e}")

        end_dt = datetime.now(timezone.utc)
        latency_ms = int((end_dt - start_dt).total_seconds() * 1000)
        trace_event = build_prompttrace_event(
            start_ts=start_dt.isoformat(),
            end_ts=end_dt.isoformat(),
            latency_ms=latency_ms,
            model=plan["model"],
            prompt=v["prompt_full"],
            status=variant_meta["status"],
            error_message=variant_meta.get("error"),
        )
        append_prompttrace_event(trace_event, prompttrace_sink)

        write_json(out_dir / "metadata.json", variant_meta)
        batch_metadata["variants"].append(variant_meta)

    write_json(root_out / "batch_metadata.json", batch_metadata)

    gallery_variants = []
    for m in batch_metadata["variants"]:
        sp = m.get("structured_prompt", {})
        gallery_variants.append(
            {
                "variant_id": m["variant_id"],
                "timestamp": m.get("timestamp"),
                "status": m.get("status", "unknown"),
                "error": m.get("error"),
                "prompt_full": m.get("prompt_full", ""),
                "prompt_summary": m.get("prompt_summary", ""),
                "provider": m.get("provider", plan["provider"]),
                "model": m.get("model", plan["model"]),
                "image_rel": m.get("output_rel_path", ""),
                "output_path": m.get("output_path", ""),
                "output_folder": str((root_out / f"variant_{m['variant_id']}").resolve()),
                "difference_focus": sp.get("variant_detail_suffix", ""),
                "structured_compact": {
                    "Pose": sp.get("subject", ""),
                    "Water": "Shallow-water motion with ripples/splashes",
                    "Lighting": sp.get("lighting", ""),
                    "Atmosphere": sp.get("variant_detail_suffix", ""),
                    "Style": sp.get("style", ""),
                },
                "prompt_parts": {
                    "base_prompt": ", ".join(
                        [
                            sp.get("subject", ""),
                            sp.get("scene", ""),
                            sp.get("style", ""),
                            sp.get("camera", ""),
                            sp.get("lighting", ""),
                            ", ".join(sp.get("detail_enhancements", [])),
                        ]
                    ).strip(", "),
                    "variant_modifiers": sp.get("variant_detail_suffix", ""),
                    "negative_constraints": sp.get("negative_constraints", []),
                    "model_settings": {
                        "provider": m.get("provider", plan["provider"]),
                        "model": m.get("model", plan["model"]),
                        "size": m.get("size", plan["size"]),
                        "quality": m.get("quality", plan["quality"]),
                    },
                },
                "metadata_rel": f"variant_{m['variant_id']}/metadata.json",
            }
        )

    index_path = write_batch_gallery(str(root_out), batch_metadata, gallery_variants)

    print(f"Done. Batch folder: {root_out}")
    print(f"Batch metadata: {root_out / 'batch_metadata.json'}")
    print(f"Favorites scaffold: {root_out / 'favorites.json'}")
    print(f"Gallery: {index_path}")

    if had_error:
        print("Completed with some errors. Check variant_*/metadata.json for details.")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
