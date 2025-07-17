#!/usr/bin/env python3
"""
Smart Search Script with Automatic Query Optimization
Demonstrates integration of chunked search and progressive enhancement.
"""

import sys
import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import argparse
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.query_manager import DynamicQueryManager, QueryResult
from src.utils.chunked_search import analyze_chunking_efficiency
from src.api.scopus_hybrid import ScopusHybridAPI
from src.api.web_of_science_starter import WebOfScienceStarterAPI
from src.api.zotero_integration import ZoteroManager
import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SmartSearchOrchestrator:
    """
    Orchestrates smart search across multiple APIs with automatic optimization.
    """
    
    def __init__(self):
        self.query_manager = DynamicQueryManager()
        self.apis = {}
        self._initialize_apis()
    
    def _initialize_apis(self):
        """Initialize available API clients."""
        try:
            self.apis['scopus'] = ScopusHybridAPI()
            logger.info("✅ Scopus API initialized")
        except Exception as e:
            logger.warning(f"⚠️  Scopus API not available: {e}")
        
        try:
            self.apis['wos'] = WebOfScienceStarterAPI()
            logger.info("✅ Web of Science API initialized")
        except Exception as e:
            logger.warning(f"⚠️  Web of Science API not available: {e}")
        
        try:
            self.apis['zotero'] = ZoteroManager()
            logger.info("✅ Zotero API initialized")
        except Exception as e:
            logger.warning(f"⚠️  Zotero API not available: {e}")
    
    def analyze_search_strategy(self, api_type: str, use_priority_terms: bool = False) -> Dict[str, Any]:
        """
        Analyze the best search strategy for given parameters.
        
        Args:
            api_type: Target API type
            use_priority_terms: Whether to use priority terms only
            
        Returns:
            Analysis results with strategy recommendations
        """
        if api_type not in self.apis:
            raise ValueError(f"API type '{api_type}' not available. Available: {list(self.apis.keys())}")
        
        logger.info(f"🔍 Analyzing search strategy for {api_type.upper()}")
        
        # Get feasibility analysis
        analysis = self.query_manager.test_query_feasibility(api_type, use_priority_terms)
        
        # Add chunking efficiency analysis
        chunking_analysis = analyze_chunking_efficiency(api_type, use_priority_terms)
        analysis['chunking_efficiency'] = chunking_analysis
        
        return analysis
    
    def execute_smart_search(self, api_type: str, use_priority_terms: bool = False,
                           force_strategy: Optional[str] = None,
                           dry_run: bool = True) -> Dict[str, Any]:
        """
        Execute a smart search with automatic optimization.
        
        Args:
            api_type: Target API type
            use_priority_terms: Whether to use priority terms only
            force_strategy: Force specific strategy (direct, chunked, progressive)
            dry_run: If True, only analyze without executing searches
            
        Returns:
            Search results and execution summary
        """
        if api_type not in self.apis:
            raise ValueError(f"API type '{api_type}' not available")
        
        api_client = self.apis[api_type]
        
        # Analyze strategy
        analysis = self.analyze_search_strategy(api_type, use_priority_terms)
        strategy = force_strategy or analysis['recommended_strategy']
        
        logger.info(f"📊 Strategy Analysis Complete:")
        logger.info(f"   • Recommended: {analysis['recommended_strategy']}")
        logger.info(f"   • Using: {strategy}")
        logger.info(f"   • Reasoning: {analysis['reasoning']}")
        
        # Build optimized queries
        query_results = self.query_manager.build_optimal_query(
            api_type, use_priority_terms, force_strategy=strategy
        )
        
        execution_summary = {
            'api_type': api_type,
            'strategy_used': strategy,
            'use_priority_terms': use_priority_terms,
            'analysis': analysis,
            'dry_run': dry_run,
            'queries_planned': [],
            'search_results': [],
            'total_articles': 0,
            'execution_time': None,
            'errors': []
        }
        
        # Handle different query result types
        if isinstance(query_results, list):
            # Chunked strategy
            for i, result in enumerate(query_results):
                query_info = {
                    'chunk_id': result.chunk_info.get('chunk_id', f'chunk_{i+1}'),
                    'query_length': result.query_length,
                    'terms_count': len(result.terms_used),
                    'query': result.query[:100] + '...' if len(result.query) > 100 else result.query
                }
                execution_summary['queries_planned'].append(query_info)
        else:
            # Single query strategy
            query_info = {
                'strategy': strategy,
                'query_length': query_results.query_length,
                'terms_count': len(query_results.terms_used),
                'terms_excluded': len(query_results.terms_excluded or []),
                'query': query_results.query[:100] + '...' if len(query_results.query) > 100 else query_results.query
            }
            execution_summary['queries_planned'].append(query_info)
        
        if dry_run:
            logger.info(f"🏃 DRY RUN - No actual searches executed")
            logger.info(f"   • Queries planned: {len(execution_summary['queries_planned'])}")
            return execution_summary
        
        # Execute actual searches
        start_time = datetime.now()
        
        try:
            if isinstance(query_results, list):
                # Execute chunked searches
                logger.info(f"🔄 Executing {len(query_results)} chunked searches...")
                for i, result in enumerate(query_results):
                    if not result.success:
                        error_msg = f"Chunk {i+1} query too long: {result.query_length} chars"
                        execution_summary['errors'].append(error_msg)
                        logger.error(error_msg)
                        continue
                    
                    # Format query for API
                    formatted_query = self.query_manager.format_query_for_api(
                        result, api_type, {"language": "english"}
                    )
                    
                    logger.info(f"   • Executing chunk {i+1}/{len(query_results)}...")
                    search_result = self._execute_api_search(api_client, formatted_query, api_type)
                    search_result['chunk_info'] = result.chunk_info
                    execution_summary['search_results'].append(search_result)
                    execution_summary['total_articles'] += search_result.get('count', 0)
            
            else:
                # Execute single search
                logger.info(f"🔍 Executing single optimized search...")
                formatted_query = self.query_manager.format_query_for_api(
                    query_results, api_type, {"language": "english"}
                )
                
                search_result = self._execute_api_search(api_client, formatted_query, api_type)
                execution_summary['search_results'].append(search_result)
                execution_summary['total_articles'] = search_result.get('count', 0)
        
        except Exception as e:
            error_msg = f"Search execution failed: {str(e)}"
            execution_summary['errors'].append(error_msg)
            logger.error(error_msg)
        
        execution_summary['execution_time'] = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"✅ Search Complete:")
        logger.info(f"   • Total articles found: {execution_summary['total_articles']}")
        logger.info(f"   • Execution time: {execution_summary['execution_time']:.1f}s")
        logger.info(f"   • Errors: {len(execution_summary['errors'])}")
        
        return execution_summary
    
    def _execute_api_search(self, api_client, query: str, api_type: str) -> Dict[str, Any]:
        """Execute search on specific API client."""
        try:
            if api_type == 'scopus':
                results = api_client.search_articles(query)
            elif api_type == 'wos':
                results = api_client.search_articles(query)
            elif api_type == 'zotero':
                # ZoteroManager doesn't have a direct search method, skip for now
                results = []
            else:
                raise ValueError(f"Unknown API type: {api_type}")
            
            return {
                'success': True,
                'count': len(results) if isinstance(results, list) else results.get('count', 0),
                'query': query[:50] + '...',
                'api_type': api_type
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'query': query[:50] + '...',
                'api_type': api_type,
                'count': 0
            }
    
    def run_comparison_analysis(self, use_priority_terms: bool = False) -> Dict[str, Any]:
        """
        Run comparison analysis across all available APIs.
        """
        logger.info(f"🔬 Running comparison analysis across APIs")
        
        comparison = {
            'use_priority_terms': use_priority_terms,
            'apis_analyzed': [],
            'summary': {}
        }
        
        for api_type in self.apis.keys():
            try:
                analysis = self.analyze_search_strategy(api_type, use_priority_terms)
                comparison['apis_analyzed'].append({
                    'api_type': api_type,
                    'recommended_strategy': analysis['recommended_strategy'],
                    'reasoning': analysis['reasoning'],
                    'api_limit': analysis['api_limit'],
                    'strategies': analysis['strategies']
                })
            except Exception as e:
                logger.error(f"Analysis failed for {api_type}: {e}")
        
        # Generate summary recommendations
        strategies_used = [api['recommended_strategy'] for api in comparison['apis_analyzed']]
        comparison['summary'] = {
            'total_apis': len(comparison['apis_analyzed']),
            'strategy_distribution': {
                'direct': strategies_used.count('direct'),
                'progressive': strategies_used.count('progressive'),
                'chunked': strategies_used.count('chunked')
            },
            'recommendation': 'Use priority terms for faster searches' if use_priority_terms else 
                            'Consider priority terms to reduce API calls'
        }
        
        return comparison


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(description='Smart Search with Automatic Query Optimization')
    parser.add_argument('--api', choices=['scopus', 'wos', 'zotero', 'all'], 
                       default='scopus', help='API to use for search')
    parser.add_argument('--priority', action='store_true', 
                       help='Use priority terms only (faster, fewer results)')
    parser.add_argument('--strategy', choices=['direct', 'chunked', 'progressive'], 
                       help='Force specific search strategy')
    parser.add_argument('--execute', action='store_true', 
                       help='Execute actual searches (default is dry run)')
    parser.add_argument('--analyze-only', action='store_true', 
                       help='Only analyze strategies without building queries')
    parser.add_argument('--compare', action='store_true', 
                       help='Compare strategies across all available APIs')
    
    args = parser.parse_args()
    
    orchestrator = SmartSearchOrchestrator()
    
    if args.compare:
        # Run comparison analysis
        print("\n🔬 CROSS-API COMPARISON ANALYSIS")
        print("=" * 60)
        
        comparison = orchestrator.run_comparison_analysis(args.priority)
        
        print(f"Priority Terms Only: {comparison['use_priority_terms']}")
        print(f"APIs Analyzed: {comparison['summary']['total_apis']}")
        
        print(f"\nStrategy Distribution:")
        for strategy, count in comparison['summary']['strategy_distribution'].items():
            print(f"  • {strategy.title()}: {count} APIs")
        
        print(f"\nPer-API Analysis:")
        for api_info in comparison['apis_analyzed']:
            print(f"  {api_info['api_type'].upper()}:")
            print(f"    • Strategy: {api_info['recommended_strategy']}")
            print(f"    • Limit: {api_info['api_limit']} chars")
            print(f"    • Reasoning: {api_info['reasoning']}")
        
        print(f"\nRecommendation: {comparison['summary']['recommendation']}")
        return
    
    if args.api == 'all':
        # Run analysis for all APIs
        for api_type in orchestrator.apis.keys():
            print(f"\n📊 ANALYSIS FOR {api_type.upper()}")
            print("=" * 50)
            
            if args.analyze_only:
                analysis = orchestrator.analyze_search_strategy(api_type, args.priority)
                print(f"Recommended Strategy: {analysis['recommended_strategy']}")
                print(f"Reasoning: {analysis['reasoning']}")
                print(f"API Limit: {analysis['api_limit']} chars")
            else:
                summary = orchestrator.execute_smart_search(
                    api_type, args.priority, args.strategy, dry_run=not args.execute
                )
                print(f"Strategy Used: {summary['strategy_used']}")
                print(f"Queries Planned: {len(summary['queries_planned'])}")
                if summary.get('total_articles'):
                    print(f"Total Articles: {summary['total_articles']}")
    else:
        # Run for specific API
        print(f"\n📊 SMART SEARCH - {args.api.upper()}")
        print("=" * 50)
        
        if args.analyze_only:
            analysis = orchestrator.analyze_search_strategy(args.api, args.priority)
            print(f"Recommended Strategy: {analysis['recommended_strategy']}")
            print(f"Reasoning: {analysis['reasoning']}")
            print(f"API Limit: {analysis['api_limit']} chars")
            
            print(f"\nStrategy Details:")
            for strategy, stats in analysis['strategies'].items():
                print(f"  {strategy.title()}:")
                print(f"    • Feasible: {stats['feasible']}")
                print(f"    • API calls: {stats.get('api_calls_needed', 'N/A')}")
        else:
            summary = orchestrator.execute_smart_search(
                args.api, args.priority, args.strategy, dry_run=not args.execute
            )
            
            print(f"Strategy Used: {summary['strategy_used']}")
            print(f"Priority Terms: {summary['use_priority_terms']}")
            print(f"Queries Planned: {len(summary['queries_planned'])}")
            
            if summary.get('total_articles'):
                print(f"Total Articles Found: {summary['total_articles']}")
                print(f"Execution Time: {summary['execution_time']:.1f}s")
            
            if summary['errors']:
                print(f"Errors: {len(summary['errors'])}")
                for error in summary['errors']:
                    print(f"  • {error}")


if __name__ == "__main__":
    main()