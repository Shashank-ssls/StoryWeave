"""Extraction orchestration (Phase 2): chapters -> mentions -> canonical entities.

Flow, per CLAUDE.md (GLiNER is the floor; provenance everywhere):

  clear -> GLiNER over each chapter's chunks -> persist raw mentions (offsets mapped
  into chapter clean_text) -> alias-cluster -> insert canonical nodes (with
  first_seen_chapter, evidence quote, method='gliner') -> backfill mention.node_id.

Idempotent: extraction is derived data, so a re-run clears the work's mentions+nodes
and rebuilds. Running GLiNER per *chunk* (not whole chapter) keeps within the model's
length limit; chunk offsets are added back to recover chapter-level positions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from storyweave.config import Settings, get_settings
from storyweave.db.models import ExtractionMethod, Mention, Node, NodeType
from storyweave.db.repository import Repository
from storyweave.ingest.work_config import WorkConfig
from storyweave.nlp.cluster import cluster_mentions
from storyweave.nlp.extractor import GlinerExtractor
from storyweave.nlp.labels import DEFAULT_LABELS, LABEL_TO_TYPE


@dataclass
class ExtractionReport:
    work_id: int
    mentions_count: int = 0
    entities_count: int = 0
    per_type: dict[NodeType, int] = field(default_factory=dict)

    def summary(self) -> str:
        by_type = ", ".join(f"{t.value}:{n}" for t, n in sorted(self.per_type.items()))
        return (
            f"work id={self.work_id}: {self.mentions_count} mentions -> "
            f"{self.entities_count} entities ({by_type})"
        )


def build_extractor(cfg: WorkConfig, settings: Settings) -> GlinerExtractor:
    """Construct a GLiNER extractor, applying per-work label/threshold overrides."""
    extra = cfg.extraction.extra_labels
    labels = DEFAULT_LABELS + [p for p in extra if p not in LABEL_TO_TYPE]
    label_map = dict(LABEL_TO_TYPE)
    for prompt, canonical in extra.items():
        label_map[prompt] = NodeType(canonical)
    return GlinerExtractor(
        model_name=cfg.extraction.model,
        threshold=cfg.extraction.threshold,
        device=cfg.extraction.device,
        labels=labels,
        label_map=label_map,
        settings=settings,
    )


def _snippet(text: str, start: int, end: int, pad: int = 40) -> str:
    if not text:
        return ""
    a = max(0, start - pad)
    b = min(len(text), end + pad)
    return re.sub(r"\s+", " ", text[a:b]).strip()


def extract_work(
    work_id: int,
    repo: Repository,
    config: WorkConfig | None = None,
    settings: Settings | None = None,
    extractor: GlinerExtractor | None = None,
) -> ExtractionReport:
    """Run the GLiNER floor over a work and persist mentions + canonical entities."""
    cfg = config or WorkConfig()
    cfg_settings = settings or get_settings()
    ext = extractor or build_extractor(cfg, cfg_settings)

    repo.clear_mentions(work_id)
    repo.clear_nodes(work_id)  # cascades mention.node_id -> NULL too
    report = ExtractionReport(work_id=work_id)

    chapters = repo.list_chapters(work_id)
    chapter_text: dict[int, str] = {}

    for chapter in chapters:
        assert chapter.id is not None
        chapter_text[chapter.id] = chapter.clean_text
        # Map each chunk's local spans back to chapter offsets; dedup the overlap.
        best: dict[tuple[int, int, NodeType], MentionSpanTuple] = {}
        for chunk in repo.list_chunks(chapter.id):
            for sp in ext.extract(chunk.text):
                cs = sp.char_start + chunk.char_start
                ce = sp.char_end + chunk.char_start
                key = (cs, ce, sp.type)
                prev = best.get(key)
                if prev is None or sp.score > prev.score:
                    best[key] = MentionSpanTuple(cs, ce, sp.type, sp.surface, sp.score, sp.subtype)

        for ordinal, span in enumerate(sorted(best.values(), key=lambda s: (s.start, s.end))):
            repo.add_mention(
                Mention(
                    work_id=work_id,
                    chapter_id=chapter.id,
                    chapter_ordinal=chapter.ordinal,
                    ordinal=ordinal,
                    surface=span.surface,
                    type=span.type,
                    subtype=span.subtype,
                    char_start=span.start,
                    char_end=span.end,
                    score=span.score,
                )
            )
            report.mentions_count += 1

    # Cluster the persisted mentions into canonical entities.
    for cluster in cluster_mentions(repo.list_mentions(work_id)):
        rep = cluster.representative
        evidence = _snippet(chapter_text.get(rep.chapter_id, ""), rep.char_start, rep.char_end)
        node_id = repo.add_node(
            Node(
                work_id=work_id,
                type=cluster.type,
                name=cluster.name,
                subtype=cluster.subtype,
                importance=float(cluster.mention_count),
                first_seen_chapter=cluster.first_seen_chapter,
                revealed_chapter=cluster.first_seen_chapter,  # Phase 2: reveal == first seen
                extraction_method=ExtractionMethod.GLINER,
                evidence_span=evidence,
            )
        )
        for member in cluster.members:
            if member.id is not None:
                repo.set_mention_node(member.id, node_id)
        report.entities_count += 1
        report.per_type[cluster.type] = report.per_type.get(cluster.type, 0) + 1

    return report


@dataclass
class MentionSpanTuple:
    """Chapter-relative mention used during dedup (before persistence)."""

    start: int
    end: int
    type: NodeType
    surface: str
    score: float
    subtype: str | None
