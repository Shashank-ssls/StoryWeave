"""Retrofit R4b: the group-noun head rule that recovers common-noun-headed Organizations.

The rule's danger is not that it misses things, it is that it invents them: it fires on
a surface pattern, so every test below is about what it must REFUSE. Two of the refusals
(sentence-initial determiners, sentence-initial conjunctions) are regression tests for
false positives this rule actually produced during R4b and that widening the function-word
guard removed -- see `evidence/retrofit/R4b_RESULT.md` §3.
"""

from __future__ import annotations

from storyweave.nlp.orgs import GROUP_NOUNS, find_organization_spans


def surfaces(text: str) -> list[str]:
    return [s.surface for s in find_organization_spans(text)]


# --- what it must FIND ------------------------------------------------------ #


def test_a_proper_modifier_plus_group_noun_is_an_organization() -> None:
    assert surfaces("He joined the Salt Quarter watch that spring.") == [
        "Salt Quarter watch"
    ]


def test_a_possessive_modifier_counts() -> None:
    """"Cassian's guard" is as much a named body as "the Salt Quarter watch"."""
    assert surfaces("Cassian's guard held the gate.") == ["Cassian's guard"]


def test_the_head_noun_may_be_capitalised() -> None:
    """A book may capitalise the head: "the Iron Order" is the same construction."""
    assert surfaces("She rode for the Iron Order.") == ["Iron Order"]


def test_the_article_is_not_part_of_the_name() -> None:
    for span in find_organization_spans("the Salt Quarter watch"):
        assert not span.surface.lower().startswith("the ")


def test_offsets_index_the_text_exactly() -> None:
    text = "Word word the Salt Quarter watch, and more."
    span = find_organization_spans(text)[0]
    assert text[span.char_start : span.char_end] == span.surface


# --- what it must REFUSE ---------------------------------------------------- #


def test_a_bare_group_noun_is_not_an_organization() -> None:
    """"the watch" is a common noun. Only a NAMED body is promoted."""
    assert surfaces("The watch was quiet that night.") == []


def test_a_sentence_initial_article_is_not_a_modifier() -> None:
    """Regression: this rule once promoted 'A ring' out of "A ring of smugglers"."""
    assert surfaces("A ring of smugglers worked the docks.") == []
    assert surfaces("The chancery kept its own records.") == []


def test_a_sentence_initial_conjunction_is_not_a_modifier() -> None:
    """Regression: this rule once promoted 'And House' and 'If House'."""
    assert surfaces("And House Vell said nothing.") == []
    assert surfaces("If House Oswald agrees, we go.") == []


def test_a_capitalised_word_that_merely_starts_with_a_function_word_still_counts() -> None:
    """The guard is on whole words: "Theodore" must not be blocked by "The"."""
    assert surfaces("Theodore Guild sent word.") == ["Theodore Guild"]


def test_a_span_the_model_already_found_is_not_duplicated() -> None:
    text = "He joined the Salt Quarter watch."
    start = text.index("Salt Quarter watch")
    existing = frozenset({(start, start + len("Salt Quarter watch"))})
    assert find_organization_spans(text, existing) == []


def test_an_overlapping_nested_mention_does_not_block_the_promotion() -> None:
    """The nested Place is the whole problem, so overlap must NOT suppress the span."""
    text = "He joined the Salt Quarter watch."
    start = text.index("Salt Quarter")
    nested = frozenset({(start, start + len("Salt Quarter"))})  # the Place GLiNER found
    assert surfaces_with(text, nested) == ["Salt Quarter watch"]


def surfaces_with(text: str, existing: frozenset[tuple[int, int]]) -> list[str]:
    return [s.surface for s in find_organization_spans(text, existing)]


# --- the vocabulary --------------------------------------------------------- #


def test_group_nouns_are_collective_nouns_not_places() -> None:
    """A sanity check on the list itself: no entry may be a bare place word."""
    for word in ("city", "town", "keep", "castle", "road", "market", "quarter"):
        assert word not in GROUP_NOUNS


def test_a_per_work_override_replaces_the_list() -> None:
    """Knobs are data: a book whose organizations are headed by invented nouns."""
    text = "She spoke for the Salt Quarter kithe."
    assert surfaces(text) == []
    assert [
        s.surface for s in find_organization_spans(text, group_nouns=("kithe",))
    ] == ["Salt Quarter kithe"]
