#!/usr/bin/env python3
"""
Identify NEW articles from WoS + Scopus search results that need manual review.
Filters to 2023+ publications not in baseline, exclusion list, or accepted list.
"""

import json
import csv
import os
import sys
from collections import defaultdict
from fuzzywuzzy import fuzz

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# File paths
WOS_FILE = os.path.join(BASE_DIR, "results/raw/wos_no_variants_20260309_220253.json")
SCOPUS_FILE = os.path.join(BASE_DIR, "results/raw/scopus_full_20260309_215712.json")
BASELINE_FILE = os.path.join(BASE_DIR, "data/baseline_766_articles.json")
EXCLUSION_FILE = os.path.join(BASE_DIR, "results/exclusion_list.json")
ACCEPTED_FILE = os.path.join(BASE_DIR, "results/accepted_from_search.json")
OUTPUT_JSON = os.path.join(BASE_DIR, "results/new_articles_to_review.json")
OUTPUT_CSV = os.path.join(BASE_DIR, "results/new_articles_to_review.csv")


def normalize_doi(doi):
    """Normalize DOI for comparison."""
    if not doi:
        return ""
    return doi.strip().lower()


def normalize_title(title):
    """Normalize title for comparison."""
    if not title:
        return ""
    return title.strip().lower()


def safe_year(val):
    """Convert year value to int, return None if not possible."""
    if val is None:
        return None
    try:
        y = int(val)
        if 1900 <= y <= 2030:
            return y
        return None
    except (ValueError, TypeError):
        return None


def load_json(filepath):
    """Load a JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)


def build_doi_set(records):
    """Build a set of normalized DOIs from records."""
    dois = set()
    for r in records:
        d = normalize_doi(r.get('doi', ''))
        if d:
            dois.add(d)
    return dois


def build_title_set(records):
    """Build a set of normalized titles from records."""
    titles = set()
    for r in records:
        t = normalize_title(r.get('title', ''))
        if t:
            titles.add(t)
    return titles


def build_title_list(records):
    """Build a list of normalized titles from records (for fuzzy matching)."""
    titles = []
    for r in records:
        t = normalize_title(r.get('title', ''))
        if t:
            titles.append(t)
    return titles


def is_fuzzy_match(title, title_list, threshold=85):
    """Check if title fuzzy-matches any title in the list."""
    norm = normalize_title(title)
    if not norm:
        return False
    for t in title_list:
        if fuzz.ratio(norm, t) >= threshold:
            return True
    return False


def main():
    print("=" * 70)
    print("FINDING NEW ARTICLES FOR MANUAL REVIEW")
    print("=" * 70)

    # ------------------------------------------------------------------
    # 1. Load all data
    # ------------------------------------------------------------------
    print("\n[1] Loading data files...")

    wos_data = load_json(WOS_FILE)
    wos_records = wos_data["records"]
    print(f"    WoS records: {len(wos_records)}")

    scopus_data = load_json(SCOPUS_FILE)
    scopus_records = scopus_data["records"]
    print(f"    Scopus records: {len(scopus_records)}")

    baseline = load_json(BASELINE_FILE)
    print(f"    Baseline articles: {len(baseline)}")

    exclusion = load_json(EXCLUSION_FILE)
    print(f"    Exclusion list: {len(exclusion)}")

    accepted = load_json(ACCEPTED_FILE)
    print(f"    Accepted from search: {len(accepted)}")

    # ------------------------------------------------------------------
    # 2. Build Scopus DOI -> year lookup for WoS year recovery
    # ------------------------------------------------------------------
    print("\n[2] Building DOI-to-year lookup from Scopus...")
    scopus_doi_year = {}
    for r in scopus_records:
        d = normalize_doi(r.get('doi', ''))
        y = safe_year(r.get('year'))
        if d and y:
            scopus_doi_year[d] = y

    # Try to recover WoS years from Scopus
    wos_year_recovered = 0
    for r in wos_records:
        d = normalize_doi(r.get('doi', ''))
        if d and d in scopus_doi_year:
            r['year'] = scopus_doi_year[d]
            wos_year_recovered += 1
    print(f"    WoS records with year recovered from Scopus: {wos_year_recovered}")

    wos_no_year = sum(1 for r in wos_records if safe_year(r.get('year')) is None)
    print(f"    WoS records still without year: {wos_no_year}")

    # ------------------------------------------------------------------
    # 3. Filter to 2023+ articles
    # ------------------------------------------------------------------
    print("\n[3] Filtering to articles published 2023, 2024, or 2025...")

    target_years = {2023, 2024, 2025}

    # Scopus 2023+ articles
    scopus_2023 = [r for r in scopus_records if safe_year(r.get('year')) in target_years]
    print(f"    Scopus 2023+ articles: {len(scopus_2023)}")

    # WoS 2023+ articles (only those with recovered years)
    wos_2023 = [r for r in wos_records if safe_year(r.get('year')) in target_years]
    print(f"    WoS 2023+ articles (with year): {len(wos_2023)}")

    # Combine all 2023+ candidates, tracking source
    # Use DOI as primary key for dedup between WoS and Scopus
    combined = {}  # key: normalized_doi or title -> record dict

    for r in scopus_2023:
        doi = normalize_doi(r.get('doi', ''))
        title = r.get('title', '').strip()
        year = safe_year(r.get('year'))
        authors = r.get('authors', [])
        if isinstance(authors, list):
            authors_str = "; ".join(authors)
        else:
            authors_str = str(authors)
        journal = r.get('journal', '')

        key = doi if doi else normalize_title(title)
        if not key:
            continue

        if key in combined:
            combined[key]['found_in'] = 'both'
        else:
            combined[key] = {
                'title': title,
                'authors': authors_str,
                'year': year,
                'doi': r.get('doi', ''),
                'journal': journal,
                'found_in': 'scopus',
                '_norm_title': normalize_title(title),
            }

    for r in wos_2023:
        doi = normalize_doi(r.get('doi', ''))
        title = r.get('title', '').strip()
        year = safe_year(r.get('year'))
        authors = r.get('authors', [])
        if isinstance(authors, list):
            authors_str = "; ".join(authors)
        else:
            authors_str = str(authors)
        journal = r.get('journal', '')

        key = doi if doi else normalize_title(title)
        if not key:
            continue

        if key in combined:
            combined[key]['found_in'] = 'both'
        else:
            combined[key] = {
                'title': title,
                'authors': authors_str,
                'year': year,
                'doi': r.get('doi', ''),
                'journal': journal,
                'found_in': 'wos',
                '_norm_title': normalize_title(title),
            }

    total_2023_plus = len(combined)
    print(f"    Combined unique 2023+ articles: {total_2023_plus}")

    # Year breakdown before filtering
    year_counts_pre = defaultdict(int)
    for rec in combined.values():
        year_counts_pre[rec['year']] += 1
    for y in sorted(target_years):
        print(f"      {y}: {year_counts_pre.get(y, 0)}")

    # ------------------------------------------------------------------
    # 4. Build reference DOI sets and title lists
    # ------------------------------------------------------------------
    print("\n[4] Building reference sets for baseline, exclusion, accepted...")

    # DOI sets
    baseline_dois = build_doi_set(baseline)
    exclusion_dois = build_doi_set(exclusion)
    accepted_dois = build_doi_set(accepted)
    print(f"    Baseline DOIs: {len(baseline_dois)}")
    print(f"    Exclusion DOIs: {len(exclusion_dois)}")
    print(f"    Accepted DOIs: {len(accepted_dois)}")

    # Title sets (exact lowercase match)
    baseline_titles = build_title_set(baseline)
    exclusion_titles = build_title_set(exclusion)
    accepted_titles = build_title_set(accepted)
    print(f"    Baseline titles: {len(baseline_titles)}")
    print(f"    Exclusion titles: {len(exclusion_titles)}")
    print(f"    Accepted titles: {len(accepted_titles)}")

    # Title lists (for fuzzy matching, only after exact fails)
    baseline_title_list = build_title_list(baseline)
    exclusion_title_list = build_title_list(exclusion)
    accepted_title_list = build_title_list(accepted)

    # ------------------------------------------------------------------
    # 5. Remove matches against baseline, exclusion, accepted
    # ------------------------------------------------------------------
    print("\n[5] Filtering out known articles...")
    print("    (This may take a while for fuzzy matching...)")

    matched_baseline = 0
    matched_exclusion = 0
    matched_accepted = 0
    new_articles = {}

    total = len(combined)
    for idx, (key, rec) in enumerate(combined.items()):
        if (idx + 1) % 100 == 0:
            print(f"    Processing {idx+1}/{total}...", flush=True)

        doi = normalize_doi(rec.get('doi', ''))
        norm_title = rec.get('_norm_title', '')

        # --- Check baseline ---
        # Fast DOI match
        if doi and doi in baseline_dois:
            matched_baseline += 1
            continue
        # Exact title match
        if norm_title and norm_title in baseline_titles:
            matched_baseline += 1
            continue
        # Fuzzy title match (baseline is small: 766)
        if norm_title and is_fuzzy_match(rec['title'], baseline_title_list, 85):
            matched_baseline += 1
            continue

        # --- Check accepted ---
        if doi and doi in accepted_dois:
            matched_accepted += 1
            matched_baseline += 1  # Count as "already known"
            continue
        if norm_title and norm_title in accepted_titles:
            matched_accepted += 1
            matched_baseline += 1
            continue
        if norm_title and is_fuzzy_match(rec['title'], accepted_title_list, 85):
            matched_accepted += 1
            matched_baseline += 1
            continue

        # --- Check exclusion ---
        # Fast DOI match
        if doi and doi in exclusion_dois:
            matched_exclusion += 1
            continue
        # Exact title match
        if norm_title and norm_title in exclusion_titles:
            matched_exclusion += 1
            continue
        # Fuzzy title match (exclusion is large: 6412, so this is expensive)
        if norm_title and is_fuzzy_match(rec['title'], exclusion_title_list, 85):
            matched_exclusion += 1
            continue

        # If we get here, it's genuinely new
        new_articles[key] = rec

    print(f"    Matched baseline/accepted (already known): {matched_baseline}")
    print(f"      (of which accepted from search): {matched_accepted}")
    print(f"    Matched exclusion list (already rejected): {matched_exclusion}")
    print(f"    Genuinely new articles: {len(new_articles)}")

    # ------------------------------------------------------------------
    # 6. Deduplicate new articles by fuzzy title
    # ------------------------------------------------------------------
    print("\n[6] Deduplicating new articles by fuzzy title...")

    deduped = []
    deduped_titles = []  # normalized titles of kept articles
    skipped_dupes = 0

    for key, rec in new_articles.items():
        norm_title = rec.get('_norm_title', '')
        is_dupe = False
        if norm_title:
            # Exact check first
            if norm_title in set(deduped_titles):
                is_dupe = True
            else:
                # Fuzzy check
                for dt in deduped_titles:
                    if fuzz.ratio(norm_title, dt) >= 85:
                        is_dupe = True
                        break

        if is_dupe:
            skipped_dupes += 1
        else:
            # Remove internal field
            clean_rec = {k: v for k, v in rec.items() if not k.startswith('_')}
            deduped.append(clean_rec)
            deduped_titles.append(norm_title)

    print(f"    Duplicate articles removed: {skipped_dupes}")
    print(f"    Final unique new articles: {len(deduped)}")

    # Sort by year then title
    deduped.sort(key=lambda x: (x.get('year', 9999), x.get('title', '').lower()))

    # ------------------------------------------------------------------
    # 7. Save JSON output
    # ------------------------------------------------------------------
    print(f"\n[7] Saving results...")

    with open(OUTPUT_JSON, 'w') as f:
        json.dump(deduped, f, indent=2, ensure_ascii=False)
    print(f"    JSON: {OUTPUT_JSON}")

    # ------------------------------------------------------------------
    # 8. Save CSV output
    # ------------------------------------------------------------------
    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Title', 'Authors', 'Year', 'DOI', 'Journal', 'Source'])
        for rec in deduped:
            writer.writerow([
                rec.get('title', ''),
                rec.get('authors', ''),
                rec.get('year', ''),
                rec.get('doi', ''),
                rec.get('journal', ''),
                rec.get('found_in', ''),
            ])
    print(f"    CSV: {OUTPUT_CSV}")

    # ------------------------------------------------------------------
    # 9. Summary
    # ------------------------------------------------------------------
    year_counts = defaultdict(int)
    source_counts = defaultdict(int)
    for rec in deduped:
        year_counts[rec.get('year')] += 1
        source_counts[rec.get('found_in', 'unknown')] += 1

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Total search results (WoS + Scopus):          {len(wos_records) + len(scopus_records)}")
    print(f"  Total unique 2023+ articles:                   {total_2023_plus}")
    print(f"  Matched baseline/accepted (already known):     {matched_baseline}")
    print(f"  Matched exclusion list (already rejected):     {matched_exclusion}")
    print(f"  Genuinely new (before internal dedup):         {len(new_articles)}")
    print(f"  Internal duplicates removed:                   {skipped_dupes}")
    print(f"  FINAL new articles for review:                 {len(deduped)}")
    print()
    print("  Year breakdown of final new articles:")
    for y in sorted(target_years):
        print(f"    {y}: {year_counts.get(y, 0)}")
    if None in year_counts:
        print(f"    Unknown year: {year_counts[None]}")
    print()
    print("  Source breakdown:")
    for src in ['scopus', 'wos', 'both']:
        if src in source_counts:
            print(f"    {src}: {source_counts[src]}")
    print("=" * 70)


if __name__ == "__main__":
    main()
