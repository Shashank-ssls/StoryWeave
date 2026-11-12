"""Retrofit R5: candidate selection and defensive parsing for the LLM recall pass.

No test here calls a model. The LLM is an enhancement layer (rule 4), so what has to be
pinned is the code AROUND it: which sentences get asked about, that the fence still binds
when they are chosen, and that a model returning rubbish cannot corrupt the graph.
"""

from __future__ import annotations

from pathlib import Path

from storyweave.db.models import (
    Chapter,
    Chunk,
    ExtractionMethod,
    Mention,
    Node,
    NodeType,
    Work,
)
from storyweave.db.repository import Repository
from storyweave.extract.llm_relations import (
    Candidate,
    LlmReport,
    OllamaClient,
    build_prompt,
    find_candidates,
    parse_json_relations,
    split_sentences,
)

RELATIONS = ["KIN_OF", "SERVES", "ALLY_OF"]


# --- sentence splitting ------------------------------------------------------ #


def test_split_sentences_slices_reconstruct_the_text() -> None:
    text = 'He left. "Did he?" she asked. No one answered.'
    for start, end, sentence in split_sentences(text):
        assert text[start:end] == sentence


def test_split_sentences_keeps_a_closing_quote_with_its_sentence() -> None:
    text = '"Lucky catch," Juno said. Ettie frowned.'
    assert len(split_sentences(text)) == 2


# --- defensive parsing ------------------------------------------------------- #


def test_parse_accepts_a_bare_json_array() -> None:
    parsed = parse_json_relations('[{"relation": "KIN_OF", "head": "A", "tail": "B"}]')
    assert parsed is not None
    assert parsed[0]["relation"] == "KIN_OF"


def test_parse_strips_a_markdown_fence() -> None:
    raw = '```json\n[{"relation": "SERVES", "head": "A", "tail": "B"}]\n```'
    parsed = parse_json_relations(raw)
    assert parsed is not None and parsed[0]["relation"] == "SERVES"


def test_parse_recovers_an_array_surrounded_by_chatter() -> None:
    """Small models preface answers. The array is still extractable."""
    raw = (
        "Sure! Here is the JSON:\n"
        '[{"relation": "ALLY_OF", "head": "A", "tail": "B"}]\n'
        "Hope that helps."
    )
    parsed = parse_json_relations(raw)
    assert parsed is not None and len(parsed) == 1


def test_parse_returns_none_on_malformed_json() -> None:
    assert parse_json_relations("[{oops") is None
    assert parse_json_relations("I could not find any relationships.") is None


def test_parse_returns_empty_list_for_an_empty_answer() -> None:
    """[] is a VALID answer meaning 'no relation here', not a parse failure."""
    assert parse_json_relations("[]") == []


def test_parse_ignores_non_object_elements() -> None:
    parsed = parse_json_relations('["KIN_OF", {"relation": "KIN_OF"}]')
    assert parsed is not None and len(parsed) == 1


# --- the prompt -------------------------------------------------------------- #


def _candidate() -> Candidate:
    return Candidate(
        chapter_ordinal=4, sentence="Orin Drask served Cassian for years.",
        context="They had met at the Chancery.", entity_ids=(1, 2),
        entity_names=("Orin Drask", "Cassian"), char_start=0, char_end=36,
    )


def test_prompt_names_only_the_closed_relation_list() -> None:
    prompt = build_prompt(_candidate(), RELATIONS, "")
    for relation in RELATIONS:
        assert relation in prompt
    assert "Betrayed" not in prompt and "Respects" not in prompt


def test_prompt_forbids_quoting_from_the_context() -> None:
    prompt = build_prompt(_candidate(), RELATIONS, "")
    assert "never quote from it" in prompt
    assert "copied character-for-character" in prompt


def test_prompt_constrains_the_endpoints_to_known_entities() -> None:
    prompt = build_prompt(_candidate(), RELATIONS, "")
    assert '"Orin Drask", "Cassian"' in prompt


# --- candidate selection, and the fence -------------------------------------- #


def _work_with(tmp_path: Path, reveal_second: int) -> tuple[Repository, int]:
    """Two characters in one sentence; the second is revealed at ``reveal_second``."""
    repo = Repository(tmp_path / "r5.sqlite")
    repo.initialize_schema()
    work_id = repo.create_work(Work(slug="w", title="W"))
    text = "Alder served Brenna faithfully. Nothing else happened that day."
    chapter_id = repo.add_chapter(Chapter(
        work_id=work_id, ordinal=1, title="One", clean_text=text, content_hash="h"))
    repo.add_chunk(Chunk(chapter_id=chapter_id, work_id=work_id, ordinal=0,
                         char_start=0, char_end=len(text), text=text, content_hash="c"))
    ids = []
    for name, revealed in (("Alder", 1), ("Brenna", reveal_second)):
        ids.append(repo.add_node(Node(
            work_id=work_id, name=name, type=NodeType.CHARACTER,
            first_seen_chapter=1, revealed_chapter=revealed,
            extraction_method=ExtractionMethod.GLINER)))
    for node_id, name in zip(ids, ("Alder", "Brenna"), strict=True):
        repo.add_mention(Mention(
            work_id=work_id, chapter_id=chapter_id, chapter_ordinal=1, ordinal=0,
            surface=name, type=NodeType.CHARACTER,
            char_start=text.index(name), char_end=text.index(name) + len(name),
            score=1.0, node_id=node_id))
    return repo, work_id


def test_a_sentence_with_two_revealed_characters_is_a_candidate(tmp_path: Path) -> None:
    repo, work_id = _work_with(tmp_path, reveal_second=1)
    candidates = find_candidates(repo, work_id)
    assert len(candidates) == 1
    assert set(candidates[0].entity_names) == {"Alder", "Brenna"}
    repo.close()


def test_the_fence_binds_on_candidate_selection(tmp_path: Path) -> None:
    """An entity revealed later must not make a candidate in an earlier chapter.

    Otherwise the LLM pass is a side channel: it would be asked about a pair the reader
    has not met, and any edge it produced would be reasoned from a future reveal.
    """
    repo, work_id = _work_with(tmp_path, reveal_second=9)
    assert find_candidates(repo, work_id) == []
    repo.close()


def test_a_sentence_with_one_entity_is_not_a_candidate(tmp_path: Path) -> None:
    repo, work_id = _work_with(tmp_path, reveal_second=1)
    candidates = find_candidates(repo, work_id)
    # The second sentence names nobody, so exactly one candidate, not two.
    assert all("Nothing else" not in c.sentence for c in candidates)
    repo.close()


# --- graceful degradation ---------------------------------------------------- #


def test_an_unreachable_server_yields_none_and_is_flagged() -> None:
    """Rule 4: with no LLM the system still works. No crash, no partial write."""
    client = OllamaClient("qwen2.5:7b", host="http://127.0.0.1:1")  # nothing listens
    report = LlmReport()
    assert client.generate("hello", report) is None
    assert report.unreachable is True
    assert client.available() is False


def test_the_cache_is_keyed_by_model_and_prompt(tmp_path: Path) -> None:
    a = OllamaClient("model-a", cache_dir=tmp_path)
    b = OllamaClient("model-b", cache_dir=tmp_path)
    assert a._cache_path("p") != b._cache_path("p")
    assert a._cache_path("p") != a._cache_path("q")
    assert a._cache_path("p") == a._cache_path("p")


def test_a_cached_response_is_returned_without_a_call(tmp_path: Path) -> None:
    import json

    client = OllamaClient("m", cache_dir=tmp_path)
    path = client._cache_path("prompt")
    assert path is not None
    path.write_text(json.dumps({"response": "[]"}), encoding="utf-8")
    report = LlmReport()
    assert client.generate("prompt", report) == "[]"
    assert report.cache_hits == 1
    assert report.called == 0
