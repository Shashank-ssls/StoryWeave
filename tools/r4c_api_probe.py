"""R4c probe: does the installed GLiNER-RelEx honour caller-supplied entity spans?

    .\\dev.ps1 -Ml
    python tools/r4c_api_probe.py

The R4c design hinges on one question the docstring alone cannot answer: passing
``input_spans`` is documented as limiting predictions to those spans, but documented and
working are different things. This runs the same sentence three ways -- free NER, and
then with the stored spans supplied -- and prints what comes back, so the choice between
the primary path (supply spans) and the fallback (snap returned spans to stored mentions)
is made on evidence.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from storyweave.config import get_settings  # noqa: E402
from storyweave.nlp.extractor import configure_hf_cache  # noqa: E402
from storyweave.nlp.relex import ENTITY_LABELS, R4_RELATION_PROMPTS  # noqa: E402

TEXT = (
    "Warden-Captain Orin Drask ran the Salt Quarter watch, and Juno Stray served "
    "under him for three years."
)


def show(tag: str, entities: list[dict[str, Any]], relations: list[dict[str, Any]]) -> None:
    print(f"\n--- {tag} ---")
    print("  entities:")
    for e in entities:
        print(f"    [{e['start']:>3},{e['end']:>3}] {e['text']!r:<28} {e.get('label')}")
    print("  relations:")
    if not relations:
        print("    (none)")
    for r in relations:
        print(f"    {r['head']['text']!r} -{r['relation']}-> {r['tail']['text']!r}"
              f"  ({r['score']:.2f})")


def main() -> int:
    settings = get_settings()
    configure_hf_cache(settings)
    from gliner import GLiNER  # noqa: PLC0415

    model = GLiNER.from_pretrained(settings.relex_model)
    prompts = list(R4_RELATION_PROMPTS)

    print("=" * 78)
    print("R4c API PROBE -- does input_spans work on this relex build?")
    print("=" * 78)
    print(f"\nmodel: {settings.relex_model}")
    print(f"text : {TEXT}")

    # 1. free NER, the R4/R4b behaviour.
    ents, rels = model.inference(
        texts=[TEXT], labels=ENTITY_LABELS, relations=prompts,
        threshold=settings.relex_ner_threshold,
        relation_threshold=settings.relex_rel_threshold,
        return_relations=True, flat_ner=False,
    )
    show("A. free NER (what R4/R4b did)", ents[0], rels[0])

    # 2. the same call, but told exactly which spans are entities. These are the spans a
    #    stored mention would supply -- note "Salt Quarter watch", the full organization,
    #    which free NER never proposes.
    spans = [
        {"start": TEXT.index("Orin Drask"), "end": TEXT.index("Orin Drask") + len("Orin Drask")},
        {"start": TEXT.index("Salt Quarter watch"),
         "end": TEXT.index("Salt Quarter watch") + len("Salt Quarter watch")},
        {"start": TEXT.index("Juno Stray"), "end": TEXT.index("Juno Stray") + len("Juno Stray")},
    ]
    print(f"\nsupplied spans: {[TEXT[s['start']:s['end']] for s in spans]}")
    try:
        ents2, rels2 = model.inference(
            texts=[TEXT], labels=ENTITY_LABELS, relations=prompts,
            threshold=settings.relex_ner_threshold,
            relation_threshold=settings.relex_rel_threshold,
            return_relations=True, flat_ner=False,
            input_spans=[spans],
        )
        show("B. WITH input_spans (the R4c primary path)", ents2[0], rels2[0])
        supplied = {TEXT[s["start"]:s["end"]] for s in spans}
        returned = {e["text"] for e in ents2[0]}
        print(f"\n  supplied spans returned as entities: {sorted(supplied & returned)}")
        print(f"  entities NOT among the supplied spans: {sorted(returned - supplied)}")
        print("\nVERDICT: input_spans is ACCEPTED by this build."
              if returned else "\nVERDICT: input_spans accepted but returned nothing.")
    except Exception as exc:  # noqa: BLE001 - the whole point is to see the failure
        print(f"\nB. input_spans RAISED: {type(exc).__name__}: {exc}")
        print("\nVERDICT: input_spans is NOT usable -- R4c must use the snapping fallback.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
