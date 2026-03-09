from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import List


@dataclass
class StructuredPrompt:
    subject: str
    scene: str
    style: str
    camera: str
    lighting: str
    detail_enhancements: List[str] = field(default_factory=list)
    negative_constraints: List[str] = field(default_factory=list)

    def to_full_prompt(self) -> str:
        parts = [
            self.subject,
            self.scene,
            self.style,
            self.camera,
            self.lighting,
            ", ".join(self.detail_enhancements) if self.detail_enhancements else "",
            ", ".join(self.negative_constraints) if self.negative_constraints else "",
        ]
        return ", ".join([p.strip() for p in parts if p and p.strip()])

    def summary(self) -> str:
        return f"{self.subject} | {self.style} | {self.lighting}"

    def as_dict(self) -> dict:
        return asdict(self)


def base_structured_prompt() -> StructuredPrompt:
    return StructuredPrompt(
        subject="A living Tyrannosaurus rex, full body in frame, dynamic forward motion through shallow water",
        scene="In a lush prehistoric valley with realistic environment interactions (ripples and splashes)",
        style="Hyper-realistic, cinematic wildlife documentary style, photorealistic natural color grading",
        camera="Shot on a full-frame DSLR with a 70mm lens, shallow depth of field, landscape composition",
        lighting="Golden hour volumetric sunlight through mist",
        detail_enhancements=[
            "Highly detailed scales, scars, mud, subtle feather-like textures",
            "Powerful muscles and physically accurate anatomy",
            "Visible atmospheric particles and believable biomechanics",
        ],
        negative_constraints=[
            "No fantasy elements",
            "No cartoon or CGI look",
            "No extra limbs or deformed anatomy",
            "No text",
            "No watermark",
        ],
    )


def variant_detail_suffixes() -> list[str]:
    return [
        "Subtle rain droplets on skin, moody storm clouds in distance",
        "Low-angle camera perspective, stronger foreground water splash",
        "Early morning cool mist, softer sunlight, highly detailed eye reflections",
        "Volcanic ash haze in far background, dramatic rim lighting on body",
    ]
