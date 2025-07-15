"""
Main orchestration system for the Nechako Watershed Saturation Search automation.
Coordinates all components to execute the complete search and processing pipeline.
"""

import logging
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import argparse

from api.web_of_science import WebOfScienceAPI, convert_wos_record_to_standard_format
from api.scopus import ScopusAPI, convert_scopus_record_to_standard_format
from api.zotero_integration import ZoteroManager
from processing.duplicate_detection import AdvancedDuplicateDetector, analyze_duplicate_patterns
from processing.automated_screening import AutomatedScreener, generate_screening_summary
from utils.location_terms import build_location_query, build_priority_location_query

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/saturation_search.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class SaturationSearchOrchestrator:
    """
    Main orchestrator for the automated saturation search system.
    
    Coordinates:
    1. Database searches (Web of Science, Scopus)
    2. Duplicate detection and removal
    3. Automated screening and classification
    4. Zotero organization and upload
    5. Validation and reporting
    """
    
    def __init__(self, 
                 use_priority_terms: bool = False,
                 max_results_per_db: int = 1000):
        """
        Initialize the orchestrator.
        
        Args:
            use_priority_terms (bool): Use priority location terms only
            max_results_per_db (int): Maximum results per database
        """
        self.use_priority_terms = use_priority_terms
        self.max_results_per_db = max_results_per_db
        
        # Initialize components
        self.wos_api = None
        self.scopus_api = None
        self.zotero_manager = None
        self.duplicate_detector = AdvancedDuplicateDetector()
        self.screener = AutomatedScreener()
        
        self._initialize_apis()
    
    def _initialize_apis(self):
        """Initialize API connections."""
        try:
            # Initialize Web of Science API
            self.wos_api = WebOfScienceAPI()
            if self.wos_api.validate_api_key():
                logger.info("Web of Science API connected successfully")
            else:
                logger.warning("Web of Science API connection failed")
                self.wos_api = None
        except Exception as e:
            logger.warning(f"Failed to initialize Web of Science API: {e}")
            self.wos_api = None
        
        try:
            # Initialize Scopus API
            self.scopus_api = ScopusAPI()
            if self.scopus_api.validate_api_key():
                logger.info("Scopus API connected successfully")
            else:
                logger.warning("Scopus API connection failed")
                self.scopus_api = None
        except Exception as e:
            logger.warning(f"Failed to initialize Scopus API: {e}")
            self.scopus_api = None
        
        try:
            # Initialize Zotero manager
            self.zotero_manager = ZoteroManager()
            if self.zotero_manager.validate_connection():
                logger.info("Zotero API connected successfully")
            else:
                logger.warning("Zotero API connection failed")
                self.zotero_manager = None
        except Exception as e:
            logger.warning(f"Failed to initialize Zotero API: {e}")
            self.zotero_manager = None
    
    def execute_full_search(self,
                           date_start: str = "1930-01-01",
                           date_end: Optional[str] = None,
                           save_raw_results: bool = True) -> Dict:
        """
        Execute the complete saturation search pipeline.
        
        Args:
            date_start (str): Start date for search (YYYY-MM-DD)
            date_end (str): End date for search (YYYY-MM-DD)
            save_raw_results (bool): Save raw search results to files
            
        Returns:
            Dict: Complete search results and processing report
        """
        logger.info("=" * 80)
        logger.info("STARTING NECHAKO WATERSHED SATURATION SEARCH")
        logger.info("=" * 80)
        
        search_start_time = datetime.now()
        
        if date_end is None:
            date_end = datetime.now().strftime("%Y-%m-%d")
        
        logger.info(f"Search period: {date_start} to {date_end}")
        logger.info(f"Using {'priority' if self.use_priority_terms else 'comprehensive'} location terms")
        
        # Step 1: Execute database searches
        logger.info("\n" + "="*50)
        logger.info("STEP 1: DATABASE SEARCHES")
        logger.info("="*50)
        
        search_results = self._execute_database_searches(date_start, date_end)
        
        if save_raw_results:
            self._save_raw_results(search_results, search_start_time)
        
        # Step 2: Combine and standardize results
        logger.info("\n" + "="*50)
        logger.info("STEP 2: COMBINING RESULTS")
        logger.info("="*50)
        
        combined_articles = self._combine_search_results(search_results)
        logger.info(f"Combined total: {len(combined_articles)} articles")
        
        # Step 3: Duplicate detection
        logger.info("\n" + "="*50)
        logger.info("STEP 3: DUPLICATE DETECTION")
        logger.info("="*50)
        
        unique_articles, dedup_report = self.duplicate_detector.detect_duplicates(combined_articles)
        duplicate_analysis = analyze_duplicate_patterns(dedup_report)
        
        logger.info(f"Unique articles after deduplication: {len(unique_articles)}")
        logger.info(f"Duplicates removed: {dedup_report.duplicates_removed}")
        logger.info(f"Duplicate rate: {duplicate_analysis['duplicate_rate']:.2%}")
        
        # Step 4: Automated screening
        logger.info("\n" + "="*50)
        logger.info("STEP 4: AUTOMATED SCREENING")
        logger.info("="*50)
        
        screening_decisions, screening_report = self.screener.screen_articles(unique_articles)
        screening_summary = generate_screening_summary(screening_decisions)
        
        logger.info(f"Screening results: {screening_report.included_articles} included, "
                   f"{screening_report.excluded_articles} excluded, "
                   f"{screening_report.manual_review_articles} manual review")
        
        # Step 5: Zotero organization (if available)
        zotero_results = None
        if self.zotero_manager:
            logger.info("\n" + "="*50)
            logger.info("STEP 5: ZOTERO ORGANIZATION")
            logger.info("="*50)
            
            try:
                zotero_results = self.zotero_manager.organize_screening_results(
                    screening_decisions, search_start_time
                )
                logger.info("Articles successfully organized in Zotero")
            except Exception as e:
                logger.error(f"Zotero organization failed: {e}")
                zotero_results = {'error': str(e)}
        
        # Step 6: Generate final report
        logger.info("\n" + "="*50)
        logger.info("STEP 6: FINAL REPORT")
        logger.info("="*50)
        
        final_report = self._generate_final_report(
            search_results, dedup_report, duplicate_analysis,
            screening_report, screening_summary, zotero_results,
            search_start_time, date_start, date_end
        )
        
        # Save final report
        report_filename = f"results/saturation_search_report_{search_start_time.strftime('%Y%m%d_%H%M%S')}.json"
        os.makedirs('results', exist_ok=True)
        
        with open(report_filename, 'w') as f:
            json.dump(final_report, f, indent=2, default=str)
        
        logger.info(f"Final report saved to: {report_filename}")
        
        total_time = datetime.now() - search_start_time
        logger.info(f"\nSEARCH COMPLETED in {total_time}")
        logger.info("="*80)
        
        return final_report
    
    def _execute_database_searches(self, date_start: str, date_end: str) -> Dict:
        """Execute searches across all available databases."""
        search_results = {}
        
        # Web of Science search
        if self.wos_api:
            try:
                logger.info("Executing Web of Science search...")
                wos_results = self.wos_api.nechako_saturation_search(
                    date_start=date_start,
                    date_end=date_end,
                    use_priority_terms=self.use_priority_terms
                )
                search_results['web_of_science'] = wos_results
                logger.info(f"Web of Science: {len(wos_results['records'])} articles retrieved")
            except Exception as e:
                logger.error(f"Web of Science search failed: {e}")
                search_results['web_of_science'] = {'error': str(e), 'records': []}
        
        # Scopus search
        if self.scopus_api:
            try:
                logger.info("Executing Scopus search...")
                # Convert date format for Scopus (year only)
                scopus_start_year = date_start.split('-')[0]
                scopus_end_year = date_end.split('-')[0]
                
                scopus_results = self.scopus_api.nechako_saturation_search(
                    date_start=scopus_start_year,
                    date_end=scopus_end_year,
                    use_priority_terms=self.use_priority_terms
                )
                search_results['scopus'] = scopus_results
                logger.info(f"Scopus: {len(scopus_results['records'])} articles retrieved")
            except Exception as e:
                logger.error(f"Scopus search failed: {e}")
                search_results['scopus'] = {'error': str(e), 'records': []}
        
        return search_results
    
    def _combine_search_results(self, search_results: Dict) -> List[Dict]:
        """Combine and standardize results from all databases."""
        combined_articles = []
        
        # Process Web of Science results
        if 'web_of_science' in search_results and 'records' in search_results['web_of_science']:
            wos_records = search_results['web_of_science']['records']
            for record in wos_records:
                standardized = convert_wos_record_to_standard_format(record)
                combined_articles.append(standardized)
        
        # Process Scopus results
        if 'scopus' in search_results and 'records' in search_results['scopus']:
            scopus_records = search_results['scopus']['records']
            for record in scopus_records:
                standardized = convert_scopus_record_to_standard_format(record)
                combined_articles.append(standardized)
        
        return combined_articles
    
    def _save_raw_results(self, search_results: Dict, timestamp: datetime):
        """Save raw search results to files."""
        os.makedirs('results/raw', exist_ok=True)
        
        timestamp_str = timestamp.strftime('%Y%m%d_%H%M%S')
        
        for database, results in search_results.items():
            filename = f"results/raw/{database}_raw_{timestamp_str}.json"
            with open(filename, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            logger.info(f"Raw {database} results saved to: {filename}")
    
    def _generate_final_report(self, 
                              search_results: Dict,
                              dedup_report,
                              duplicate_analysis: Dict,
                              screening_report,
                              screening_summary: Dict,
                              zotero_results: Optional[Dict],
                              search_start_time: datetime,
                              date_start: str,
                              date_end: str) -> Dict:
        """Generate comprehensive final report."""
        
        return {
            'search_metadata': {
                'search_id': search_start_time.strftime('%Y%m%d_%H%M%S'),
                'search_date': search_start_time.isoformat(),
                'date_range': {'start': date_start, 'end': date_end},
                'search_type': 'Nechako Watershed Saturation Search',
                'location_terms_used': 'priority' if self.use_priority_terms else 'comprehensive',
                'processing_time': str(datetime.now() - search_start_time)
            },
            'database_results': {
                database: {
                    'total_results': results.get('total_results', 0),
                    'retrieved_results': results.get('retrieved_results', 0),
                    'query': results.get('query', ''),
                    'error': results.get('error')
                }
                for database, results in search_results.items()
            },
            'deduplication': {
                'input_articles': dedup_report.total_input_articles,
                'unique_articles': dedup_report.unique_articles,
                'duplicates_removed': dedup_report.duplicates_removed,
                'duplicate_rate': duplicate_analysis['duplicate_rate'],
                'matches_by_type': dedup_report.matches_by_type,
                'processing_time': dedup_report.processing_time
            },
            'screening': {
                'total_articles': screening_report.total_articles,
                'included_articles': screening_report.included_articles,
                'excluded_articles': screening_report.excluded_articles,
                'manual_review_articles': screening_report.manual_review_articles,
                'inclusion_rate': screening_summary['screening_summary']['inclusion_rate'],
                'theme_distribution': screening_report.theme_distribution,
                'top_exclusion_reasons': screening_summary['top_exclusion_reasons'],
                'average_confidence': screening_report.average_confidence,
                'processing_time': screening_report.processing_time
            },
            'quality_metrics': {
                'geographic_relevance': screening_summary['geographic_relevance'],
                'confidence_distribution': screening_summary['quality_metrics'],
                'duplicate_detection_confidence': duplicate_analysis.get('confidence_distribution', {})
            },
            'zotero_organization': zotero_results,
            'recommendations': self._generate_recommendations(
                dedup_report, screening_report, duplicate_analysis, screening_summary
            )
        }
    
    def _generate_recommendations(self, 
                                 dedup_report,
                                 screening_report, 
                                 duplicate_analysis: Dict,
                                 screening_summary: Dict) -> List[str]:
        """Generate recommendations based on search results."""
        recommendations = []
        
        # Duplicate detection recommendations
        duplicate_rate = duplicate_analysis['duplicate_rate']
        if duplicate_rate > 0.3:
            recommendations.append(
                f"High duplicate rate ({duplicate_rate:.1%}) detected. Consider refining search terms "
                "or database selection to reduce overlap."
            )
        
        # Screening recommendations
        manual_review_rate = screening_report.manual_review_articles / screening_report.total_articles
        if manual_review_rate > 0.15:
            recommendations.append(
                f"High manual review rate ({manual_review_rate:.1%}). Consider training the "
                "screening algorithm with more examples to improve automation."
            )
        
        # Geographic relevance recommendations
        geo_stats = screening_summary['geographic_relevance']
        if geo_stats['mean_score'] < 0.5:
            recommendations.append(
                "Low average geographic relevance detected. Consider expanding location terms "
                "or reviewing search strategy."
            )
        
        # Theme distribution recommendations
        theme_dist = screening_report.theme_distribution
        if theme_dist and max(theme_dist.values()) / sum(theme_dist.values()) > 0.8:
            recommendations.append(
                "Highly skewed theme distribution. Consider expanding search terms to capture "
                "more diverse research areas."
            )
        
        # Success recommendations
        inclusion_rate = screening_summary['screening_summary']['inclusion_rate']
        if inclusion_rate > 0.15 and duplicate_rate < 0.2:
            recommendations.append(
                "Search performed well with good inclusion rate and low duplicates. "
                "Results appear suitable for systematic review."
            )
        
        return recommendations


def main():
    """Main entry point for the saturation search system."""
    parser = argparse.ArgumentParser(description='Nechako Watershed Saturation Search')
    parser.add_argument('--start-date', default='1930-01-01', 
                       help='Start date for search (YYYY-MM-DD)')
    parser.add_argument('--end-date', default=None,
                       help='End date for search (YYYY-MM-DD, defaults to today)')
    parser.add_argument('--priority-terms', action='store_true',
                       help='Use only priority location terms')
    parser.add_argument('--max-results', type=int, default=1000,
                       help='Maximum results per database')
    parser.add_argument('--save-raw', action='store_true', default=True,
                       help='Save raw search results')
    
    args = parser.parse_args()
    
    # Create orchestrator
    orchestrator = SaturationSearchOrchestrator(
        use_priority_terms=args.priority_terms,
        max_results_per_db=args.max_results
    )
    
    # Execute search
    try:
        results = orchestrator.execute_full_search(
            date_start=args.start_date,
            date_end=args.end_date,
            save_raw_results=args.save_raw
        )
        
        print("\n" + "="*80)
        print("SEARCH SUMMARY")
        print("="*80)
        print(f"Total articles processed: {results['screening']['total_articles']}")
        print(f"Articles included: {results['screening']['included_articles']}")
        print(f"Articles excluded: {results['screening']['excluded_articles']}")
        print(f"Manual review required: {results['screening']['manual_review_articles']}")
        print(f"Inclusion rate: {results['screening']['inclusion_rate']:.1%}")
        print("\nRecommendations:")
        for i, rec in enumerate(results['recommendations'], 1):
            print(f"{i}. {rec}")
        
    except Exception as e:
        logger.error(f"Search execution failed: {e}")
        raise


if __name__ == "__main__":
    main()