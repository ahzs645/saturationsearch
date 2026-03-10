"""
Baseline comparison pipeline for the Nechako Watershed saturation search.

Compares new search results against the known ~700 accepted baseline articles
to identify:
  - Which baseline articles were found (validation)
  - Which search results are new (not in baseline)
  - Which baseline articles were missed (gap detection)

Also builds an exclusion database from the ~1,000 articles that were in the
original ~1,764 raw results but excluded during Jonathan's manual screening.
"""

import json
import csv
import logging
import os
import re
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from fuzzywuzzy import fuzz

logger = logging.getLogger(__name__)

# Matching thresholds
DOI_MATCH = "doi"
TITLE_EXACT_MATCH = "title_exact"
TITLE_FUZZY_MATCH = "title_fuzzy"
AUTHOR_YEAR_MATCH = "author_year"

TITLE_FUZZY_THRESHOLD = 90  # fuzz ratio threshold for title matching


@dataclass
class ComparisonResult:
    """Result of comparing a search result against the baseline."""
    article: Dict
    match_type: Optional[str] = None  # doi, title_exact, title_fuzzy, author_year
    baseline_article: Optional[Dict] = None
    similarity_score: float = 0.0
    status: str = "new"  # "matched", "new"


@dataclass
class BaselineComparisonReport:
    """Summary report of the baseline comparison."""
    total_search_results: int = 0
    total_baseline_articles: int = 0
    matched_articles: int = 0
    new_articles: int = 0
    missed_baseline_articles: int = 0
    match_breakdown: Dict[str, int] = field(default_factory=dict)
    matched_results: List[ComparisonResult] = field(default_factory=list)
    new_results: List[ComparisonResult] = field(default_factory=list)
    missed_baseline: List[Dict] = field(default_factory=list)
    comparison_time: str = ""


def normalize_title(title: str) -> str:
    """Normalize a title for comparison."""
    if not title:
        return ""
    title = title.lower().strip()
    # Remove punctuation and extra whitespace
    title = re.sub(r'[^\w\s]', '', title)
    title = re.sub(r'\s+', ' ', title)
    return title


def normalize_doi(doi: str) -> str:
    """Normalize a DOI for comparison."""
    if not doi:
        return ""
    doi = doi.lower().strip()
    # Remove common prefixes
    doi = re.sub(r'^https?://(dx\.)?doi\.org/', '', doi)
    doi = re.sub(r'^doi:\s*', '', doi)
    return doi


def extract_first_author_surname(authors) -> str:
    """Extract the first author's surname from various author formats."""
    if not authors:
        return ""

    if isinstance(authors, list):
        if len(authors) == 0:
            return ""
        first_author = authors[0]
    elif isinstance(authors, str):
        # Split by semicolon or comma
        first_author = authors.split(';')[0].split(',')[0]
    else:
        return ""

    if isinstance(first_author, dict):
        first_author = first_author.get('family', first_author.get('surname', ''))

    # Handle "Last, First" format
    first_author = str(first_author).strip()
    if ',' in first_author:
        first_author = first_author.split(',')[0]

    return first_author.lower().strip()


def load_baseline_from_json(filepath: str) -> List[Dict]:
    """Load baseline articles from a JSON file."""
    with open(filepath, 'r') as f:
        data = json.load(f)
    # Handle both list format and dict with 'records' key
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and 'records' in data:
        return data['records']
    return []


def load_baseline_from_csv(filepath: str) -> List[Dict]:
    """Load baseline articles from a CSV file."""
    articles = []
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            article = {
                'title': row.get('Title', row.get('title', '')),
                'authors': row.get('Authors', row.get('authors', '')),
                'year': None,
                'doi': row.get('DOI', row.get('doi', '')),
                'journal': row.get('Journal', row.get('journal',
                           row.get('Source Title', row.get('source_title', '')))),
            }
            # Parse year from various column names
            year_str = row.get('Year', row.get('year',
                       row.get('Publication Year', row.get('publication_year', ''))))
            if year_str:
                try:
                    article['year'] = int(str(year_str).strip()[:4])
                except (ValueError, TypeError):
                    pass
            articles.append(article)
    return articles


def load_baseline_from_ris(filepath: str) -> List[Dict]:
    """Load baseline articles from a RIS file."""
    articles = []
    current = {}
    current_tag = None

    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.rstrip('\n')
            if line.startswith('ER  -'):
                if current:
                    articles.append({
                        'title': current.get('TI', current.get('T1', '')),
                        'authors': current.get('AU', []),
                        'year': None,
                        'doi': current.get('DO', ''),
                        'journal': current.get('JO', current.get('T2',
                                   current.get('JF', ''))),
                    })
                    year_str = current.get('PY', current.get('Y1', ''))
                    if year_str:
                        try:
                            articles[-1]['year'] = int(str(year_str).strip()[:4])
                        except (ValueError, TypeError):
                            pass
                current = {}
                current_tag = None
            elif len(line) >= 6 and line[2:6] == '  - ':
                current_tag = line[:2].strip()
                value = line[6:].strip()
                if current_tag == 'AU':
                    current.setdefault('AU', [])
                    current['AU'].append(value)
                else:
                    current[current_tag] = value
            elif current_tag and line.startswith('      '):
                # Continuation line
                if current_tag in current:
                    if isinstance(current[current_tag], list):
                        current[current_tag][-1] += ' ' + line.strip()
                    else:
                        current[current_tag] += ' ' + line.strip()

    return articles


def load_baseline(filepath: str) -> List[Dict]:
    """
    Load baseline articles from a file. Detects format by extension.

    Supported formats: .json, .csv, .ris
    """
    ext = os.path.splitext(filepath)[1].lower()
    if ext == '.json':
        return load_baseline_from_json(filepath)
    elif ext == '.csv':
        return load_baseline_from_csv(filepath)
    elif ext == '.ris':
        return load_baseline_from_ris(filepath)
    else:
        raise ValueError(f"Unsupported baseline file format: {ext}. Use .json, .csv, or .ris")


def compare_against_baseline(
    search_results: List[Dict],
    baseline_articles: List[Dict]
) -> BaselineComparisonReport:
    """
    Compare search results against baseline accepted articles.

    Uses multi-level matching:
      1. DOI match (exact, normalized)
      2. Title exact match (normalized)
      3. Title fuzzy match (>= threshold)
      4. First author surname + year match

    Args:
        search_results: Articles from the current search run
        baseline_articles: Known accepted articles (~700)

    Returns:
        BaselineComparisonReport with full comparison details
    """
    start_time = datetime.now()
    logger.info(f"Comparing {len(search_results)} search results against "
                f"{len(baseline_articles)} baseline articles")

    report = BaselineComparisonReport(
        total_search_results=len(search_results),
        total_baseline_articles=len(baseline_articles),
        match_breakdown={DOI_MATCH: 0, TITLE_EXACT_MATCH: 0,
                         TITLE_FUZZY_MATCH: 0, AUTHOR_YEAR_MATCH: 0},
    )

    # Build baseline indexes for fast lookup
    baseline_by_doi = {}
    baseline_by_title = {}
    baseline_by_author_year = {}
    baseline_matched = set()  # Track which baseline articles were found

    for i, article in enumerate(baseline_articles):
        doi = normalize_doi(article.get('doi', ''))
        if doi:
            baseline_by_doi[doi] = (i, article)

        title = normalize_title(article.get('title', ''))
        if title:
            baseline_by_title[title] = (i, article)

        surname = extract_first_author_surname(article.get('authors', ''))
        year = article.get('year')
        if surname and year:
            key = f"{surname}_{year}"
            baseline_by_author_year.setdefault(key, []).append((i, article))

    # Compare each search result against baseline
    for result in search_results:
        comparison = ComparisonResult(article=result)

        # Level 1: DOI match
        doi = normalize_doi(result.get('doi', ''))
        if doi and doi in baseline_by_doi:
            idx, baseline_art = baseline_by_doi[doi]
            comparison.match_type = DOI_MATCH
            comparison.baseline_article = baseline_art
            comparison.similarity_score = 1.0
            comparison.status = "matched"
            baseline_matched.add(idx)
            report.match_breakdown[DOI_MATCH] += 1
            report.matched_results.append(comparison)
            continue

        # Level 2: Title exact match
        title = normalize_title(result.get('title', ''))
        if title and title in baseline_by_title:
            idx, baseline_art = baseline_by_title[title]
            comparison.match_type = TITLE_EXACT_MATCH
            comparison.baseline_article = baseline_art
            comparison.similarity_score = 1.0
            comparison.status = "matched"
            baseline_matched.add(idx)
            report.match_breakdown[TITLE_EXACT_MATCH] += 1
            report.matched_results.append(comparison)
            continue

        # Level 3: Title fuzzy match
        if title:
            best_score = 0
            best_match = None
            best_idx = None
            for norm_title, (idx, baseline_art) in baseline_by_title.items():
                score = fuzz.ratio(title, norm_title)
                if score > best_score:
                    best_score = score
                    best_match = baseline_art
                    best_idx = idx

            if best_score >= TITLE_FUZZY_THRESHOLD:
                comparison.match_type = TITLE_FUZZY_MATCH
                comparison.baseline_article = best_match
                comparison.similarity_score = best_score / 100.0
                comparison.status = "matched"
                baseline_matched.add(best_idx)
                report.match_breakdown[TITLE_FUZZY_MATCH] += 1
                report.matched_results.append(comparison)
                continue

        # Level 4: Author + year match
        surname = extract_first_author_surname(result.get('authors', ''))
        year = result.get('year')
        if surname and year:
            key = f"{surname}_{year}"
            if key in baseline_by_author_year:
                # Check title similarity as confirmation
                candidates = baseline_by_author_year[key]
                for idx, baseline_art in candidates:
                    b_title = normalize_title(baseline_art.get('title', ''))
                    if b_title and title:
                        score = fuzz.ratio(title, b_title)
                        if score >= 70:  # Lower threshold since author+year already match
                            comparison.match_type = AUTHOR_YEAR_MATCH
                            comparison.baseline_article = baseline_art
                            comparison.similarity_score = score / 100.0
                            comparison.status = "matched"
                            baseline_matched.add(idx)
                            report.match_breakdown[AUTHOR_YEAR_MATCH] += 1
                            report.matched_results.append(comparison)
                            break
                if comparison.status == "matched":
                    continue

        # No match found — this is a new article
        comparison.status = "new"
        report.new_results.append(comparison)

    # Identify missed baseline articles (in baseline but not found in search)
    for i, article in enumerate(baseline_articles):
        if i not in baseline_matched:
            report.missed_baseline.append(article)

    report.matched_articles = len(report.matched_results)
    report.new_articles = len(report.new_results)
    report.missed_baseline_articles = len(report.missed_baseline)
    report.comparison_time = str(datetime.now() - start_time)

    logger.info(f"Comparison complete: {report.matched_articles} matched, "
                f"{report.new_articles} new, "
                f"{report.missed_baseline_articles} missed from baseline")
    logger.info(f"Match breakdown: {report.match_breakdown}")

    return report


def build_exclusion_database(
    raw_search_results: List[Dict],
    accepted_baseline: List[Dict],
    output_path: Optional[str] = None
) -> Dict:
    """
    Build an exclusion database by identifying articles from raw search results
    that were NOT in the accepted baseline (i.e., they were excluded by Jonathan).

    Args:
        raw_search_results: The ~1,764 raw results from the original search
        accepted_baseline: The ~700 accepted articles

    Returns:
        Dict with excluded articles list and metadata
    """
    logger.info("Building exclusion database...")
    logger.info(f"  Raw results: {len(raw_search_results)}")
    logger.info(f"  Accepted baseline: {len(accepted_baseline)}")

    # Compare raw results against accepted baseline
    report = compare_against_baseline(raw_search_results, accepted_baseline)

    # The "new" results (not matched to baseline) are the excluded articles
    excluded_articles = [r.article for r in report.new_results]

    exclusion_db = {
        'metadata': {
            'created': datetime.now().isoformat(),
            'raw_results_count': len(raw_search_results),
            'accepted_count': len(accepted_baseline),
            'excluded_count': len(excluded_articles),
            'matched_count': report.matched_articles,
            'match_breakdown': report.match_breakdown,
        },
        'excluded_articles': excluded_articles,
    }

    if output_path:
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(exclusion_db, f, indent=2, default=str)
        logger.info(f"Exclusion database saved to: {output_path}")

    logger.info(f"Exclusion database built: {len(excluded_articles)} excluded articles")
    return exclusion_db


def filter_against_exclusion_database(
    new_results: List[Dict],
    exclusion_db_path: str
) -> Tuple[List[Dict], List[Dict]]:
    """
    Filter new search results against a previously built exclusion database.
    Returns articles that should be reviewed and articles that were previously excluded.

    Args:
        new_results: New search results to filter
        exclusion_db_path: Path to the exclusion database JSON

    Returns:
        Tuple of (articles_to_review, previously_excluded)
    """
    with open(exclusion_db_path, 'r') as f:
        exclusion_db = json.load(f)

    excluded_articles = exclusion_db.get('excluded_articles', [])
    logger.info(f"Filtering {len(new_results)} results against "
                f"{len(excluded_articles)} excluded articles")

    # Compare new results against exclusion database
    report = compare_against_baseline(new_results, excluded_articles)

    # "matched" = previously excluded, "new" = needs review
    articles_to_review = [r.article for r in report.new_results]
    previously_excluded = [r.article for r in report.matched_results]

    logger.info(f"Filtering result: {len(articles_to_review)} to review, "
                f"{len(previously_excluded)} previously excluded")

    return articles_to_review, previously_excluded


def generate_comparison_report(report: BaselineComparisonReport) -> Dict:
    """Generate a summary report from a baseline comparison."""
    recall = (report.matched_articles / report.total_baseline_articles
              if report.total_baseline_articles > 0 else 0)

    return {
        'summary': {
            'search_results': report.total_search_results,
            'baseline_articles': report.total_baseline_articles,
            'matched': report.matched_articles,
            'new_articles': report.new_articles,
            'missed_from_baseline': report.missed_baseline_articles,
            'recall': f"{recall:.1%}",
            'comparison_time': report.comparison_time,
        },
        'match_breakdown': report.match_breakdown,
        'missed_articles': [
            {
                'title': a.get('title', 'Unknown'),
                'authors': a.get('authors', ''),
                'year': a.get('year'),
                'doi': a.get('doi', ''),
                'journal': a.get('journal', ''),
            }
            for a in report.missed_baseline
        ],
        'new_articles_sample': [
            {
                'title': r.article.get('title', 'Unknown'),
                'authors': r.article.get('authors', ''),
                'year': r.article.get('year'),
                'doi': r.article.get('doi', ''),
            }
            for r in report.new_results[:50]  # First 50 as sample
        ],
    }
