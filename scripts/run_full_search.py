#!/usr/bin/env python3
"""
Run the full Nechako Watershed saturation search across all databases.
Uses comprehensive location terms and the corrected query structure
matching Terry's search (geographic TS terms AND regional all-fields filter).
"""

import sys
import os
import json
import logging
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from config import WOS_API_KEY, SCOPUS_API_KEY

# Setup logging
os.makedirs('logs', exist_ok=True)
os.makedirs('results/raw', exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/full_search_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Search parameters
DATE_START = "1930-01-01"
DATE_END = "2025-12-31"
USE_PRIORITY_TERMS = False  # Comprehensive search
MAX_RESULTS = 5000  # Per chunk — high enough to get everything


def run_wos_search():
    """Run Web of Science search."""
    if not WOS_API_KEY or WOS_API_KEY == 'your_web_of_science_api_key_here':
        logger.warning("No WoS API key — skipping")
        return None

    from api.web_of_science_starter import WebOfScienceStarterAPI

    logger.info("=" * 60)
    logger.info("WEB OF SCIENCE SEARCH")
    logger.info("=" * 60)

    wos = WebOfScienceStarterAPI()
    results = wos.nechako_saturation_search(
        date_start=DATE_START,
        date_end=DATE_END,
        use_priority_terms=USE_PRIORITY_TERMS,
        max_results=MAX_RESULTS
    )

    logger.info(f"WoS: {results['retrieved_results']} unique records retrieved "
                f"({results['total_results']} total available across chunks)")

    # Save raw results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filepath = f'results/raw/wos_full_{timestamp}.json'
    with open(filepath, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    logger.info(f"WoS results saved to {filepath}")

    return results


def run_scopus_search():
    """Run Scopus search."""
    if not SCOPUS_API_KEY or SCOPUS_API_KEY == 'your_scopus_api_key_here':
        logger.warning("No Scopus API key — skipping")
        return None

    from api.scopus_hybrid import ScopusHybridAPI

    logger.info("=" * 60)
    logger.info("SCOPUS SEARCH")
    logger.info("=" * 60)

    scopus = ScopusHybridAPI()
    results = scopus.nechako_saturation_search(
        date_start=DATE_START,
        date_end=DATE_END,
        use_priority_terms=USE_PRIORITY_TERMS,
        max_results=MAX_RESULTS
    )

    logger.info(f"Scopus: {results['retrieved_results']} unique records retrieved "
                f"({results['total_results']} total available across chunks)")

    # Save raw results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filepath = f'results/raw/scopus_full_{timestamp}.json'
    with open(filepath, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    logger.info(f"Scopus results saved to {filepath}")

    return results


def main():
    start_time = datetime.now()
    logger.info("FULL NECHAKO WATERSHED SATURATION SEARCH")
    logger.info(f"Date range: {DATE_START} to {DATE_END}")
    logger.info(f"Terms: {'priority' if USE_PRIORITY_TERMS else 'comprehensive'}")
    logger.info(f"Started at: {start_time.isoformat()}")

    # Run both searches
    wos_results = run_wos_search()
    scopus_results = run_scopus_search()

    # Summary
    elapsed = datetime.now() - start_time
    logger.info("")
    logger.info("=" * 60)
    logger.info("SEARCH COMPLETE")
    logger.info("=" * 60)

    wos_count = wos_results['retrieved_results'] if wos_results else 0
    scopus_count = scopus_results['retrieved_results'] if scopus_results else 0

    logger.info(f"Web of Science: {wos_count} records")
    logger.info(f"Scopus:         {scopus_count} records")
    logger.info(f"Combined:       {wos_count + scopus_count} records (before dedup)")
    logger.info(f"Time elapsed:   {elapsed}")

    # Save combined summary
    summary = {
        'search_date': start_time.isoformat(),
        'date_range': {'start': DATE_START, 'end': DATE_END},
        'terms': 'comprehensive' if not USE_PRIORITY_TERMS else 'priority',
        'wos_records': wos_count,
        'scopus_records': scopus_count,
        'combined_before_dedup': wos_count + scopus_count,
        'elapsed_time': str(elapsed),
        'wos_chunks': wos_results['metadata'].get('chunks_executed', 0) if wos_results else 0,
        'scopus_chunks': scopus_results['metadata'].get('chunks_executed', 0) if scopus_results else 0,
    }

    summary_path = f'results/search_summary_{start_time.strftime("%Y%m%d_%H%M%S")}.json'
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    logger.info(f"Summary saved to {summary_path}")


if __name__ == "__main__":
    main()
