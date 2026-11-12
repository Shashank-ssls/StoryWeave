# "The Ninth House" — story bible

Original CC0 fantasy court-intrigue serial, written as StoryWeave's second demo work
(DESIGN_SPEC D8). Slug: `the-ninth-house`. Target: 40 chapters, 200–350 words each,
75–90 named entities across all 8 ontology types, 4–5 factions of 5+ members (org
folding), 5 arcs, 7 identity edges across 6 distinct pairs (one deepening).

This bible is the ground truth for: (1) grading the real GLiNER extraction pass
(Part B.3 precision/recall), (2) hand-curating the Tier-2/3 records the LLM would
normally produce, (3) the citation-gate test (every identity edge's `evidence_span`
must occur verbatim in its reveal chapter's text — the confirming sentence for each
reveal below is drafted here and finalized verbatim when that chapter is written).

---

## 1. Premise

King Aldric of Thornmere dies without a clear heir. A Regency Council of the realm's
Great Houses governs the capital, Aldenreach, until the Choosing — a ceremony months
away that will name the next monarch. Sorrel Quill, a low-born scribe in the Chancery
of Records, finds a coded ledger implicating the Regent's own household in something
older and stranger than a succession dispute: the Umbral Choir, remnant of the
outlawed Ninth House, and its forbidden soul-craft — the power to move a mind out of
one body, one name, one life, and into another.

## 2. Setting (Places — Place type, 11 total)

| Name | Subtype | Notes |
|---|---|---|
| Thornmere | Region | the kingdom |
| Aldenreach | City | the capital |
| Aldenreach Keep | Building | seat of the Regency |
| the Chancery of Records | Building | Sorrel's workplace |
| the Salt Quarter | Region | dockside district, Warden patrol ground |
| Vell Hall | Building | House Vell's townhouse |
| the Undercroft | Building | the Umbral Choir's hidden sanctum, beneath the Salt Quarter |
| Marrowfall | Realm | the Ninth House's ruined ancestral seat, outside the city |
| the Bone Market | Landmark | a black market in the Salt Quarter |
| the Ashen Court | Landmark | ceremonial plaza where the Choosing is held |
| Sallowmere | Realm | neighbouring realm, sends an envoy in Arc V |

## 3. Factions (Organization type, 7 total; 4 have 5+ Character members)

- **House Ashcombe** (Kingdom) — the Regent's house, currently governing. 6 members:
  Cassian Ashcombe, Ione Ashcombe, Ser Robart Kell, Bellamy Thorne, Maester Ysolde Fenn,
  Pello Ashcombe.
- **House Vell** (Kingdom) — the leading rival house. 5 members: Meraude Vell, Ser Tobin
  Vell, Corwin Vell, Sable Vell, Hask.
- **the Salt Wardens** (Guild) — the city watch of the Salt Quarter. 5 members:
  Orin Drask, Pryn Voss, Casimir Lowe, Ettie Marsh, Juno Stray.
- **the Umbral Choir** (Cult) — the Ninth House's secret remnant. 5 members: Vesper
  (alias "Mistress Vey"), Alden, Mira Quell, Thessaly, Oswin.
- **the Regency Council** (Faction) — the governing body of Houses; Cassian, Meraude and
  two lesser lords sit on it (Fennick Oswald, Brenna Oswald — House Oswald, not detailed
  as a full 5-member faction, referenced as a pair).
- **the Chancery Scribes** (Guild) — Sorrel's own minor guild. Members named loosely
  (Sorrel + Denna Ashford, not a folding-relevant faction).
- **the Sallow Concord** (Corporation) — Sallowmere's trade delegation, arrives Arc V
  with Envoy Petra Hollis.

## 4. Cast (Character type, 32 total)

**House Ashcombe:** Cassian Ashcombe (Lord Regent), Ione Ashcombe (his sister),
Ser Robart Kell (guard-captain), Bellamy Thorne (steward), Maester Ysolde Fenn
(physician/scholar), Pello Ashcombe (young nephew, child heir candidate).

**House Vell:** Meraude Vell (Duchess), Ser Tobin Vell (her son), Corwin Vell (her
nephew), Sable Vell (her daughter — see identity thread), Hask (huntsman/enforcer).

**Salt Wardens:** Orin Drask (Warden-Captain), Pryn Voss, Casimir Lowe, Ettie Marsh,
Juno Stray (see identity thread).

**Umbral Choir:** Vesper / "Mistress Vey" (see identity thread), Alden (posing as a
tutor), Mira Quell (young initiate — see identity thread), Thessaly (archivist — see
identity thread), Oswin.

**Regency Council (minor House):** Fennick Oswald, Brenna Oswald.

**Chancery:** Sorrel Quill (protagonist — see identity thread), Denna Ashford (rival
scribe).

**Historical / identity-thread nodes** (introduced as lore before their identity
connection lands — see §6): Aurelia Marrow (the lost Ninth House scion), Kaelen the
Unmaker (Ninth-House-era sorcerer-king), the Wanderer (a soul from beyond Thornmere).

**Late-introduced (Arc V, no earlier mention — for the "not yet met" search tests):**
Envoy Petra Hollis (Sallowmere), Magistrate Wyle (arbiter of the Choosing).

**Deceased, referenced only:** King Aldric (dead before ch1; never a living node with
dialogue, but named/first-seen ch1 as context).

## 5. Items (9), Abilities (6), Concepts (8), Events (8), Titles (8)

**Items:** the Marrow Seal (Relic), the coded ledger (Resource), Kaelen's Grimoire
(Relic), the Ashcombe Blade (Weapon), the iron stave (Weapon), a salt-glass vial
(Consumable), the Regent's signet ring (Treasure), the Thornbite (Weapon, Corwin/Vell's
dagger), the ninth coin (Artifact, a Choir recognition token).

**Abilities** (power system: Marrow-craft, see Concepts): Soul-sight (Aspect),
Memory-warding (Skill), the Unmaking (Technique), Quickhand (Skill, Sorrel's), Voice of
Command (Talent, Cassian's), Warden's Discipline (Passive).

**Concepts:** Marrow-craft (PowerSystem), the Ninth House (Phenomenon), the Long
Silence (Phenomenon, historical), the Grey Road (Phenomenon, between-worlds), Thornmere
Succession Law (Law), the Salt Tithe (Law), the Choir Cipher (Language), the Choosing
(as an institution/tradition — distinct from the ceremony Event below, this Concept
entry is the LAW that defines it; the Event is the specific ceremony in ch40).

**Events:** the Mourning Bell (Ceremony, King Aldric's funeral, ch1), the Regency
Council's First Sitting (Ceremony, ch2), the Salt Quarter Raid (Battle, ch13), the Long
Silence (Disaster, historical, referenced not witnessed), the Vell Masque (Ceremony,
ch18), the Undercroft Collapse (Disaster, ch33), the Sallow Accord signing (Ceremony,
ch36), the Choosing (Ceremony, ch40).

**Titles:** Lord Regent (Political), Warden-Captain (Combat), Choirmaster (Religious),
Duchess (Political), Maester (Honorary), Scion of the Ninth House (Honorary), Envoy
(Political), Magistrate (Political).

Total named entities: 32 + 11 + 7 + 9 + 6 + 8 + 8 + 8 = **89**, within the 60–90 target.

## 6. Identity reveal schedule (7 edges, 6 distinct pairs, staggered, one deepening)

Each row's "confirming sentence" is the intended `evidence_span` — drafted here,
finalized verbatim when that chapter is actually written (the citation-gate test checks
the FINAL text, not this draft).

| # | Ch | Relation | Pair | Confirming sentence (drafted) |
|---|---|---|---|---|
| 1 | 5 | ALIAS | Mistress Vey ↔ Vesper | "Mistress Vey untied her apron, and under it she wore the grey sash of the Choir — Vesper had never been a laundress at all." |
| 2 | 10 | SECRET_IDENTITY | Juno Stray ↔ Sable Vell | "Warden Juno Stray pulled back her hood, and Sorrel saw the Vell chin she'd only known from a portrait: Sable Vell, the Duchess's vanished daughter, had been standing watch in the Salt Quarter for a year." |
| 3 | 16 | ALIAS | the Choirmaster ↔ Thessaly | "The old archivist folded her hands and said, without any weight at all, that she was the Choirmaster, and had been since before Sorrel was born." |
| 4 | 20 | SECRET_IDENTITY | Sorrel Quill ↔ Aurelia Marrow | "The ledger's last page named the scribe who would carry it: not Sorrel Quill, a chancery orphan, but Aurelia Marrow, the Ninth House's last acknowledged daughter." |
| 5 | 28 | REINCARNATION | Cassian Ashcombe ↔ Kaelen the Unmaker | "Thessaly held the grimoire beside the Regent's sleeping face and said the old name plainly: Kaelen, worn thin over three centuries, had woken up as Cassian Ashcombe." |
| 6 | 34 | REINCARNATION (deepening of #4) | Sorrel Quill ↔ Aurelia Marrow | "It was not blood that had made her a Marrow, Thessaly said — blood was only ever the door. The soul that opened it had done this before, and Aurelia Marrow was the name it wore the last time." |
| 7 | 37 | TRANSMIGRATED_INTO | Mira Quell ↔ the Wanderer | "Mira Quell had always known the names of places she had never been, and now, on the Grey Road's threshold, she finally said why: she had walked in from outside Thornmere altogether, a Wanderer poured into a Choir initiate's small body." |

Staggering: early (ch5, ch10), middle (ch16, ch20), late (ch28, ch34, ch37) — spans
Arc I–V. `first_seen_chapter` for the "surface" identity in each pair is always EARLIER
than the reveal (the alias/undercover persona is introduced first; the reader only
connects the dots at the reveal chapter) — mirrors Hollow Crown's own convention
exactly.

## 7. Arcs (5, for `storyweave.toml` D6 config)

| # | Name | Chapters |
|---|---|---|
| 1 | The Mourning Bell | 1–8 |
| 2 | The Salt Cipher | 9–16 |
| 3 | The Vell Masque | 17–26 |
| 4 | The Undercroft | 27–34 |
| 5 | The Choosing | 35–40 |

## 8. Chapter-by-chapter outline

1. King Aldric's funeral (the Mourning Bell). Sorrel introduced at the Chancery,
   cataloguing the dead king's effects. Rumor of the Ninth House surfaces in passing.
2. The Regency Council's First Sitting: Cassian, Meraude, the Oswalds. Ione and Robart
   Kell introduced. Sorrel assigned to copy a water-damaged ledger.
3. Sorrel meets Mistress Vey, a laundress who trades gossip for bread. Warden Juno
   Stray patrols the Salt Quarter; introduced on watch.
4. The ledger's cipher resists Sorrel's usual tricks. Denna Ashford needles her at the
   Chancery. Corwin Vell first seen courting Council favor.
5. **Reveal 1 (ALIAS)**: Vey = Vesper. Sorrel follows Vey into the Salt Quarter at dusk.
6. Thessaly introduced at the Undercroft archive (unnamed as Choirmaster yet). Bellamy
   Thorne's loyalty to Cassian established in a quiet, ordinary scene.
7. Mira Quell introduced, a young Choir initiate running errands for Thessaly. Pello
   Ashcombe's claim to the succession discussed by the Houses.
8. Arc I close: Sorrel decides to keep investigating rather than hand the ledger to
   Kell. House Vell's ambitions made explicit in a council argument.
9. Arc II opens. Casimir Lowe and Ettie Marsh introduced on the Warden roster. Hask
   menaces a Bone Market trader for House Vell.
10. **Reveal 2 (SECRET_IDENTITY)**: Juno Stray = Sable Vell.
11. Meraude Vell privately confronts the fact her daughter is alive and hiding; Tobin
    Vell disapproves of pursuing her.
12. Sorrel cross-references the ledger against Chancery tax rolls; the Salt Tithe
    explained. Oswin (Choir) appears delivering a coded message.
13. **The Salt Quarter Raid** (Event): Orin Drask leads the Wardens against a smuggling
    ring; Juno's dual loyalties nearly surface.
14. Alden, posing as a tutor, is shown teaching Pello Ashcombe — first hint the Choir
    has reach inside House Ashcombe itself.
15. Sorrel and Vesper meet openly for the first time since the reveal; Vesper explains
    the Choir Cipher partially, withholding the rest.
16. **Reveal 3 (ALIAS)**: the Choirmaster = Thessaly.
17. Arc III opens with the Vell Masque invitations going out. Fennick and Brenna Oswald
    angle for a marriage alliance with House Vell.
18. **The Vell Masque** (Event): Corwin Vell and Sorrel cross paths in disguise; Ysolde
    Fenn treats a masked guest for a Marrow-craft side-effect (soul-sight migraine).
19. Sorrel realizes the ledger's final page is written in a hand that matches old
    Ninth House records, not a modern one. Kaelen's Grimoire mentioned for the first
    time (as a rumor, not yet located).
20. **Reveal 4 (SECRET_IDENTITY)**: Sorrel Quill = Aurelia Marrow.
21. Sorrel confronts Thessaly; the Choir's real interest in her is explained only
    partially. Robart Kell grows suspicious of Sorrel's absences.
22. Ione Ashcombe, sympathetic to Sorrel, shields her from Kell without knowing why.
23. Casimir Lowe and Pryn Voss stumble on Choir activity near the Bone Market; Orin
    Drask orders a quiet watch rather than a second raid.
24. Sorrel is taken to Marrowfall for the first time. The ruin, the Marrow Seal, and
    the Ninth House's fall (the Long Silence) are described together.
25. The Marrow Seal is placed in Sorrel's hands; nothing happens, which unsettles
    Thessaly more than if it had. Kaelen the Unmaker named directly as history for the
    first time (node first_seen here, ahead of the ch28 reveal).
26. Arc III closes: Corwin Vell steals a look at Sorrel's ledger copy; House Vell now
    suspects there's more to the "chancery girl" than Kell's reports say.
27. Arc IV opens. Cassian Ashcombe shown privately unwell — a soul-sight migraine like
    the masked guest's in ch18, worse.
28. **Reveal 5 (REINCARNATION)**: Cassian Ashcombe = Kaelen the Unmaker.
29. Thessaly and Vesper argue over whether to tell Cassian what he is; Mira Quell
    overhears more than she should.
30. Bellamy Thorne notices Cassian's changed manner and, loyal but frightened, tells no
    one — a quiet character beat, not a reveal.
31. Sorrel and Cassian meet directly for the first time since ch2; neither says what
    they now suspect about the other.
32. Hask, on Vell's orders, breaks into the Chancery for the ledger; Sorrel already
    moved it to the Undercroft.
33. **The Undercroft Collapse** (Event): Hask's break-in triggers a Marrow-craft ward;
    the Undercroft is damaged, Oswin injured, the Choir's hiding place compromised.
34. **Reveal 6 (REINCARNATION, deepening of #4)**: Sorrel Quill = Aurelia Marrow
    deepens — not blood-heir but the same soul, come again.
35. Arc V opens. Envoy Petra Hollis arrives from Sallowmere for the Sallow Accord,
    unaware of the succession crisis beneath the pageantry.
36. **The Sallow Accord signing** (Event). Magistrate Wyle introduced, appointed to
    arbitrate the Choosing.
37. **Reveal 7 (TRANSMIGRATED_INTO)**: Mira Quell = the Wanderer.
38. Cassian, now aware of what he carries, chooses to stand for the Choosing anyway;
    Meraude Vell, informed by Corwin, considers exposing him and decides — for reasons
    of her own house's stability — not to.
39. Sorrel decides her Ninth House name is not a throne to claim, and gives the Marrow
    Seal to Thessaly rather than keep it; the Choir's long secrecy begins to end by her
    choice, not Cassian's.
40. **The Choosing** (Event): Cassian is named Thornmere's monarch under Magistrate
    Wyle's arbitration; Sorrel watches from the Chancery scribes' gallery, her name
    still just Sorrel Quill in every public record. Book closes on the Ashen Court at
    dusk.

## 9. Extraction ground truth (for Part B.3 grading)

Every named entity in §2–§5 above must appear, in-text, in the chapter(s) implied by
the outline in §8, under the exact surface form used in these tables (surface-form
consistency matters for GLiNER + the clustering step). Grading in `INTEGRATION.md`
compares the real `extract` pass's node list against this bible's 89-entity roster:
precision = (bible-matching nodes) / (all extracted nodes), recall = (bible entities
found) / 89.
