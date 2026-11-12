"""Retrofit R5: a local-LLM recall pass that proposes; the R4 validator still disposes.

Why this exists, measured rather than assumed. R4c ended with 4 ring-1 edges at chapter
40 and **zero** edges in the Characters-only view, and its residue of 125 ungrounded
endpoints was dominated by pronouns (`She` x14) and common nouns. Two phases of grounding
work (R4b entities, R4c span snapping) moved the recall accounting by zero, because the
missing information is not in the spans -- it is in the prose. GLiNER-RelEx scores a
sentence in isolation; it cannot read "She had been his ward since the fire" two
sentences after Sorrel is named. An LLM can, so R5 gives it the sentence plus context and
asks for a closed-vocabulary answer.

What is deliberately unchanged (rule 8: the LLM proposes, the code disposes):

* every proposal goes through `extract/validator.py` untouched -- there is no bypass flag
  and no LLM-specific leniency;
* STATED still requires a label of BOTH participants inside the verbatim quote, so a
  proposal whose head is only "She" grades INFERRED and is stored but never served;
* the relation must be one of the twelve, or the proposal is discarded with a reason code.

Local-only, per CLAUDE.md: HTTP to Ollama through the stdlib ``urllib`` (no new package),
model files under ``.local\\ollama_models``, responses cached under ``.local\\llm_cache``
keyed by (model, prompt hash) so a re-run is free and reproducible. With Ollama off the
pass degrades to zero proposals and the R4c graph stands unchanged (rule 4).
"""

# ruff: noqa: E501 - `build_prompt` below emits PROMPT TEXT. Wrapping its lines
# would change what the model is asked, so they are left exactly as sent.

from __future__ import annotations

import hashlib
import json
import re
import urllib.error
import urllib.request
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from storyweave.db.models import NodeType
from storyweave.db.repository import Repository
from storyweave.query import fence

#: Sentence boundary: terminal punctuation, optional closing quotes, then whitespace.
_SENT_SPLIT = re.compile(r"(?<=[.!?][\"'”’)\]])\s+|(?<=[.!?])\s+")

#: The two types a relation candidate must connect. Places and Items are excluded on
#: purpose: R4c already extracts LOCATED_IN/OWNS well (22 and 17 edges at ch40), and the
#: hole this phase is aimed at is character-to-character.
_AGENT_TYPES = frozenset({NodeType.CHARACTER, NodeType.ORGANIZATION})


@dataclass(frozen=True)
class Candidate:
    """One sentence worth asking the LLM about."""

    chapter_ordinal: int
    sentence: str
    context: str  # up to 2 preceding sentences, for pronoun resolution
    entity_ids: tuple[int, ...]
    entity_names: tuple[str, ...]
    char_start: int
    char_end: int


def split_sentences(text: str) -> list[tuple[int, int, str]]:
    """``(start, end, sentence)`` triples whose slices reconstruct ``text`` exactly."""
    out: list[tuple[int, int, str]] = []
    pos = 0
    for piece in _SENT_SPLIT.split(text):
        if not piece:
            continue
        idx = text.find(piece, pos)
        if idx < 0:
            continue
        out.append((idx, idx + len(piece), piece))
        pos = idx + len(piece)
    return out


def find_candidates(
    repo: Repository, work_id: int, context_sentences: int = 2
) -> list[Candidate]:
    """Sentences naming >= 2 distinct Character/Organization entities, fenced.

    **Fenced the same way R4c's snapper is** (retrofit rule 1): a sentence in chapter *n*
    may only count entities whose ``revealed_chapter <= n``, so a candidate can never be
    built out of a reveal the reader has not reached.

    No relation-cue requirement. `docs/retrofit/R5_llm_recall_pass.md` task 1 asks for a
    cue word as well; this run deliberately omits it, because the cue lists were written
    for the R4 GRADE rule and requiring them here would let the LLM see only sentences the
    cue vocabulary already covers -- exactly the recall R4 measured as insufficient. The
    deviation is recorded in `evidence/retrofit/R5_RESULT.md`.
    """
    mentions = repo.list_mentions(work_id)
    nodes = {n.id: n for n in repo.list_nodes(work_id) if n.id is not None}
    out: list[Candidate] = []

    for chapter in repo.list_chapters(work_id):
        revealed = {n.id for n in fence.visible_nodes(repo, work_id, chapter.ordinal)}
        here = [
            m for m in mentions
            if m.chapter_ordinal == chapter.ordinal
            and m.node_id is not None
            and m.node_id in revealed
            and nodes[m.node_id].type in _AGENT_TYPES
        ]
        if not here:
            continue
        sentences = split_sentences(chapter.clean_text)
        for i, (start, end, sentence) in enumerate(sentences):
            inside = {m.node_id for m in here if start <= m.char_start < end}
            if len(inside) < 2:
                continue
            lo = max(0, i - context_sentences)
            context = " ".join(s for _st, _en, s in sentences[lo:i])
            ids = tuple(sorted(x for x in inside if x is not None))
            out.append(
                Candidate(
                    chapter_ordinal=chapter.ordinal,
                    sentence=sentence,
                    context=context,
                    entity_ids=ids,
                    entity_names=tuple(nodes[i2].name for i2 in ids),
                    char_start=start,
                    char_end=end,
                )
            )
    return out


# --------------------------------------------------------------------------- #
# The local model call. stdlib urllib only.
# --------------------------------------------------------------------------- #


@dataclass
class LlmReport:
    """What one R5 pass did, in numbers the phase report can quote."""

    candidates: int = 0
    called: int = 0
    cache_hits: int = 0
    unreachable: bool = False
    raw_proposals: int = 0
    per_reason: dict[str, int] = field(default_factory=dict)

    def note(self, reason: str) -> None:
        self.per_reason[reason] = self.per_reason.get(reason, 0) + 1


class OllamaClient:
    """Minimal Ollama /api/generate client with an on-disk response cache."""

    def __init__(
        self,
        model: str,
        host: str = "http://127.0.0.1:11434",
        cache_dir: Path | None = None,
        timeout: float = 180.0,
    ) -> None:
        self.model = model
        self.host = host.rstrip("/")
        self.cache_dir = cache_dir
        self.timeout = timeout
        if cache_dir is not None:
            cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, prompt: str) -> Path | None:
        if self.cache_dir is None:
            return None
        key = hashlib.sha256(f"{self.model}\x00{prompt}".encode()).hexdigest()
        return self.cache_dir / f"{key}.json"

    def available(self) -> bool:
        try:
            with urllib.request.urlopen(f"{self.host}/api/tags", timeout=10) as r:
                return bool(r.status == 200)
        except Exception:
            return False

    def generate(self, prompt: str, report: LlmReport) -> str | None:
        """The model's raw text, from cache when possible. None if unreachable."""
        path = self._cache_path(prompt)
        if path is not None and path.exists():
            report.cache_hits += 1
            return str(json.loads(path.read_text(encoding="utf-8"))["response"])
        body = json.dumps({
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            # Temperature 0: this is an extraction task, not a writing task, and a
            # reproducible run is worth more than variety.
            "options": {"temperature": 0.0, "num_predict": 512},
        }).encode()
        req = urllib.request.Request(
            f"{self.host}/api/generate", data=body,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                text = str(json.loads(r.read().decode())["response"])
        except Exception:
            report.unreachable = True
            return None
        report.called += 1
        if path is not None:
            path.write_text(json.dumps({"response": text}), encoding="utf-8")
        return text


def parse_json_relations(raw: str) -> list[dict[str, str]] | None:
    """Parse the model's reply defensively. None means malformed."""
    text = raw.strip()
    if text.startswith("```"):  # strip a markdown fence if the model added one
        text = re.sub(r"^```[a-zA-Z]*\s*|\s*```$", "", text)
    start, end = text.find("["), text.rfind("]")
    if start < 0 or end < start:
        return None
    try:
        parsed = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, list):
        return None
    out: list[dict[str, str]] = []
    for item in parsed:
        if isinstance(item, dict):
            out.append({str(k): str(v) for k, v in item.items()})
    return out


def build_prompt(candidate: Candidate, relations: Sequence[str], examples: str) -> str:
    """The extraction prompt: closed list, JSON only, quote copied verbatim."""
    names = ", ".join(f'"{n}"' for n in candidate.entity_names)
    context = candidate.context or "(none)"
    return f"""You extract relationships between characters from a fantasy novel.

Return ONLY a JSON array. No prose, no markdown, no explanation.

Each element must be exactly:
{{"relation": "<one of the allowed relations>", "head": "<name>", "tail": "<name>", "quote": "<text copied verbatim from THE SENTENCE>"}}

Allowed relations, and nothing else:
{", ".join(relations)}

Rules:
- Use ONLY the relations listed above. If none applies, return [].
- "head" and "tail" must each be one of these known entities: {names}
- "quote" must be copied character-for-character from THE SENTENCE below. Never from the context, never reworded.
- Only state a relationship the text actually asserts. Do not guess from vibes.
- If a pronoun refers to one of the known entities, you may still use the entity's name in "head"/"tail", but the quote must stay verbatim.

{examples}
CONTEXT (for understanding pronouns only, never quote from it):
{context}

THE SENTENCE:
{candidate.sentence}

JSON:"""
