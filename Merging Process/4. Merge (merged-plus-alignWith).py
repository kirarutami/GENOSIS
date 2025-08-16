# -*- coding: utf-8 -*-
"""ontology_merge.py — merge + provenance + alignment

Pipeline
========
1. **Pass‑1**   Create *skeleton* entities in the merged ontology, preserving
   the original OWL type (Class, ObjectProperty, DatatypeProperty, …).
2. **Pass‑2**   Copy **rdfs:subClassOf** assertions (+ `sourceOrigin`).
3. **Pass‑3**   Copy **rdfs:domain / rdfs:range** (union from every source).
4. **Pass‑4**   Copy every `rdfs:comment`, but stored in a dedicated
   annotation property per ontology: `OSNcomment`, `MPcomment`,
   `MCSScomment`, `OFBcomment`.
5. **Pass‑5**   Append explicit `alignWithXXX` annotations for every entity
   that appears in the YES‑labelled alignment TSV files.
"""
from __future__ import annotations
from owlready2 import *  # type: ignore
import types, re, codecs, pandas as pd
from io import BytesIO
from pathlib import Path
from collections import defaultdict

# ─────────────────────────── CONFIG ────────────────────────────
ONTOLOGY_PATHS = {
    "OSN" : r"D:\Dokumentasi\LLMs4OM\datasets\local-ont\Local OSN.rdf",
    "MP"  : r"D:\Dokumentasi\LLMs4OM\datasets\local-ont\Local MP.rdf",
    "MCSS": r"D:\Dokumentasi\LLMs4OM\datasets\local-ont\Local MCSS.rdf",
    "OFB" : r"D:\Dokumentasi\LLMs4OM\datasets\local-ont\Local OFB.rdf",
}
# TSV alignment files (YES rows only will be used)
ALIGN_PATHS = [
    r"D:\Dokumentasi\LLMs4OM\experiments\results\matchOSN-MP\rag\gpt-4.1-2025-04-14_CD_thresh0.7_cardmany-to-one\llm_alignment_final_many-to-one_label_only.tsv",
    r"D:\Dokumentasi\LLMs4OM\experiments\results\matchOSN-MCSS\rag\gpt-4.1-2025-04-14_CCD_thresh0.7_cardmany-to-one\llm_alignment_final_many-to-one_label_only.tsv",
    r"D:\Dokumentasi\LLMs4OM\experiments\results\matchOSN-OFB\rag\gpt-4.1-2025-04-14_CCD_thresh0.7_cardmany-to-one\llm_alignment_final_many-to-one_label_only.tsv",
    r"D:\Dokumentasi\LLMs4OM\experiments\results\matchMP-MCSS\rag\gpt-4.1-2025-04-14_CCD_thresh0.7_cardmany-to-one\llm_alignment_final_many-to-one_label_only.tsv",
    r"D:\Dokumentasi\LLMs4OM\experiments\results\matchMP-OFB\rag\gpt-4.1-2025-04-14_CCD_thresh0.7_cardmany-to-one\llm_alignment_final_many-to-one_label_only.tsv",
    r"D:\Dokumentasi\LLMs4OM\experiments\results\matchMCSS-OFB\rag\gpt-4.1-2025-04-14_CCD_thresh0.6_cardmany-to-one\llm_alignment_final_many-to-one_label_only.tsv",
]
THRESH     = 0.6   # score threshold for YES rows
OUT_PATH   = Path(r"D:\Dokumentasi\LLMs4OM\experiments\results\merged-ontology\DEBUG_merged3.owl")
MERGED_IRI = "http://example.org/debug_merge.owl#"
STEP       = 200
TYPE_PRIO  = [ObjectPropertyClass, DataPropertyClass, AnnotationPropertyClass, ThingClass]

# ─────────────────── helper : load with BOM sniff ─────────────
BOMS = [codecs.BOM_UTF8, codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE,
        codecs.BOM_UTF32_LE, codecs.BOM_UTF32_BE]

def load_ontology(world: World, path: str):
    """Robust loader — detect BOM & syntax (RDF/XML, Turtle, N‑Triples)."""
    raw = Path(path).read_bytes()
    for b in BOMS:
        if raw.startswith(b):
            raw = raw[len(b):]
            break
    fmt = (
        "rdfxml" if raw.lstrip()[:1] == b"<" else
        "turtle"  if re.search(rb"@prefix|PREFIX", raw[:200], re.I) else
        "ntriples"
    )
    return world.get_ontology(path).load(fileobj=BytesIO(raw), format=fmt)

# ───────────────────────── LOAD ───────────────────────────────
print("Loading source ontologies …")
world = World()
ont2tag: dict[Ontology, str] = {}
rep2members: dict[str, list[EntityClass]] = defaultdict(list)

for tag, path in ONTOLOGY_PATHS.items():
    ont = load_ontology(world, path)
    ont2tag[ont] = tag
    for ent in list(ont.classes()) + list(ont.properties()):
        if isinstance(ent.iri, str) and ent.iri.startswith("http"):
            rep2members[ent.iri].append(ent)
print(f"▶  {sum(len(v) for v in rep2members.values()):,} entities loaded from {len(ONTOLOGY_PATHS)} ontologies\n")

# ───── merged ontology & provenance annotation properties ─────
merged = world.get_ontology(MERGED_IRI)
with merged:
    class sourceOrigin(AnnotationProperty): pass
    class OSNcomment (AnnotationProperty): pass
    class MPcomment  (AnnotationProperty): pass
    class MCSScomment(AnnotationProperty): pass
    class OFBcomment (AnnotationProperty): pass
    # alignment annotation props
    class alignWithOSN (AnnotationProperty): pass
    class alignWithMP  (AnnotationProperty): pass
    class alignWithMCSS(AnnotationProperty): pass
    class alignWithOFB (AnnotationProperty): pass
comment_prop = {"OSN":OSNcomment, "MP":MPcomment,
                "MCSS":MCSScomment, "OFB":OFBcomment}
# ───── tambahkan tepat SETELAH blok comment_prop ──────────────
align_tag_map = {          #   tag  →  AnnotationProperty class
    "OSN": "alignWithOSN",
    "MP" : "alignWithMP",
    "MCSS": "alignWithMCSS",
    "OFB": "alignWithOFB",
}

# buat AnnotationProperty‑nya
with merged:
    align_prop = { t : types.new_class(an, (AnnotationProperty,), {})
                   for t, an in align_tag_map.items() }

# ---------- util: base‐IRI → tag  --------------------------------
# kita pakai world.ontologies untuk tahu base IRI masing‑masing file
iri2tag = {}
for ont, tag in ont2tag.items():
    base = ont.base_iri               # ex: http://saralutami.org/OnlineSocialNetworkSites#
    iri2tag[base] = tag

def iri_tag(iri:str)->str|None:
    """kembalikan 'OSN' / 'MP' / … sesuai base IRI."""
    for base, tag in iri2tag.items():
        if iri.startswith(base):
            return tag
    return None


name2merged: dict[str, EntityClass] = {}

# ───────────────── PASS‑1 : skeletons ─────────────────────────
print("Pass‑1 ▶ creating skeletons …")
with merged:
    for idx, (iri, members) in enumerate(rep2members.items(), 1):
        rep = next((m for t in TYPE_PRIO for m in members if isinstance(m, t)), members[0])
        if rep.name in name2merged:
            continue
        if isinstance(rep, ObjectPropertyClass):
            skel = types.new_class(rep.name, (ObjectProperty,), {})
        elif isinstance(rep, DataPropertyClass):
            skel = types.new_class(rep.name, (DatatypeProperty,), {})
        elif isinstance(rep, AnnotationPropertyClass):
            skel = types.new_class(rep.name, (AnnotationProperty,), {})
        else:
            skel = types.new_class(rep.name, (Thing,), {})
        name2merged[rep.name] = skel
        if idx % STEP == 0:
            print(f"  • [pass‑1] {idx}/{len(rep2members)} skeletons")
print("✔  Pass‑1 done.\n")

# ───────────────── PASS‑2 : subClassOf ────────────────────────
print("Pass‑2 ▶ linking superclass relations …")
for idx, (iri, members) in enumerate(rep2members.items(), 1):
    tgt = name2merged[members[0].name]
    if isinstance(tgt, ThingClass):
        supers: dict[str, set[str]] = defaultdict(set)
        for m in members:
            if not isinstance(m, ThingClass):
                continue
            tag = ont2tag[m.namespace.ontology]
            for sup in (s for s in m.is_a if isinstance(s, ThingClass) and s.name not in {"Thing", tgt.name}):
                supers[sup.name].add(tag)
        for sup_name, tags in supers.items():
            sup_tgt = name2merged.setdefault(sup_name, types.new_class(sup_name, (Thing,), {}))
            if sup_tgt not in tgt.is_a:
                tgt.is_a.append(sup_tgt)
            for t in tags:
                tgt.sourceOrigin.append(f"subClassOf:{sup_name}_from:{t}")
    if idx % STEP == 0:
        print(f"  • [pass‑2] {idx}/{len(rep2members)} processed")
print("✔  Pass‑2 done.\n")

# ───────────────── PASS‑3 : domain / range ────────────────────
print("Pass‑3 ▶ adding domain & range …")
for idx, (iri, members) in enumerate(rep2members.items(), 1):
    tgt = name2merged[members[0].name]
    if isinstance(tgt, PropertyClass):
        doms, rngs = set(), set()
        for m in members:
            if isinstance(m, PropertyClass):
                doms.update(getattr(m, 'domain', []))
                rngs.update(getattr(m, 'range',  []))
        for d in doms:
            if isinstance(d, ThingClass):
                d_tgt = name2merged.setdefault(d.name, types.new_class(d.name, (Thing,), {}))
                if d_tgt not in tgt.domain:
                    tgt.domain.append(d_tgt)
            elif d and d not in tgt.domain:
                tgt.domain.append(d)
        for r in rngs:
            if isinstance(r, ThingClass):
                r_tgt = name2merged.setdefault(r.name, types.new_class(r.name, (Thing,), {}))
                if r_tgt not in tgt.range:
                    tgt.range.append(r_tgt)
            elif r and r not in tgt.range:
                tgt.range.append(r)
    if idx % STEP == 0:
        print(f"  • [pass‑3] {idx}/{len(rep2members)}")
print("✔  Pass‑3 done.\n")

# ───────────────── PASS‑4 : comments ─────────────────────────
print("Pass‑4 ▶ adding comments …")
for idx, (iri, members) in enumerate(rep2members.items(), 1):
    tgt = name2merged[members[0].name]
    for m in members:
        tag = ont2tag.get(m.namespace.ontology)
        if not tag:
            continue
        prop = comment_prop[tag]
        for txt in getattr(m, 'comment', []):
            if txt not in getattr(tgt, prop.name):
                getattr(tgt, prop.name).append(txt)
    if idx % STEP == 0:
        print(f"  • [pass‑4] {idx}/{len(rep2members)}")
print("✔  Pass‑4 done.\n")

# ──────────────── PASS‑5 : alignment annotations ───────────────
print("Pass‑5 ▶ applying alignment annotations (deduplicated) …")

aligned_map = defaultdict(set)
for tsv in ALIGN_PATHS:
    df = pd.read_csv(tsv, sep='\t', keep_default_na=False)
    for _, r in df.iterrows():
        if str(r.get('Label', '')).lower() != 'yes':
            continue
        if float(r.get('Score', 1.0)) < THRESH:
            continue
        src = r['Source'].strip(); tgt_iri = r['Target'].strip()
        aligned_map[src].add(tgt_iri)
        aligned_map[tgt_iri].add(src)

def get_tag_from_iri(iri: str) -> str | None:
    for ont, tag in ont2tag.items():
        if iri.startswith(ont.base_iri):
            return tag
    return None

for idx, (root, members) in enumerate(aligned_map.items(), 1):
    anchor_name = root.split('#')[-1]
    anchor_ent = name2merged.get(anchor_name)
    if not anchor_ent:
        continue

    seen_tags = set()
    for iri in members | {root}:
        tag = get_tag_from_iri(iri)
        if not tag or tag in seen_tags:
            continue
        prop = align_prop.get(tag)
        if prop and iri not in getattr(anchor_ent, prop.name):
            getattr(anchor_ent, prop.name).append(iri)
            seen_tags.add(tag)

    if idx % STEP == 0:
        print(f"  • [pass‑5] {idx}/{len(aligned_map)} groups processed")
print("✔  Pass‑5 done (deduplicated).\n")


# ───────────────────────── SAVE ──────────────────────────────
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
merged.save(file=str(OUT_PATH), format="rdfxml")
print("Merged ontology saved →", OUT_PATH)
