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
from storyweave.db.models import (
    EntityLabel,
    ExtractionMethod,
    LabelKind,
    Mention,
    Node,
    NodeType,
)
from storyweave.db.repository import Repository
from storyweave.ingest.work_config import WorkConfig
from storyweave.nlp.cluster import cluster_mentions_detailed, normalize_surface
from storyweave.nlp.extractor import GlinerExtractor
from storyweave.nlp.labels import DEFAULT_LABELS, LABEL_TO_TYPE
from storyweave.nlp.orgs import GROUP_NOUNS, find_organization_spans
from storyweave.nlp.titles import find_title_links


@dataclass
class ExtractionReport:
    work_id: int
    mentions_count: int = 0
    entities_count: int = 0
    per_type: dict[NodeType, int] = field(default_factory=dict)
    labels_count: int = 0
    title_links: int = 0
    titles_rejected: int = 0
    #: abbreviation merges made, and candidates refused (with reasons), for the report
    alias_merges: int = 0
    alias_under_merges: list[str] = field(default_factory=list)
    #: retrofit R4b: Organization spans added by the group-noun head rule
    group_noun_promotions: int = 0

    def summary(self) -> str:
        by_type = ", ".join(f"{t.value}:{n}" for t, n in sorted(self.per_type.items()))
        return (
            f"work id={self.work_id}: {self.mentions_count} mentions -> "
            f"{self.entities_count} entities ({by_type}); "
            f"{self.labels_count} labels, {self.alias_merges} alias merges, "
            f"{len(self.alias_under_merges)} refused, "
            f"{self.title_links} title links ({self.titles_rejected} refused), "
            f"{self.group_noun_promotions} group-noun org promotions"
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

    repo.clear_entity_labels(work_id)  # before clear_nodes: labels FK-cascade off nodes
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

        # Retrofit R4b: add the Organization spans the model structurally cannot see.
        # Runs AFTER the model's own spans are collected and never replaces one, so the
        # floor's output is a strict subset of what is persisted.
        if cfg.extraction.promote_group_nouns:
            group_nouns = tuple(cfg.extraction.group_nouns) or GROUP_NOUNS
            already = frozenset((s.start, s.end) for s in best.values())
            for org in find_organization_spans(chapter.clean_text, already, group_nouns):
                key = (org.char_start, org.char_end, NodeType.ORGANIZATION)
                if key in best:
                    continue
                best[key] = MentionSpanTuple(
                    org.char_start, org.char_end, NodeType.ORGANIZATION,
                    org.surface,
                    # Score 1.0 is not a model confidence and must not be read as one:
                    # this span came from a deterministic rule, which is also why its
                    # provenance is `rule`, not `gliner`.
                    1.0, None, ExtractionMethod.RULE,
                )
                report.group_noun_promotions += 1

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
                    extraction_method=span.method,
                )
            )
            report.mentions_count += 1

    # Cluster the persisted mentions into canonical entities.
    outcome = cluster_mentions_detailed(repo.list_mentions(work_id), cfg.clustering)
    report.alias_merges = len(outcome.merges)
    report.alias_under_merges = [
        f"{d.short!r} -/-> {d.host!r}: {d.reason}" for d in outcome.under_merges
    ]
    #: entity_id -> the surface strings naming it, for title apposition matching
    names_by_entity: dict[int, set[str]] = {}
    _node_types: dict[int, NodeType] = {}

    for cluster in outcome.clusters:
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

        # --- entity_labels: the canonical name plus every merged surface variant ---
        # Each label's revealed_chapter is the chapter that surface FIRST APPEARS in, not
        # the entity's reveal chapter: the reader learns "Drask" when they read "Drask",
        # which may be chapters after they met "Warden-Captain Orin Drask".
        surfaces: dict[str, tuple[int, Mention]] = {}
        for member in cluster.members:
            surface = member.surface.strip()
            prior = surfaces.get(surface)
            if prior is None or member.chapter_ordinal < prior[0]:
                surfaces[surface] = (member.chapter_ordinal, member)
        names_by_entity[node_id] = set(surfaces)
        _node_types[node_id] = cluster.type

        canonical_norm = normalize_surface(cluster.name)
        for surface, (first_chapter, member) in sorted(surfaces.items()):
            is_primary = surface == cluster.name
            # A surface with fewer words than the canonical name is a shortening of it;
            # same length means it is the same name differently punctuated/cased.
            kind = (
                LabelKind.FULL
                if is_primary or normalize_surface(surface) == canonical_norm
                else LabelKind.SHORT
            )
            repo.add_entity_label(
                EntityLabel(
                    entity_id=node_id,
                    label=surface,
                    kind=kind,
                    revealed_chapter=first_chapter,
                    is_primary=is_primary,
                    quote=_snippet(
                        chapter_text.get(member.chapter_id, ""),
                        member.char_start,
                        member.char_end,
                    ),
                )
            )
            report.labels_count += 1

    # --- titles: attach to the person the text appositions them to, fenced on that
    # chapter. Characters only - an organization does not hold a title.
    character_names = {
        nid: names
        for nid, names in names_by_entity.items()
        if _node_types.get(nid) is NodeType.CHARACTER
    }
    links, rejected = find_title_links(
        character_names, {c.ordinal: c.clean_text for c in chapters}
    )
    for link in links:
        repo.add_entity_label(
            EntityLabel(
                entity_id=link.entity_id,
                label=link.title,
                kind=LabelKind.TITLE,
                revealed_chapter=link.chapter,  # the reveal: when the text connects them
                is_primary=False,
                quote=link.quote,  # mandatory for a title; R4's validator reads it
            )
        )
        report.labels_count += 1
        report.title_links += 1
    report.titles_rejected = len(rejected)

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
    #: retrofit R4b: how this span was produced. `rule` for a group-noun promotion,
    #: so a rule-derived mention is never mistaken for a model prediction.
    method: ExtractionMethod = ExtractionMethod.GLINER
