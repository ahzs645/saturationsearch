#!/usr/bin/env python3
"""
Analyze 267 missed baseline articles to determine their origins.
Cross-references against:
  1. CSV from prior saturation search (~526 articles)
  2. Zotero XML export (Nechako Portal, ~2284 articles)

Uses fuzzy title matching (fuzzywuzzy, threshold >= 85%) and DOI matching.
"""

import json
import csv
import re
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from fuzzywuzzy import fuzz

# ── Paths ──────────────────────────────────────────────────────────────────
MISSED_PATH = "/Users/ahmadjalil/github/saturationsearch/results/missed_baseline_articles.json"
CSV_PATH = "/Users/ahmadjalil/Downloads/0-637_saturation_search.csv"
XML_PATH = "/Users/ahmadjalil/Desktop/Nechako Portal.xml"
OUTPUT_PATH = "/Users/ahmadjalil/github/saturationsearch/results/missed_articles_analysis.json"

FUZZY_THRESHOLD = 85


def normalize_title(title):
    """Lowercase, strip punctuation/whitespace for comparison."""
    if not title:
        return ""
    title = title.lower().strip()
    title = re.sub(r'[^\w\s]', '', title)
    title = re.sub(r'\s+', ' ', title)
    return title


def normalize_doi(doi):
    """Extract and normalise a DOI string."""
    if not doi or str(doi).strip() in ("", "nan", "NaN", "None"):
        return ""
    doi = str(doi).strip().lower()
    # Strip URL prefix if present
    doi = re.sub(r'^https?://(dx\.)?doi\.org/', '', doi)
    return doi


# ── Load missed articles ──────────────────────────────────────────────────
with open(MISSED_PATH, "r", encoding="utf-8") as f:
    missed_articles = json.load(f)
print(f"Loaded {len(missed_articles)} missed baseline articles")

# ── Load CSV ──────────────────────────────────────────────────────────────
csv_articles = []
with open(CSV_PATH, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        csv_articles.append(row)
print(f"Loaded {len(csv_articles)} articles from CSV")

# ── Load XML ──────────────────────────────────────────────────────────────
tree = ET.parse(XML_PATH)
root = tree.getroot()
xml_records = root.findall(".//record")
xml_articles = []
for rec in xml_records:
    title_el = rec.find(".//titles/title")
    doi_el = rec.find(".//electronic-resource-num")
    ref_type_el = rec.find("ref-type")
    year_el = rec.find(".//dates/year")
    authors = [a.text for a in rec.findall(".//contributors/authors/author") if a.text]
    keywords = [k.text for k in rec.findall(".//keywords/keyword") if k.text]
    xml_articles.append({
        "title": title_el.text if title_el is not None and title_el.text else "",
        "doi": doi_el.text if doi_el is not None and doi_el.text else "",
        "ref_type": ref_type_el.get("name") if ref_type_el is not None else "",
        "year": year_el.text if year_el is not None and year_el.text else "",
        "authors": authors,
        "keywords": keywords,
    })
print(f"Loaded {len(xml_articles)} articles from XML")

# ── Build lookup indexes ──────────────────────────────────────────────────
# CSV indexes
csv_doi_index = {}
csv_title_norm = []
for i, art in enumerate(csv_articles):
    doi = normalize_doi(art.get("DOI", ""))
    if doi:
        csv_doi_index[doi] = i
    csv_title_norm.append(normalize_title(art.get("Title", "")))

# XML indexes
xml_doi_index = {}
xml_title_norm = []
for i, art in enumerate(xml_articles):
    doi = normalize_doi(art["doi"])
    if doi:
        xml_doi_index[doi] = i
    xml_title_norm.append(normalize_title(art["title"]))

# ── Cross-reference ───────────────────────────────────────────────────────
found_in_csv = []
found_in_xml = []
found_in_both = []
found_in_neither = []

csv_match_details = []   # (missed_idx, csv_idx, match_type)
xml_match_details = []   # (missed_idx, xml_idx, match_type)

for mi, missed in enumerate(missed_articles):
    m_doi = normalize_doi(missed.get("doi", ""))
    m_title_norm = normalize_title(missed.get("title", ""))

    in_csv = False
    csv_idx = None
    csv_match_type = None

    in_xml = False
    xml_idx = None
    xml_match_type = None

    # ── CSV matching ──
    # DOI match
    if m_doi and m_doi in csv_doi_index:
        in_csv = True
        csv_idx = csv_doi_index[m_doi]
        csv_match_type = "doi"
    else:
        # Fuzzy title match
        best_score = 0
        best_idx = -1
        for ci, ct in enumerate(csv_title_norm):
            if not ct:
                continue
            score = fuzz.ratio(m_title_norm, ct)
            if score > best_score:
                best_score = score
                best_idx = ci
        if best_score >= FUZZY_THRESHOLD:
            in_csv = True
            csv_idx = best_idx
            csv_match_type = f"fuzzy_title ({best_score}%)"

    # ── XML matching ──
    if m_doi and m_doi in xml_doi_index:
        in_xml = True
        xml_idx = xml_doi_index[m_doi]
        xml_match_type = "doi"
    else:
        best_score = 0
        best_idx = -1
        for xi, xt in enumerate(xml_title_norm):
            if not xt:
                continue
            score = fuzz.ratio(m_title_norm, xt)
            if score > best_score:
                best_score = score
                best_idx = xi
        if best_score >= FUZZY_THRESHOLD:
            in_xml = True
            xml_idx = best_idx
            xml_match_type = f"fuzzy_title ({best_score}%)"

    # Categorize
    if in_csv:
        found_in_csv.append(mi)
        csv_match_details.append((mi, csv_idx, csv_match_type))
    if in_xml:
        found_in_xml.append(mi)
        xml_match_details.append((mi, xml_idx, xml_match_type))
    if in_csv and in_xml:
        found_in_both.append(mi)
    if not in_csv and not in_xml:
        found_in_neither.append(mi)

    if (mi + 1) % 25 == 0:
        print(f"  Processed {mi+1}/{len(missed_articles)} ...")

print(f"\nMatching complete.")

# ── Collect item types for CSV matches ────────────────────────────────────
csv_item_types = Counter()
csv_search_terms = Counter()
csv_manual_tags = Counter()
for mi, ci, mt in csv_match_details:
    item_type = csv_articles[ci].get("ItemType", "unknown")
    csv_item_types[item_type] += 1
    st = csv_articles[ci].get("SearchTerms", "").strip()
    if st:
        csv_search_terms[st] += 1
    tags = csv_articles[ci].get("ManualTags", "").strip()
    if tags:
        # Split by semicolons
        for tag in tags.split(";"):
            tag = tag.strip()
            if tag:
                csv_manual_tags[tag] += 1

# ── Collect ref types for XML matches ─────────────────────────────────────
xml_ref_types = Counter()
for mi, xi, mt in xml_match_details:
    ref_type = xml_articles[xi].get("ref_type", "unknown")
    xml_ref_types[ref_type] += 1

# ── Categorize ALL missed articles by journal field (rough heuristic) ─────
# Use the journal field from missed_baseline_articles.json
journal_categories = Counter()
for art in missed_articles:
    journal = (art.get("journal") or "").strip()
    title = (art.get("title") or "").lower()
    if not journal:
        journal_categories["No journal listed"] += 1
    else:
        journal_categories[journal] += 1

# Broader categorization by item type from CSV + XML
broad_categories = Counter()
# For articles found in CSV, use ItemType
csv_matched_indices = set()
for mi, ci, mt in csv_match_details:
    item_type = csv_articles[ci].get("ItemType", "unknown").strip()
    broad_categories[item_type] += 1
    csv_matched_indices.add(mi)

# For articles found only in XML (not in CSV), use ref_type
xml_only_matched = set()
for mi, xi, mt in xml_match_details:
    if mi not in csv_matched_indices:
        ref_type = xml_articles[xi].get("ref_type", "unknown")
        broad_categories[ref_type] += 1
        xml_only_matched.add(mi)

# For articles in neither, try to infer from journal name
for mi in found_in_neither:
    art = missed_articles[mi]
    journal = (art.get("journal") or "").strip().lower()
    title = (art.get("title") or "").lower()
    if any(kw in journal for kw in ["report", "technical", "bulletin"]):
        broad_categories["report (inferred)"] += 1
    elif any(kw in journal for kw in ["book", "press"]):
        broad_categories["book (inferred)"] += 1
    elif any(kw in journal for kw in ["thesis", "dissertation"]):
        broad_categories["thesis (inferred)"] += 1
    elif any(kw in journal for kw in ["proceeding", "conference", "symposium"]):
        broad_categories["conferencePaper (inferred)"] += 1
    elif any(kw in journal for kw in ["newspaper", "times", "herald", "gazette", "citizen"]):
        broad_categories["newspaperArticle (inferred)"] += 1
    elif journal:
        broad_categories["journalArticle (inferred)"] += 1
    else:
        broad_categories["unknown / grey literature"] += 1

# ── Build detailed lists ──────────────────────────────────────────────────
csv_matched_articles_detail = []
for mi, ci, mt in csv_match_details:
    art = missed_articles[mi]
    csv_art = csv_articles[ci]
    csv_matched_articles_detail.append({
        "missed_title": art.get("title", ""),
        "missed_doi": art.get("doi", ""),
        "missed_year": art.get("year", ""),
        "csv_title": csv_art.get("Title", ""),
        "csv_doi": csv_art.get("DOI", ""),
        "csv_item_type": csv_art.get("ItemType", ""),
        "csv_search_terms": csv_art.get("SearchTerms", ""),
        "csv_manual_tags": csv_art.get("ManualTags", ""),
        "match_type": mt,
    })

xml_matched_articles_detail = []
for mi, xi, mt in xml_match_details:
    art = missed_articles[mi]
    xml_art = xml_articles[xi]
    xml_matched_articles_detail.append({
        "missed_title": art.get("title", ""),
        "missed_doi": art.get("doi", ""),
        "missed_year": art.get("year", ""),
        "xml_title": xml_art.get("title", ""),
        "xml_doi": xml_art.get("doi", ""),
        "xml_ref_type": xml_art.get("ref_type", ""),
        "xml_keywords": xml_art.get("keywords", []),
        "match_type": mt,
    })

neither_articles_detail = []
for mi in found_in_neither:
    art = missed_articles[mi]
    neither_articles_detail.append({
        "title": art.get("title", ""),
        "doi": art.get("doi", ""),
        "year": art.get("year", ""),
        "journal": art.get("journal", ""),
        "authors": art.get("authors", []),
    })

# ── Assemble results ─────────────────────────────────────────────────────
results = {
    "summary": {
        "total_missed_articles": len(missed_articles),
        "found_in_csv": len(found_in_csv),
        "found_in_xml": len(found_in_xml),
        "found_in_both": len(found_in_both),
        "found_in_csv_only": len(found_in_csv) - len(found_in_both),
        "found_in_xml_only": len(found_in_xml) - len(found_in_both),
        "found_in_neither": len(found_in_neither),
        "fuzzy_threshold": FUZZY_THRESHOLD,
    },
    "csv_item_type_distribution": dict(csv_item_types.most_common()),
    "csv_search_terms_distribution": dict(csv_search_terms.most_common()),
    "csv_manual_tags_distribution": dict(csv_manual_tags.most_common(30)),
    "xml_ref_type_distribution": dict(xml_ref_types.most_common()),
    "broad_category_distribution": dict(broad_categories.most_common()),
    "csv_matched_articles": csv_matched_articles_detail,
    "xml_matched_articles": xml_matched_articles_detail,
    "neither_articles": neither_articles_detail,
}

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f"\nResults saved to {OUTPUT_PATH}")
print(f"\n{'='*60}")
print(f"SUMMARY")
print(f"{'='*60}")
print(f"Total missed baseline articles:   {len(missed_articles)}")
print(f"Found in CSV (saturation search): {len(found_in_csv)}")
print(f"Found in XML (Nechako Portal):    {len(found_in_xml)}")
print(f"Found in BOTH:                    {len(found_in_both)}")
print(f"Found in CSV only:                {len(found_in_csv) - len(found_in_both)}")
print(f"Found in XML only:                {len(found_in_xml) - len(found_in_both)}")
print(f"Found in NEITHER:                 {len(found_in_neither)}")
print(f"\nCSV Item Type distribution (for matched articles):")
for k, v in csv_item_types.most_common():
    print(f"  {k}: {v}")
print(f"\nXML Ref Type distribution (for matched articles):")
for k, v in xml_ref_types.most_common():
    print(f"  {k}: {v}")
print(f"\nBroad category distribution (all 267 missed articles):")
for k, v in broad_categories.most_common():
    print(f"  {k}: {v}")
print(f"\nCSV SearchTerms distribution:")
for k, v in csv_search_terms.most_common():
    print(f"  {k}: {v}")
print(f"\nCSV ManualTags distribution (top 20):")
for k, v in csv_manual_tags.most_common(20):
    print(f"  {k}: {v}")
