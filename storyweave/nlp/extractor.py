"""GLiNER entity extraction — the extraction FLOOR (Phase 2).

GLiNER is zero-shot and genre-agnostic: it needs no training and produces a useful
typed-entity set by itself, satisfying rule #3. The heavy ``gliner``/``torch``
imports are LAZY (done inside methods) so this module imports cleanly in the light
``.venv`` (3.14); the model only loads under ``.venv-ml`` (3.12).

HuggingFace weights are forced onto the project drive (F:) by configuring HF_HOME
*before* the first HF import — never C: (CLAUDE.md env discipline).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from storyweave.config import Settings, get_settings
from storyweave.db.models import NodeType
from storyweave.nlp.labels import DEFAULT_LABELS, LABEL_TO_TYPE

if TYPE_CHECKING:  # pragma: no cover - typing only
    from gliner import GLiNER


@dataclass
class MentionSpan:
    """A single GLiNER candidate, offsets relative to the text passed to ``extract``."""

    surface: str
    type: NodeType
    char_start: int
    char_end: int
    score: float
    subtype: str | None = None


def configure_hf_cache(settings: Settings | None = None) -> None:
    """Pin the HuggingFace cache to the project drive. Must run before HF imports."""
    cfg = settings or get_settings()
    cfg.hf_home.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("HF_HOME", str(cfg.hf_home))
    if cfg.hf_disable_symlinks:
        os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS", "1")
        os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")


class GlinerExtractor:
    """Lazy wrapper around a GLiNER model returning canonical-typed mentions."""

    def __init__(
        self,
        model_name: str | None = None,
        threshold: float | None = None,
        device: str | None = None,
        labels: list[str] | None = None,
        label_map: dict[str, NodeType] | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self.model_name = model_name or self._settings.gliner_model
        self.threshold = threshold if threshold is not None else self._settings.gliner_threshold
        self.device = device or self._settings.gliner_device
        self.labels = labels or DEFAULT_LABELS
        self.label_map = label_map or LABEL_TO_TYPE
        self._model: GLiNER | None = None

    def _ensure_loaded(self) -> GLiNER:
        if self._model is None:
            configure_hf_cache(self._settings)
            from gliner import GLiNER  # lazy: heavy import only under .venv-ml

            model = GLiNER.from_pretrained(self.model_name)
            if self.device and self.device != "cpu":
                model = model.to(self.device)
            self._model = model
        return self._model

    def extract(self, text: str) -> list[MentionSpan]:
        """Extract canonical-typed mentions from ``text`` (offsets relative to it)."""
        if not text.strip():
            return []
        model = self._ensure_loaded()
        raw: list[dict[str, Any]] = model.predict_entities(
            text, self.labels, threshold=self.threshold
        )
        mentions: list[MentionSpan] = []
        for ent in raw:
            canonical = self.label_map.get(ent["label"])
            if canonical is None:
                continue  # unknown prompt label -> drop (stay within the 8 types)
            mentions.append(
                MentionSpan(
                    surface=ent["text"],
                    type=canonical,
                    char_start=int(ent["start"]),
                    char_end=int(ent["end"]),
                    score=float(ent["score"]),
                )
            )
        return mentions
