"""Phase 7c: Tier-3 identity inference.

The permanent regressions inject a FAKE model (IdentityProtocol) so the reveal
computation, citation gate, anchoring, persistence, idempotency, fencing, and
graceful degradation all run under the light .venv with ZERO ML and ZERO network —
and they are DETERMINISTIC (a live LLM is non-deterministic and must never gate CI).

A. FLIP-AT-GOLD     — edges land at revealed_chapter == gold k (C1=2, C2=3, C3=4).
B. NO-CITATION-NO-EDGE — a confident YES with an unverifiable quote writes NOTHING.

The live model is exercised separately, non-blocking, in eval/identity_eval.py (and
the opt-in smoke at the bottom), per the repo's eval-script convention.
"""

from __future__ import annotations

import os
import urllib.request

import pytest

from storyweave.db.models import (
    TIER3_RELATIONS,
    Chapter,
    Edge,
    ExtractionMethod,
    Mention,
    Node,
    NodeType,
    RelationTier,
    Work,
)
from storyweave.db.repository import Repository
from storyweave.nlp.identity import (
    IdentityReport,
    IdentityVerdict,
    citation_in_range,
    infer_identities,
    normalize_relation,
)
from storyweave.query import fence

# Chapter texts carrying the real confirming clauses (the citation gate matches these).
CH1 = "Wren moved through the night markets of Aldercross. He saw glass towers that do not exist."
CH2 = (
    "Wren was Caelum. Prince Caelum Veyle, only son of Queen Maela, drowned at six. "
    "Ser Dunmore posted men at every gate."
)
CH3 = (
    "The message named the Gray Sparrow. The Gray Sparrow and Lady Veris were the same person."
)
CH4 = "It was as if an older soul had been poured into the drowned prince. Ser Dunmore knelt."

# Gold reveal chapters (fixed by the Phase-7b addendum, confirmed against the text).
SECRET_CLUE = "Wren was Caelum"  # ch2  -> SECRET_IDENTITY, gold k=2
ALIAS_CLUE = "The Gray Sparrow and Lady Veris were the same person"  # ch3 -> ALIAS, gold k=3
TRANSMIG_CLUE = "an older soul had been poured into the drowned prince"  # ch4 -> gold k=4


class FakeIdentity:
    """Deterministic IdentityProtocol stand-in scripted by (name-pair, k)."""

    def __init__(
        self,
        script: dict[tuple[frozenset[str], int], IdentityVerdict],
        *,
        raise_on_call: bool = False,
    ) -> None:
        self._script = script
        self._raise = raise_on_call
        self.calls = 0

    def infer(self, a: str, b: str, text: str, k: int) -> IdentityVerdict:
        self.calls += 1
        if self._raise:
            raise RuntimeError("simulated model failure")
        return self._script.get((frozenset({a, b}), k), IdentityVerdict(False, None, ""))


def _setup_sample(repo: Repository) -> tuple[int, dict[str, int]]:
    """4-chapter work with clue-bearing text and the five canonical person nodes."""
    wid = repo.create_work(Work(slug="hc", title="HC"))
    chap_ids: dict[int, int] = {}
    for ordinal, text in ((1, CH1), (2, CH2), (3, CH3), (4, CH4)):
        chap_ids[ordinal] = repo.add_chapter(
            Chapter(work_id=wid, ordinal=ordinal, clean_text=text, content_hash=f"h{ordinal}")
        )
    # (name, type, first_seen, chapters it is mentioned in -> drives co-occurrence).
    people: list[tuple[str, NodeType, int, list[int]]] = [
        ("Wren", NodeType.CHARACTER, 1, [1, 2, 3, 4]),
        ("Caelum", NodeType.CHARACTER, 2, [2, 3, 4]),
        ("Gray Sparrow", NodeType.CHARACTER, 3, [3, 4]),
        ("Lady Veris", NodeType.CHARACTER, 3, [3, 4]),
        ("Ser Dunmore", NodeType.CHARACTER, 2, [2, 4]),
    ]
    ids: dict[str, int] = {}
    for name, typ, first_seen, chapters in people:
        nid = repo.add_node(
            Node(
                work_id=wid, type=typ, name=name,
                first_seen_chapter=first_seen, revealed_chapter=first_seen,
                extraction_method=ExtractionMethod.GLINER, importance=1.0,
            )
        )
        ids[name] = nid
        for ordinal in chapters:
            repo.add_mention(
                Mention(
                    work_id=wid, chapter_id=chap_ids[ordinal], chapter_ordinal=ordinal,
                    ordinal=0, surface=name, type=typ,
                    char_start=0, char_end=len(name), score=0.9, node_id=nid,
                )
            )
    return wid, ids


def _gold_script() -> dict[tuple[frozenset[str], int], IdentityVerdict]:
    """Per-(pair, k) verdicts mirroring the addendum's correct, citation-anchored behavior."""
    wc = frozenset({"Wren", "Caelum"})
    sv = frozenset({"Gray Sparrow", "Lady Veris"})
    return {
        # (Wren, Caelum): SECRET_IDENTITY confirmable from ch2; TRANSMIGRATED_INTO from ch4.
        (wc, 2): IdentityVerdict(True, "SECRET_IDENTITY", SECRET_CLUE),
        (wc, 3): IdentityVerdict(True, "SECRET_IDENTITY", SECRET_CLUE),
        (wc, 4): IdentityVerdict(True, "TRANSMIGRATED_INTO", TRANSMIG_CLUE),
        # (Gray Sparrow, Lady Veris): ALIAS confirmable from ch3.
        (sv, 3): IdentityVerdict(True, "ALIAS", ALIAS_CLUE),
        (sv, 4): IdentityVerdict(True, "ALIAS", ALIAS_CLUE),
    }


# --------------------------------------------------------------------------- #
# A. FLIP-AT-GOLD (the anti-early-bloom guarantee, made permanent).
# --------------------------------------------------------------------------- #
def test_flip_at_gold_writes_each_edge_at_its_reveal_chapter() -> None:
    with Repository(":memory:") as repo:
        repo.initialize_schema()
        wid, ids = _setup_sample(repo)
        report = infer_identities(wid, repo, model=FakeIdentity(_gold_script()))

        assert not report.disabled and not report.degraded
        assert report.edges_added == 3
        edges = repo.list_edges_by_tier(wid, RelationTier.IDENTITY)
        by_rel = {e.relation: e for e in edges}
        assert set(by_rel) == {"SECRET_IDENTITY", "ALIAS", "TRANSMIGRATED_INTO"}

        # The whole phase: each edge blooms at its gold k, never a chapter early.
        assert by_rel["SECRET_IDENTITY"].revealed_chapter == 2
        assert by_rel["ALIAS"].revealed_chapter == 3
        assert by_rel["TRANSMIGRATED_INTO"].revealed_chapter == 4

        # Anchored to the floor nodes; provenance + evidence; never a node collapse.
        wc = by_rel["SECRET_IDENTITY"]
        assert {wc.source_id, wc.target_id} == {ids["Wren"], ids["Caelum"]}
        assert wc.source_id != wc.target_id
        for e in edges:
            assert e.tier is RelationTier.IDENTITY
            assert e.extraction_method is ExtractionMethod.LLM
            assert e.evidence_span
        assert repo.count_nodes(wid) == 5  # nothing invented, nothing merged


def test_layered_reveal_on_one_pair() -> None:
    """The Wren/Caelum pair carries TWO reveals at two chapters (the LotM-style showcase)."""
    with Repository(":memory:") as repo:
        repo.initialize_schema()
        wid, ids = _setup_sample(repo)
        infer_identities(wid, repo, model=FakeIdentity(_gold_script()))
        pair = {ids["Wren"], ids["Caelum"]}
        on_pair = [
            e
            for e in repo.list_edges_by_tier(wid, RelationTier.IDENTITY)
            if {e.source_id, e.target_id} == pair
        ]
        assert {(e.relation, e.revealed_chapter) for e in on_pair} == {
            ("SECRET_IDENTITY", 2),
            ("TRANSMIGRATED_INTO", 4),
        }


def test_identity_edge_is_fenced_by_revealed_chapter() -> None:
    """No new fence path: the SECRET_IDENTITY edge is hidden until both endpoints + edge show."""
    with Repository(":memory:") as repo:
        repo.initialize_schema()
        wid, _ = _setup_sample(repo)
        infer_identities(wid, repo, model=FakeIdentity(_gold_script()))
        # Caelum is revealed ch2, so at n=1 the edge is hidden; at n=2 it appears.
        rels_at_1 = {e.relation for e in fence.visible_edges(repo, wid, 1)}
        rels_at_2 = {e.relation for e in fence.visible_edges(repo, wid, 2)}
        assert "SECRET_IDENTITY" not in rels_at_1
        assert "SECRET_IDENTITY" in rels_at_2
        assert "TRANSMIGRATED_INTO" not in rels_at_2  # gold ch4
        assert "TRANSMIGRATED_INTO" in {e.relation for e in fence.visible_edges(repo, wid, 4)}


# --------------------------------------------------------------------------- #
# B. NO-CITATION-NO-EDGE (the citation gate / confidence margin).
# --------------------------------------------------------------------------- #
def test_confident_yes_without_valid_citation_writes_no_edge() -> None:
    with Repository(":memory:") as repo:
        repo.initialize_schema()
        wid, _ = _setup_sample(repo)
        wc = frozenset({"Wren", "Caelum"})
        # Confident, correctly-typed YES — but the "quote" is fabricated (not in the text).
        script = {
            (wc, 2): IdentityVerdict(True, "SECRET_IDENTITY", "they share a secret bloodline"),
            (wc, 3): IdentityVerdict(True, "SECRET_IDENTITY", "they share a secret bloodline"),
            (wc, 4): IdentityVerdict(True, "SECRET_IDENTITY", "they share a secret bloodline"),
        }
        report = infer_identities(wid, repo, model=FakeIdentity(script))

        assert report.edges_added == 0
        assert repo.list_edges_by_tier(wid, RelationTier.IDENTITY) == []
        # Observably DISTINCT from "no identity found": the YES was seen and rejected.
        assert report.citations_rejected >= 1


def test_no_identity_found_is_distinct_from_rejected() -> None:
    """A clean NO leaves citations_rejected at zero (diagnosable fail paths)."""
    with Repository(":memory:") as repo:
        repo.initialize_schema()
        wid, _ = _setup_sample(repo)
        report = infer_identities(wid, repo, model=FakeIdentity({}))  # always NO
        assert report.edges_added == 0
        assert report.citations_rejected == 0


# --------------------------------------------------------------------------- #
# Idempotency + tier isolation + graceful degradation + disabled-by-default.
# --------------------------------------------------------------------------- #
def test_idempotent_and_leaves_other_tiers_untouched() -> None:
    with Repository(":memory:") as repo:
        repo.initialize_schema()
        wid, ids = _setup_sample(repo)
        # Pre-existing Tier-1 + Tier-2 edges must survive a Tier-3 rebuild.
        repo.add_edge(Edge(
            work_id=wid, source_id=ids["Wren"], target_id=ids["Ser Dunmore"],
            relation="RelatedTo", tier=RelationTier.STRUCTURAL,
            first_seen_chapter=2, revealed_chapter=2,
            extraction_method=ExtractionMethod.RULE, evidence_span="ev",
        ))
        repo.add_edge(Edge(
            work_id=wid, source_id=ids["Lady Veris"], target_id=ids["Ser Dunmore"],
            relation="Ally", tier=RelationTier.SOCIAL,
            first_seen_chapter=4, revealed_chapter=4,
            extraction_method=ExtractionMethod.GLINER, evidence_span="ev",
        ))

        first = infer_identities(wid, repo, model=FakeIdentity(_gold_script()))
        second = infer_identities(wid, repo, model=FakeIdentity(_gold_script()))
        assert first.edges_added == second.edges_added == 3
        assert len(repo.list_edges_by_tier(wid, RelationTier.IDENTITY)) == 3  # no duplication
        assert len(repo.list_edges_by_tier(wid, RelationTier.STRUCTURAL)) == 1
        assert len(repo.list_edges_by_tier(wid, RelationTier.SOCIAL)) == 1


def test_graceful_degradation_keeps_the_floor() -> None:
    with Repository(":memory:") as repo:
        repo.initialize_schema()
        wid, ids = _setup_sample(repo)
        repo.add_edge(Edge(
            work_id=wid, source_id=ids["Wren"], target_id=ids["Caelum"],
            relation="RelatedTo", tier=RelationTier.STRUCTURAL,
            first_seen_chapter=2, revealed_chapter=2,
            extraction_method=ExtractionMethod.RULE, evidence_span="ev",
        ))
        report: IdentityReport = infer_identities(
            wid, repo, model=FakeIdentity({}, raise_on_call=True)
        )
        assert report.degraded is True and report.edges_added == 0
        assert repo.list_edges_by_tier(wid, RelationTier.IDENTITY) == []
        assert len(repo.list_edges_by_tier(wid, RelationTier.STRUCTURAL)) == 1  # floor intact


def test_disabled_by_default_writes_nothing_and_opens_no_socket(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Flag off (default) -> disabled report, zero edges, no client, no network (rules #4/#5)."""

    def _boom(*_a: object, **_k: object) -> None:
        raise AssertionError("network call attempted while llm_enabled=False")

    monkeypatch.setattr(urllib.request, "urlopen", _boom)
    with Repository(":memory:") as repo:
        repo.initialize_schema()
        wid, _ = _setup_sample(repo)
        report = infer_identities(wid, repo)  # no injected model, default settings (disabled)
        assert report.disabled is True
        assert report.edges_added == 0
        assert repo.list_edges_by_tier(wid, RelationTier.IDENTITY) == []


# --------------------------------------------------------------------------- #
# Unit: citation gate + relation vocabulary.
# --------------------------------------------------------------------------- #
def test_citation_gate_tolerates_formatting_but_rejects_fabrication() -> None:
    fed = "the Gray Sparrow and Lady Veris were the same person"
    # Smart quotes, em-dash, casing, extra spaces — still matches the same words.
    assert citation_in_range("“The Gray Sparrow — and Lady Veris were the SAME person”", fed)
    assert not citation_in_range("they are secretly the same", fed)  # different words
    assert not citation_in_range("person", fed)  # occurs, but below the min-length floor


def test_relation_normalization_stays_within_tier3() -> None:
    assert normalize_relation("secret identity") == "SECRET_IDENTITY"
    assert normalize_relation("Transmigrated-Into") == "TRANSMIGRATED_INTO"
    assert normalize_relation("Ally") is None  # a Tier-2 relation is not a Tier-3 identity
    assert set(TIER3_RELATIONS) == {
        "SAME_AS", "ALIAS", "SECRET_IDENTITY", "REINCARNATION", "TRANSMIGRATED_INTO"
    }


# --------------------------------------------------------------------------- #
# Live-model smoke (opt-in, non-blocking). Skips unless STORYWEAVE_LLM_LIVE=1 with a
# running runner; never gates CI. Full reveal-accuracy numbers: eval/identity_eval.py.
# --------------------------------------------------------------------------- #
def test_real_model_identity_smoke() -> None:
    if not os.environ.get("STORYWEAVE_LLM_LIVE"):
        pytest.skip("live model not requested (set STORYWEAVE_LLM_LIVE=1 with a running runner)")
    from storyweave.config import Settings
    from storyweave.nlp.identity import LlmIdentityModel

    model = LlmIdentityModel(Settings(llm_enabled=True))
    verdict = model.infer("Wren", "Caelum", CH1 + "\n\n" + CH2, k=2)
    assert isinstance(verdict, IdentityVerdict)  # shape only — correctness is the eval's job
