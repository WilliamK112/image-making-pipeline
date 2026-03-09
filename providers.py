from __future__ import annotations

import glob
import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


class ProviderError(RuntimeError):
    pass


@dataclass
class GenerationConfig:
    model: str
    size: str
    quality: str


class ImageProvider:
    provider_name: str = "unknown"

    def generate_image(self, prompt: str, out_dir: str, config: GenerationConfig) -> dict:
        raise NotImplementedError


class OpenAIProvider(ImageProvider):
    provider_name = "openai"

    def __init__(self, script_path: str):
        self.script_path = script_path

    def _validate_env(self) -> None:
        key = os.environ.get("OPENAI_API_KEY")
        if not key:
            raise ProviderError("Missing API key: OPENAI_API_KEY is not set.")

    def generate_image(self, prompt: str, out_dir: str, config: GenerationConfig) -> dict:
        self._validate_env()
        Path(out_dir).mkdir(parents=True, exist_ok=True)

        cmd = [
            "python3",
            self.script_path,
            "--model",
            config.model,
            "--count",
            "1",
            "--size",
            config.size,
            "--quality",
            config.quality,
            "--out-dir",
            out_dir,
            "--prompt",
            prompt,
        ]

        proc = subprocess.run(cmd, capture_output=True, text=True)

        if proc.returncode != 0:
            stderr = (proc.stderr or "").strip()
            stdout = (proc.stdout or "").strip()
            merged = "\n".join([x for x in [stdout, stderr] if x])
            if "401" in merged or "Unauthorized" in merged:
                raise ProviderError("Invalid or unauthorized OpenAI API key (401).")
            if "HTTP Error" in merged or "OpenAI Images API failed" in merged:
                raise ProviderError(f"OpenAI API error: {merged[:500]}")
            raise ProviderError(f"Image generation failed: {merged[:500]}")

        image_path = self._detect_image_file(out_dir)
        if not image_path:
            raise ProviderError("Malformed response/output: generation completed but no image file found.")

        prompts_json = os.path.join(out_dir, "prompts.json")
        provider_raw = None
        if os.path.exists(prompts_json):
            try:
                with open(prompts_json, "r", encoding="utf-8") as f:
                    provider_raw = json.load(f)
            except Exception:
                provider_raw = None

        return {
            "image_path": image_path,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "provider_raw": provider_raw,
        }

    @staticmethod
    def _detect_image_file(out_dir: str) -> Optional[str]:
        candidates = []
        for ext in ("*.png", "*.jpg", "*.jpeg", "*.webp"):
            candidates.extend(glob.glob(os.path.join(out_dir, ext)))
        if not candidates:
            return None
        candidates.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        return candidates[0]
