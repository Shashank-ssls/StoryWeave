"""Part A: conservative coreference merge (pronoun self-reference -> POV).

Deterministic, light .venv, zero ML. Proves the SAFE-case merge folds first/second-person
pronoun nodes into the canonical POV character (edges re-pointed + deduped, no edge lost),
leaves AMBIGUOUS epithets alone (over-merge guard), preserves the fence invariant (a merged
edge keeps the EARLIEST revealed_chapter of its sources), and is idempotent + OFF by default.
"""

from __future__ import annotations

from storyweave.db.models import (
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
from storyweave.ingest.work_config import CorefConfig, WorkConfig
from storyweave.nlp.coref import merge_coref
from storyweave.query import fence


def _cfg(pov: str = "Sunny", *, on: bool = True) -> WorkConfig:
    return WorkConfig(coref=CorefConfig(merge_self_reference=on, pov_character=pov))


def _node(repo: Repository, wid: int, name: str, imp: float, rev: int = 1) -> int:
    return repo.add_node(
        Node(
            work_id=wid,
            type=NodeType.CHARACTER,
            name=name,
            importance=imp,
            first_seen_chapter=rev,
            revealed_chapter=rev,
            extraction_method=ExtractionMethod.GLINER,
        )
    )


def _edge(repo: Repository, wid: int, s: int, t: int, rev: int, rel: str = "RelatedTo") -> int:
    return repo.add_edge(
        Edge(
            work_id=wid,
            source_id=s,
            target_id=t,
            relation=rel,
            tier=RelationTier.STRUCTURAL,
            first_seen_chapter=rev,
            revealed_chapter=rev,
            extraction_method=ExtractionMethod.RULE,
            evidence_span="ev",
        )
    )


def _mention(repo: Repository, wid: int, cid: int, name: str, nid: int) -> None:
    repo.add_mention(
        Mention(
            work_id=wid, chapter_id=cid, chapter_ordinal=1, ordinal=0, surface=name,
            type=NodeType.CHARACTER, char_start=0, char_end=len(name), score=0.9, node_id=nid,
        )
    )


def _neighbors(repo: Repository, wid: int, node_id: int) -> set[int]:
    out: set[int] = set()
    for e in repo.list_edges(wid):
        if e.source_id == node_id:
            out.add(e.target_id)
        elif e.target_id == node_id:
            out.add(e.source_id)
    return out


def test_pronoun_nodes_fold_into_pov_edges_repointed_and_deduped() -> None:
    with Repository(":memory:") as repo:
        repo.initialize_schema()
        wid = repo.create_work(Work(slug="ss", title="SS"))
        cid = repo.add_chapter(Chapter(work_id=wid, ordinal=1, clean_text="x", content_hash="h"))
        sunny = _node(repo, wid, "Sunny", imp=10)
        you = _node(repo, wid, "you", imp=2)
        i = _node(repo, wid, "I", imp=1)
        a = _node(repo, wid, "Nightmares", imp=3)
        b = _node(repo, wid, "Dream Realm", imp=3)
        c = _node(repo, wid, "Sword", imp=1)
        _mention(repo, wid, cid, "you", you)
        _mention(repo, wid, cid, "I", i)
        # Sunny->A and you->A collide after merge (dedup); you->B and I->C re-point;
        # you->Sunny becomes a self-loop and is dropped.
        _edge(repo, wid, sunny, a, rev=2)
        _edge(repo, wid, you, a, rev=3)
        _edge(repo, wid, you, b, rev=2)
        _edge(repo, wid, i, c, rev=4)
        _edge(repo, wid, you, sunny, rev=2)

        report = merge_coref(wid, repo, _cfg())

        assert report.pov_character == "Sunny"
        assert report.nodes_merged == 2  # you + I folded away
        assert report.edges_deduped == 1  # you->A collapsed into Sunny->A
        assert report.edges_repointed == 2  # you->B and I->C moved onto Sunny
        assert report.self_loops_removed == 1  # you->Sunny
        assert report.mentions_repointed == 2  # evidence kept on Sunny
        # Junk pronoun nodes are gone; Sunny + the 3 neighbours remain.
        names = {n.name for n in repo.list_nodes(wid)}
        assert names == {"Sunny", "Nightmares", "Dream Realm", "Sword"}
        # No edge lost: Sunny now connects to ALL three neighbours, deduped to 3 edges.
        assert _neighbors(repo, wid, sunny) == {a, b, c}
        assert repo.count_edges(wid) == 3
        # Mentions re-attributed, none left pointing at a deleted node.
        assert all(m.node_id == sunny for m in repo.list_mentions(wid))


def test_ambiguous_epithet_is_not_merged() -> None:
    """An epithet that could match >1 character is LEFT alone (over-merge corrupts data)."""
    with Repository(":memory:") as repo:
        repo.initialize_schema()
        wid = repo.create_work(Work(slug="ss", title="SS"))
        sunny = _node(repo, wid, "Sunny", imp=10)
        _node(repo, wid, "you", imp=1)
        epithet = _node(repo, wid, "the younger soldier", imp=1)
        sentinel = _node(repo, wid, "Sentinel", imp=5)
        _node(repo, wid, "Cassia", imp=4)  # a 2nd candidate the epithet could match
        _edge(repo, wid, epithet, sentinel, rev=2)

        report = merge_coref(wid, repo, _cfg())

        assert report.nodes_merged == 1  # only the pronoun "you" folded
        names = {n.name for n in repo.list_nodes(wid)}
        assert "you" not in names  # pronoun merged
        assert "the younger soldier" in names  # epithet UNTOUCHED
        assert report.ambiguous_left >= 1  # observed as still-deferred, never guessed
        # The epithet's edge survives unchanged on its own node (not fused to anyone).
        assert _neighbors(repo, wid, epithet) == {sentinel}
        assert sunny in {n.id for n in repo.list_nodes(wid)}


def test_merged_edge_keeps_earliest_revealed_and_fence_hides_it() -> None:
    """Fence invariant: a merged edge reveals at min(sources), never earlier; fenced reads hold."""
    with Repository(":memory:") as repo:
        repo.initialize_schema()
        wid = repo.create_work(Work(slug="ss", title="SS"))
        sunny = _node(repo, wid, "Sunny", imp=10, rev=1)
        you = _node(repo, wid, "you", imp=2, rev=1)
        n = _node(repo, wid, "Nightmares", imp=3, rev=1)  # endpoints don't gate the edge
        _edge(repo, wid, you, n, rev=2)  # the earlier of the two
        _edge(repo, wid, sunny, n, rev=4)

        merge_coref(wid, repo, _cfg())

        edges = repo.list_edges(wid)
        assert len(edges) == 1
        # min(2, 4) == 2: the EARLIEST source reveal, never earlier than one of its sources.
        assert edges[0].revealed_chapter == 2
        assert {edges[0].source_id, edges[0].target_id} == {sunny, n}
        # The fence still hides the merged edge before its own revealed_chapter.
        assert fence.visible_edges(repo, wid, 1) == []  # rev 2 > n 1
        assert len(fence.visible_edges(repo, wid, 2)) == 1


def test_merge_is_idempotent() -> None:
    with Repository(":memory:") as repo:
        repo.initialize_schema()
        wid = repo.create_work(Work(slug="ss", title="SS"))
        sunny = _node(repo, wid, "Sunny", imp=10)
        you = _node(repo, wid, "you", imp=2)
        a = _node(repo, wid, "Nightmares", imp=3)
        _edge(repo, wid, you, a, rev=2)
        _edge(repo, wid, sunny, a, rev=3)

        first = merge_coref(wid, repo, _cfg())
        nodes_after = repo.count_nodes(wid)
        edges_after = repo.count_edges(wid)
        second = merge_coref(wid, repo, _cfg())

        assert first.nodes_merged == 1
        assert second.nodes_merged == 0  # nothing left to merge
        assert second.skipped_reason is not None
        assert repo.count_nodes(wid) == nodes_after  # graph unchanged by the 2nd run
        assert repo.count_edges(wid) == edges_after


def test_disabled_by_default_is_a_noop() -> None:
    with Repository(":memory:") as repo:
        repo.initialize_schema()
        wid = repo.create_work(Work(slug="ss", title="SS"))
        _node(repo, wid, "Sunny", imp=10)
        _node(repo, wid, "you", imp=2)

        report = merge_coref(wid, repo, WorkConfig())  # default: merge_self_reference=False

        assert report.skipped_reason is not None and report.skipped_reason.startswith("disabled")
        assert report.nodes_merged == 0
        assert {n.name for n in repo.list_nodes(wid)} == {"Sunny", "you"}


def test_auto_pov_tie_skips_but_clear_winner_merges() -> None:
    """Auto-detect POV: a tie at the top is ambiguous -> SKIP; a clear winner merges."""
    with Repository(":memory:") as repo:
        repo.initialize_schema()
        wid = repo.create_work(Work(slug="ss", title="SS"))
        _node(repo, wid, "Sunny", imp=5)
        _node(repo, wid, "Nephis", imp=5)  # tie at the top
        _node(repo, wid, "you", imp=1)

        tied = merge_coref(wid, repo, _cfg(pov=""))  # no explicit POV -> auto-detect
        assert tied.skipped_reason == "no unambiguous POV character"
        assert tied.nodes_merged == 0  # pronoun left alone when POV is unsure

    # Break the tie in a fresh work: Sunny clearly most important -> auto-detect merges.
    with Repository(":memory:") as repo:
        repo.initialize_schema()
        wid = repo.create_work(Work(slug="ss", title="SS"))
        _node(repo, wid, "Sunny", imp=9)  # clear winner
        _node(repo, wid, "Nephis", imp=4)
        _node(repo, wid, "you", imp=1)
        clear = merge_coref(wid, repo, _cfg(pov=""))
        assert clear.pov_character == "Sunny"
        assert clear.nodes_merged == 1
