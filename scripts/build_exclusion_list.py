#!/usr/bin/env python3
"""
Build exclusion, accepted, and portal-only article lists by cross-referencing
WoS + Scopus search results against the 766 baseline articles and the
Nechako Portal XML.

Outputs:
  results/exclusion_list.json      - search results NOT in the baseline
  results/accepted_from_search.json - search results IN the baseline
  results/portal_only_articles.json - baseline articles found in Portal XML
                                      but NOT in WoS/Scopus search results
"""

import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict

from fuzzywuzzy import fuzz

# ── paths ────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

WOS_PATH = os.path.join(
    BASE_DIR, "results", "raw", "wos_no_variants_20260309_220253.json"
)
SCOPUS_PATH = os.path.join(
    BASE_DIR, "results", "raw", "scopus_full_20260309_215712.json"
)
BASELINE_PATH = os.path.join(BASE_DIR, "data", "baseline_766_articles.json")
PORTAL_XML_PATH = os.path.expanduser(
    "~/Desktop/Nechako Portal.xml"
)
SATURATION_XML_PATH = os.path.expanduser(
    "~/Desktop/Nechako Saturation Search (2024-04).xml"
)

OUT_DIR = os.path.join(BASE_DIR, "results")

FUZZY_THRESHOLD = 85  # title similarity threshold (%)


# ── helpers ──────────────────────────────────────────────────────────────
def normalize_title(title: str) -> str:
    """Lower-case, strip punctuation/whitespace for comparison."""
    if not title:
        return ""
    title = title.lower().strip()
    title = re.sub(r"[^a-z0-9\s]", "", title)
    title = re.sub(r"\s+", " ", title)
    return title


def normalize_doi(doi: str) -> str:
    """Lower-case, strip URL prefix."""
    if not doi:
        return ""
    doi = doi.strip().lower()
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi)
    return doi


def get_field(record: dict, *candidates, default=""):
    """Return the first non-empty value for any of the candidate keys."""
    for key in candidates:
        val = record.get(key)
        if val is not None and val != "" and val != []:
            return val
    return default


# ── XML parsing ──────────────────────────────────────────────────────────
def parse_zotero_xml(path: str) -> list[dict]:
    """Parse a Zotero-exported Endnote XML file into a list of dicts."""
    tree = ET.parse(path)
    root = tree.getroot()
    records_el = root.find("records")
    if records_el is None:
        print(f"  WARNING: no <records> element in {path}")
        return []

    parsed = []
    for rec in records_el.findall("record"):
        # Title
        title_el = rec.find("titles/title")
        title = title_el.text.strip() if title_el is not None and title_el.text else ""

        # Authors
        authors = []
        authors_el = rec.find("contributors/authors")
        if authors_el is not None:
            for a in authors_el.findall("author"):
                if a.text:
                    authors.append(a.text.strip())

        # Year
        year_el = rec.find("dates/year")
        year = year_el.text.strip() if year_el is not None and year_el.text else ""

        # DOI
        doi_el = rec.find("electronic-resource-num")
        doi = doi_el.text.strip() if doi_el is not None and doi_el.text else ""

        # Ref-type
        ref_type_el = rec.find("ref-type")
        ref_type = ref_type_el.attrib.get("name", "") if ref_type_el is not None else ""

        # Keywords
        keywords = []
        kw_el = rec.find("keywords")
        if kw_el is not None:
            for kw in kw_el.findall("keyword"):
                if kw.text:
                    keywords.append(kw.text.strip())

        # Journal / periodical
        journal_el = rec.find("periodical/full-title")
        journal = journal_el.text.strip() if journal_el is not None and journal_el.text else ""

        parsed.append(
            {
                "title": title,
                "authors": authors,
                "year": year,
                "doi": doi,
                "ref_type": ref_type,
                "keywords": keywords,
                "journal": journal,
            }
        )
    return parsed


# ── loading ──────────────────────────────────────────────────────────────
def load_json(path: str) -> dict | list:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


# ── deduplication & matching ─────────────────────────────────────────────
def deduplicate_search_results(wos_records: list, scopus_records: list) -> list[dict]:
    """
    Merge WoS + Scopus, deduplicate by DOI first then fuzzy title.
    Each result carries a 'source' field: 'wos', 'scopus', or 'both'.
    """
    # Normalise every record into a common shape
    merged = []
    for r in wos_records:
        merged.append(
            {
                "title": get_field(r, "title", "Title"),
                "authors": get_field(r, "authors", "Authors", default=[]),
                "year": get_field(r, "year", "Year", default=""),
                "doi": get_field(r, "doi", "DOI", default=""),
                "journal": get_field(r, "journal", "Journal", default=""),
                "source": "wos",
                "_norm_title": normalize_title(get_field(r, "title", "Title")),
                "_norm_doi": normalize_doi(get_field(r, "doi", "DOI", default="")),
            }
        )
    for r in scopus_records:
        merged.append(
            {
                "title": get_field(r, "title", "Title"),
                "authors": get_field(r, "authors", "Authors", default=[]),
                "year": get_field(r, "year", "Year", default=""),
                "doi": get_field(r, "doi", "DOI", default=""),
                "journal": get_field(r, "journal", "Journal", default=""),
                "source": "scopus",
                "_norm_title": normalize_title(get_field(r, "title", "Title")),
                "_norm_doi": normalize_doi(get_field(r, "doi", "DOI", default="")),
            }
        )

    # Pass 1: group by DOI
    doi_map: dict[str, list[dict]] = defaultdict(list)
    no_doi: list[dict] = []
    for rec in merged:
        if rec["_norm_doi"]:
            doi_map[rec["_norm_doi"]].append(rec)
        else:
            no_doi.append(rec)

    unique: list[dict] = []
    for doi, group in doi_map.items():
        sources = set(r["source"] for r in group)
        rep = group[0].copy()
        rep["source"] = "both" if len(sources) > 1 else sources.pop()
        unique.append(rep)

    # Pass 2: fuzzy-match the no-doi records against what we already have,
    # and among themselves
    for rec in no_doi:
        matched = False
        for existing in unique:
            if rec["_norm_title"] and existing["_norm_title"]:
                score = fuzz.ratio(rec["_norm_title"], existing["_norm_title"])
                if score >= FUZZY_THRESHOLD:
                    # merge source
                    if rec["source"] != existing["source"] and existing["source"] != "both":
                        existing["source"] = "both"
                    matched = True
                    break
        if not matched:
            unique.append(rec)

    return unique


def match_against_baseline(
    search_results: list[dict],
    baseline: list[dict],
) -> tuple[list[dict], list[dict], set[int]]:
    """
    Returns (accepted, excluded, matched_baseline_indices).
    accepted  = search results that match a baseline article
    excluded  = search results that do NOT match any baseline article
    matched_baseline_indices = indices into `baseline` that were matched
    """
    # Pre-normalise baseline
    bl_norm = []
    for i, b in enumerate(baseline):
        bl_norm.append(
            {
                "idx": i,
                "norm_title": normalize_title(b.get("title", "")),
                "norm_doi": normalize_doi(b.get("doi", "")),
            }
        )

    # Build a DOI lookup for baseline
    bl_doi_map: dict[str, int] = {}
    for bn in bl_norm:
        if bn["norm_doi"]:
            bl_doi_map[bn["norm_doi"]] = bn["idx"]

    accepted = []
    excluded = []
    matched_bl_indices: set[int] = set()

    for rec in search_results:
        found = False

        # Try DOI match first
        if rec["_norm_doi"] and rec["_norm_doi"] in bl_doi_map:
            idx = bl_doi_map[rec["_norm_doi"]]
            matched_bl_indices.add(idx)
            found = True

        # Try fuzzy title match
        if not found and rec["_norm_title"]:
            for bn in bl_norm:
                if bn["norm_title"]:
                    score = fuzz.ratio(rec["_norm_title"], bn["norm_title"])
                    if score >= FUZZY_THRESHOLD:
                        matched_bl_indices.add(bn["idx"])
                        found = True
                        break

        clean = {
            "title": rec["title"],
            "doi": rec["doi"],
            "authors": rec["authors"],
            "year": rec["year"],
            "journal": rec["journal"],
            "source": rec["source"],
        }

        if found:
            accepted.append(clean)
        else:
            excluded.append(clean)

    return accepted, excluded, matched_bl_indices


def find_portal_only(
    baseline: list[dict],
    matched_bl_indices: set[int],
    portal_records: list[dict],
) -> list[dict]:
    """
    Identify baseline articles that were NOT found in WoS/Scopus
    but CAN be found in the Portal XML.
    """
    missed_indices = set(range(len(baseline))) - matched_bl_indices

    # Pre-normalise portal
    portal_norm = []
    for p in portal_records:
        portal_norm.append(
            {
                "norm_title": normalize_title(p.get("title", "")),
                "norm_doi": normalize_doi(p.get("doi", "")),
                "record": p,
            }
        )

    portal_doi_map: dict[str, dict] = {}
    for pn in portal_norm:
        if pn["norm_doi"]:
            portal_doi_map[pn["norm_doi"]] = pn["record"]

    portal_only: list[dict] = []
    for idx in sorted(missed_indices):
        bl = baseline[idx]
        bl_doi = normalize_doi(bl.get("doi", ""))
        bl_title = normalize_title(bl.get("title", ""))
        found_in_portal = False
        portal_rec = None

        # DOI match
        if bl_doi and bl_doi in portal_doi_map:
            found_in_portal = True
            portal_rec = portal_doi_map[bl_doi]

        # Fuzzy title match
        if not found_in_portal and bl_title:
            for pn in portal_norm:
                if pn["norm_title"]:
                    score = fuzz.ratio(bl_title, pn["norm_title"])
                    if score >= FUZZY_THRESHOLD:
                        found_in_portal = True
                        portal_rec = pn["record"]
                        break

        if found_in_portal and portal_rec:
            portal_only.append(
                {
                    "title": portal_rec.get("title", bl.get("title", "")),
                    "doi": portal_rec.get("doi", bl.get("doi", "")),
                    "authors": portal_rec.get("authors", bl.get("authors", [])),
                    "year": portal_rec.get("year", bl.get("year", "")),
                    "journal": portal_rec.get("journal", bl.get("journal", "")),
                    "ref_type": portal_rec.get("ref_type", ""),
                    "keywords": portal_rec.get("keywords", []),
                    "source": "portal",
                }
            )
        else:
            # Baseline article not found in portal either — still include it
            # so the user knows about it
            portal_only.append(
                {
                    "title": bl.get("title", ""),
                    "doi": bl.get("doi", ""),
                    "authors": bl.get("authors", []),
                    "year": bl.get("year", ""),
                    "journal": bl.get("journal", ""),
                    "ref_type": "",
                    "keywords": [],
                    "source": "baseline_only",
                }
            )

    return portal_only


# ── main ─────────────────────────────────────────────────────────────────
def main():
    print("=" * 70)
    print("BUILD EXCLUSION LIST")
    print("=" * 70)

    # 1. Load search results
    print("\n[1] Loading search results ...")
    wos_data = load_json(WOS_PATH)
    wos_records = wos_data["records"]
    print(f"    WoS records loaded: {len(wos_records)}")

    scopus_data = load_json(SCOPUS_PATH)
    scopus_records = scopus_data["records"]
    print(f"    Scopus records loaded: {len(scopus_records)}")

    # 2. Load baseline
    print("\n[2] Loading baseline 766 articles ...")
    baseline = load_json(BASELINE_PATH)
    print(f"    Baseline articles loaded: {len(baseline)}")

    # 3. Load Portal XML
    print("\n[3] Parsing Nechako Portal XML ...")
    portal_records = parse_zotero_xml(PORTAL_XML_PATH)
    print(f"    Portal records parsed: {len(portal_records)}")

    # 4. Load Saturation Search XML
    print("\n[4] Parsing Saturation Search baseline XML ...")
    saturation_records = parse_zotero_xml(SATURATION_XML_PATH)
    print(f"    Saturation Search records parsed: {len(saturation_records)}")

    # 5. Deduplicate WoS + Scopus
    print("\n[5] Deduplicating WoS + Scopus search results ...")
    unique_results = deduplicate_search_results(wos_records, scopus_records)
    print(f"    Combined raw: {len(wos_records) + len(scopus_records)}")
    print(f"    After deduplication: {len(unique_results)}")

    source_counts = defaultdict(int)
    for r in unique_results:
        source_counts[r["source"]] += 1
    for src, cnt in sorted(source_counts.items()):
        print(f"      {src}: {cnt}")

    # 6. Match search results against baseline
    print("\n[6] Matching search results against baseline ...")
    accepted, excluded, matched_bl_indices = match_against_baseline(
        unique_results, baseline
    )
    print(f"    Matched (accepted): {len(accepted)}")
    print(f"    Not matched (excluded): {len(excluded)}")
    print(f"    Baseline articles matched: {len(matched_bl_indices)} / {len(baseline)}")

    # 7. Find portal-only articles
    print("\n[7] Finding baseline articles not in search results (portal-only) ...")
    portal_only = find_portal_only(baseline, matched_bl_indices, portal_records)
    portal_found_in_xml = sum(1 for p in portal_only if p["source"] == "portal")
    baseline_only_count = sum(1 for p in portal_only if p["source"] == "baseline_only")
    print(f"    Baseline articles NOT in WoS/Scopus: {len(portal_only)}")
    print(f"      Found in Portal XML: {portal_found_in_xml}")
    print(f"      Not found in Portal XML either: {baseline_only_count}")

    # 8. Save outputs
    print("\n[8] Saving output files ...")
    os.makedirs(OUT_DIR, exist_ok=True)

    excl_path = os.path.join(OUT_DIR, "exclusion_list.json")
    with open(excl_path, "w", encoding="utf-8") as f:
        json.dump(excluded, f, indent=2, ensure_ascii=False, default=str)
    print(f"    {excl_path}  ({len(excluded)} records)")

    acc_path = os.path.join(OUT_DIR, "accepted_from_search.json")
    with open(acc_path, "w", encoding="utf-8") as f:
        json.dump(accepted, f, indent=2, ensure_ascii=False, default=str)
    print(f"    {acc_path}  ({len(accepted)} records)")

    po_path = os.path.join(OUT_DIR, "portal_only_articles.json")
    with open(po_path, "w", encoding="utf-8") as f:
        json.dump(portal_only, f, indent=2, ensure_ascii=False, default=str)
    print(f"    {po_path}  ({len(portal_only)} records)")

    # 9. Print summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Total unique search results (WoS + Scopus deduplicated): {len(unique_results)}")
    print(f"  Matched baseline (accepted from search):                 {len(accepted)}")
    print(f"  Exclusions (search results NOT in baseline):             {len(excluded)}")
    print(f"  Baseline articles from Portal only:                      {len(portal_only)}")
    print(f"    - Found in Portal XML:                                 {portal_found_in_xml}")
    print(f"    - Not in Portal XML (baseline-only):                   {baseline_only_count}")
    print()

    # Exclusion breakdown by source
    excl_by_source = defaultdict(int)
    for e in excluded:
        excl_by_source[e["source"]] += 1
    print("  Exclusions by source:")
    for src, cnt in sorted(excl_by_source.items()):
        print(f"    {src}: {cnt}")

    # Sanity checks
    print()
    print(f"  Sanity check: accepted + portal_only = {len(accepted) + len(portal_only)} "
          f"(should approximate {len(baseline)} baseline)")
    print(f"  Sanity check: accepted + excluded = {len(accepted) + len(excluded)} "
          f"(should equal {len(unique_results)} unique search results)")
    print("=" * 70)


if __name__ == "__main__":
    main()
