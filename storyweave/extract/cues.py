"""Per-relation cue vocabulary for the R4 grade rule.

PROVENANCE, stated once so the phase report can cite it (integrity rule 2 of the R4
brief): these lists were written BEFORE any scoring run and WITHOUT reading the
annotation's gold relations or evidence quotes. Each entry comes from one of two
places, both of which predate the answer key:

1. The relation vocabulary itself -- ``SPEC.md`` §5.3 names and the natural-language
   prompts already sitting in ``storyweave/nlp/relex.py`` since Phase 7a ("ally of",
   "serves under", "married to", ...). These are the project's own words for each
   relation.
2. General English vocabulary for the same idea (a thesaurus pass over 1, done by
   hand): "slew" alongside "killed", "betrothed" alongside "married".

``docs/ONTOLOGY.md`` is named as a source in the R4 brief but does not exist in this
repository; SPEC.md §5.3 is the ontology of record and is used in its place. That
substitution is recorded in ``evidence/retrofit/R4_RESULT.md`` rather than passed over.

A cue is matched on WORD BOUNDARIES against the lowercased quote, so "in" matches
"in the Salt Quarter" but not "brigandine". Per-work overrides live in
``storyweave.toml`` (``[relations.cues]``) -- knobs are data, never code.

Known precision risk, recorded in advance rather than discovered afterwards:
LOCATED_IN's cues include bare prepositions ("in", "at", "from"), because that IS how
English states location. The cue test is therefore weak for that one relation and the
"both participants named in the quote" test is carrying the whole burden. This was not
tuned away after seeing the score.
"""

from __future__ import annotations

from storyweave.db.models import Relation

#: Relation -> the cue words/phrases whose presence in a quote makes it STATED.
DEFAULT_CUES: dict[Relation, tuple[str, ...]] = {
    Relation.KIN_OF: (
        "father", "mother", "son", "daughter", "brother", "sister", "uncle", "aunt",
        "nephew", "niece", "cousin", "grandfather", "grandmother", "grandson",
        "granddaughter", "wife", "husband", "spouse", "kin", "kinsman", "parent",
        "parents", "child", "sibling", "family", "blood", "stepfather", "stepmother",
        "half-brother", "half-sister", "in-law", "widow", "widower",
    ),
    Relation.ROMANTIC_WITH: (
        "love", "loved", "loves", "lover", "beloved", "in love", "courted", "courting",
        "kissed", "betrothed", "sweetheart", "married", "marry", "wedded", "wed",
        "suitor", "mistress", "paramour", "affair",
    ),
    Relation.ALLY_OF: (
        "ally", "allies", "allied", "alliance", "friend", "friends", "friendship",
        "comrade", "companion", "partner", "alongside", "stood with", "fought with",
        "side by side", "sworn to", "pact", "together against",
    ),
    Relation.ENEMY_OF: (
        "enemy", "enemies", "foe", "foes", "hated", "hates", "hatred", "opposed",
        "against", "adversary", "nemesis", "feud", "war with", "at odds", "loathed",
        "despised",
    ),
    Relation.SERVES: (
        "serves", "served", "serve", "service", "servant", "retainer", "works for",
        "worked for", "obeyed", "obeys", "answered to", "answers to", "sworn to",
        "under", "in the pay of", "orders from",
    ),
    Relation.MENTOR_OF: (
        "taught", "teach", "teacher", "mentor", "mentored", "tutor", "tutored",
        "trained", "training", "apprentice", "apprenticed", "student", "pupil",
        "master", "instructed", "schooled", "raised", "took on", "lessons",
    ),
    Relation.KILLED: (
        "killed", "kill", "kills", "slew", "slain", "slay", "murdered", "murder",
        "murderer", "stabbed", "strangled", "poisoned", "executed", "put to death",
        "cut down", "struck down", "death of", "hanged", "drowned",
    ),
    Relation.SAME_AS: (
        "is", "was", "really", "truly", "actually", "none other than", "alias",
        "known as", "called", "same", "himself", "herself", "themselves", "revealed",
        "in truth", "under the name",
    ),
    Relation.MEMBER_OF: (
        "member", "members", "belongs", "belonged", "joined", "joins", "initiate",
        "novice", "sworn", "enlisted", "one of", "ranks", "of the", "among the",
        "inducted", "brotherhood",
    ),
    Relation.LEADS: (
        "leads", "led", "leader", "commands", "commanded", "commander", "captain",
        "heads", "headed", "rules", "ruled", "ruler", "ran", "runs", "in charge",
        "master of", "chief", "lord of", "lady of", "at the head of",
    ),
    Relation.OWNS: (
        "owns", "owned", "owner", "carried", "carries", "bore", "bears", "wielded",
        "wields", "possessed", "possesses", "kept", "keeps", "belonged to", "his",
        "her", "their", "property", "hers", "held",
    ),
    Relation.LOCATED_IN: (
        "in", "at", "within", "inside", "lives in", "lived in", "stood in", "from",
        "near", "housed", "dwelt", "dwells", "of the", "outside", "beneath", "under",
    ),
}

#: Kin nouns, for the KIN_OF guard (R4 task 3e). A subset of the KIN_OF cues: only the
#: words that NAME a relative, not the abstract ones ("family", "blood") -- the guard
#: asks whether a specific relative word is attached to a participant.
KIN_NOUNS: tuple[str, ...] = (
    "father", "mother", "son", "daughter", "brother", "sister", "uncle", "aunt",
    "nephew", "niece", "cousin", "grandfather", "grandmother", "grandson",
    "granddaughter", "wife", "husband", "spouse", "kinsman", "parent", "parents",
    "child", "sibling", "stepfather", "stepmother", "half-brother", "half-sister",
    "widow", "widower",
)
