#!/usr/bin/env python3
"""
Enhanced saturation search using the improved location terms database.
Tests the impact of comprehensive location terms on search results.
"""

import sys
import os
import json
import logging
from datetime import datetime

# Add src to path
# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.api.web_of_science_starter import WebOfScienceStarterAPI
from src.api.scopus_hybrid import ScopusHybridAPI
from src.utils.location_terms import (
    build_web_of_science_query, 
    build_scopus_query,
    get_location_terms_stats,
    ENHANCED_NECHAKO_LOCATION_TERMS
)
from config import WOS_API_KEY, SCOPUS_API_KEY

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/enhanced_search.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def run_enhanced_search(start_date="1930-01-01", end_date="2022-12-31", use_priority_terms=False):
    """
    Run enhanced saturation search with improved location terms.
    """
    
    print("="*80)
    print("ENHANCED NECHAKO WATERSHED SATURATION SEARCH")
    print("="*80)
    print(f"Search period: {start_date} to {end_date}")
    print(f"Location terms: {'Priority' if use_priority_terms else 'Comprehensive'}")
    
    # Display location terms statistics
    stats = get_location_terms_stats()
    print(f"Location terms database: {stats['total_unique']} unique terms ({stats['total_raw']} raw)")
    print(f"  - New physiography category: {stats['physiography_raw']} terms")
    print(f"  - Enhanced creeks: {stats['creeks_raw']} terms")
    print(f"  - Enhanced lakes: {stats['lakes_raw']} terms")
    print(f"  - Cross-category duplicates: {stats['duplicates_across_categories']} terms")
    print("="*80)
    
    results = {
        'search_metadata': {
            'search_date': datetime.now().isoformat(),
            'date_range': {'start': start_date, 'end': end_date},
            'search_type': 'Enhanced Nechako Watershed Saturation Search',
            'location_terms_used': 'priority' if use_priority_terms else 'comprehensive',
            'location_terms_count': stats['total_unique']
        },
        'database_results': {},
        'location_terms_stats': stats,
        'summary': {}
    }
    
    # Search Web of Science with enhanced terms
    print("\n" + "="*50)
    print("STEP 1: ENHANCED WEB OF SCIENCE SEARCH")
    print("="*50)
    
    wos_results = search_web_of_science_enhanced(start_date, end_date, use_priority_terms)
    results['database_results']['web_of_science'] = wos_results
    
    # Search Scopus with enhanced terms
    print("\n" + "="*50)
    print("STEP 2: ENHANCED SCOPUS SEARCH")
    print("="*50)
    
    scopus_results = search_scopus_enhanced(start_date, end_date, use_priority_terms)
    results['database_results']['scopus'] = scopus_results
    
    # Summary and comparison
    print("\n" + "="*50)
    print("STEP 3: ENHANCED RESULTS SUMMARY")
    print("="*50)
    
    wos_total = wos_results.get('total_results', 0)
    wos_retrieved = len(wos_results.get('records', []))
    scopus_total = scopus_results.get('total_results', 0)
    scopus_retrieved = len(scopus_results.get('records', []))
    
    print(f"Enhanced Web of Science: {wos_retrieved}/{wos_total} articles")
    print(f"Enhanced Scopus: {scopus_retrieved}/{scopus_total} articles")
    print(f"Combined potential: {wos_total + scopus_total} articles")
    
    results['summary'] = {
        'wos_total': wos_total,
        'wos_retrieved': wos_retrieved,
        'scopus_total': scopus_total,
        'scopus_retrieved': scopus_retrieved,
        'combined_potential': wos_total + scopus_total,
        'reference_target': 742,
        'coverage_ratio': (wos_total + scopus_total)/742
    }
    
    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    search_type = "priority" if use_priority_terms else "comprehensive"
    output_file = f"results/enhanced_search_{search_type}_{timestamp}.json"
    
    os.makedirs('results', exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n📄 Enhanced results saved to: {output_file}")
    
    return results

def search_web_of_science_enhanced(start_date, end_date, use_priority_terms):
    """Search Web of Science using enhanced location terms."""
    try:
        if not WOS_API_KEY:
            print("❌ No Web of Science API key found")
            return {'error': 'No API key', 'total_results': 0, 'records': []}
        
        print(f"🔍 Initializing Enhanced Web of Science search...")
        wos_api = WebOfScienceStarterAPI()
        
        if not wos_api.validate_api_key():
            print("❌ Web of Science API key validation failed")
            return {'error': 'Invalid API key', 'total_results': 0, 'records': []}
        
        print("✅ API key validated")
        
        # Build enhanced query
        enhanced_query = build_web_of_science_query(use_priority_terms, start_date, end_date)
        
        print(f"🔍 Enhanced query built ({len(enhanced_query)} characters)")
        print(f"📋 Query sample: {enhanced_query[:200]}...")
        
        # Execute search with enhanced query
        print("🔍 Executing enhanced search...")
        
        results = wos_api.search_documents(
            query=enhanced_query,
            max_results=1000,
            database="WOS"
        )
        
        total = results.get('total_results', 0)
        retrieved = len(results.get('records', []))
        
        print(f"✅ Enhanced Web of Science search completed:")
        print(f"   Total results available: {total}")
        print(f"   Results retrieved: {retrieved}")
        
        # Add enhanced query info to results
        results['enhanced_query'] = enhanced_query
        results['enhanced_query_length'] = len(enhanced_query)
        
        if results.get('records'):
            print(f"📄 Sample enhanced results:")
            for i, record in enumerate(results['records'][:3], 1):
                title = record.get('title', 'No title')[:50]
                year = record.get('year', 'Unknown')
                authors = record.get('authors', [])
                author_str = authors[0] if authors else 'Unknown'
                print(f"   {i}. {title}... ({year}) - {author_str}")
        
        return results
        
    except Exception as e:
        print(f"❌ Enhanced Web of Science search failed: {e}")
        logger.error(f"Enhanced WoS search failed: {e}", exc_info=True)
        return {'error': str(e), 'total_results': 0, 'records': []}

def search_scopus_enhanced(start_date, end_date, use_priority_terms):
    """Search Scopus using enhanced location terms."""
    try:
        if not SCOPUS_API_KEY:
            print("❌ No Scopus API key found")
            return {'error': 'No API key', 'total_results': 0, 'records': []}
        
        print(f"🔍 Initializing Enhanced Scopus search...")
        scopus_api = ScopusHybridAPI()
        
        if not scopus_api.validate_api_key():
            print("❌ Scopus API key validation failed")
            return {'error': 'Invalid API key', 'total_results': 0, 'records': []}
        
        print("✅ API key validated")
        
        # Convert dates for Scopus
        start_year = start_date.split('-')[0]
        end_year = end_date.split('-')[0]
        
        # Build enhanced query
        enhanced_query = build_scopus_query(use_priority_terms, start_year, end_year)
        
        print(f"🔍 Enhanced query built ({len(enhanced_query)} characters)")
        print(f"📋 Query sample: {enhanced_query[:200]}...")
        
        # Execute search with enhanced query
        print("🔍 Executing enhanced search...")
        
        results = scopus_api.search_documents(
            query=enhanced_query,
            max_results=1000
        )
        
        total = results.get('total_results', 0)
        retrieved = len(results.get('records', []))
        
        print(f"✅ Enhanced Scopus search completed:")
        print(f"   Total results available: {total}")
        print(f"   Results retrieved: {retrieved}")
        
        # Add enhanced query info to results
        results['enhanced_query'] = enhanced_query
        results['enhanced_query_length'] = len(enhanced_query)
        
        if results.get('records'):
            print(f"📄 Sample enhanced results:")
            for i, record in enumerate(results['records'][:3], 1):
                title = record.get('title', 'No title')[:50]
                year = record.get('year', 'Unknown')
                journal = record.get('journal', 'Unknown')[:30]
                print(f"   {i}. {title}... ({year}) - {journal}")
        
        return results
        
    except Exception as e:
        print(f"❌ Enhanced Scopus search failed: {e}")
        logger.error(f"Enhanced Scopus search failed: {e}", exc_info=True)
        return {'error': str(e), 'total_results': 0, 'records': []}

def compare_with_original(enhanced_results, original_results_file):
    """Compare enhanced results with original functional search."""
    try:
        with open(original_results_file, 'r') as f:
            original = json.load(f)
        
        print("\n" + "="*80)
        print("COMPARISON: ENHANCED vs ORIGINAL SEARCH")
        print("="*80)
        
        # Original results
        orig_wos = original['database_results']['web_of_science'].get('total_results', 0)
        orig_scopus = original['database_results']['scopus'].get('total_results', 0)
        orig_total = orig_wos + orig_scopus
        
        # Enhanced results  
        enh_wos = enhanced_results['summary']['wos_total']
        enh_scopus = enhanced_results['summary']['scopus_total']
        enh_total = enh_wos + enh_scopus
        
        print(f"ORIGINAL SEARCH (basic location terms):")
        print(f"  Web of Science: {orig_wos:,} articles")
        print(f"  Scopus: {orig_scopus:,} articles")
        print(f"  Combined: {orig_total:,} articles")
        
        print(f"\nENHANCED SEARCH ({enhanced_results['search_metadata']['location_terms_count']} location terms):")
        print(f"  Web of Science: {enh_wos:,} articles")
        print(f"  Scopus: {enh_scopus:,} articles") 
        print(f"  Combined: {enh_total:,} articles")
        
        print(f"\nIMPROVEMENT:")
        print(f"  Web of Science: {((enh_wos - orig_wos) / orig_wos * 100):+.1f}% change")
        print(f"  Scopus: {((enh_scopus - orig_scopus) / orig_scopus * 100):+.1f}% change")
        print(f"  Combined: {((enh_total - orig_total) / orig_total * 100):+.1f}% change")
        
        print(f"\nCOVERAGE vs REFERENCE (742 articles):")
        print(f"  Original: {orig_total/742:.2f}x coverage")
        print(f"  Enhanced: {enh_total/742:.2f}x coverage")
        
        return {
            'original_total': orig_total,
            'enhanced_total': enh_total,
            'improvement_pct': ((enh_total - orig_total) / orig_total * 100),
            'enhanced_coverage_ratio': enh_total/742
        }
        
    except Exception as e:
        print(f"⚠️  Could not compare with original results: {e}")
        return None

def main():
    """Main function to run enhanced search."""
    # Ensure directories exist
    os.makedirs('logs', exist_ok=True)
    os.makedirs('results', exist_ok=True)
    
    try:
        # Run both priority and comprehensive enhanced searches
        print("🚀 Running PRIORITY terms enhanced search...")
        priority_results = run_enhanced_search(
            start_date="1930-01-01",
            end_date="2022-12-31", 
            use_priority_terms=True
        )
        
        print(f"\n{'='*80}")
        print("🚀 Running COMPREHENSIVE terms enhanced search...")
        comprehensive_results = run_enhanced_search(
            start_date="1930-01-01",
            end_date="2022-12-31",
            use_priority_terms=False
        )
        
        # Compare with original results if available
        original_file = "results/functional_search_20250716_164537.json"
        if os.path.exists(original_file):
            print(f"\n{'='*80}")
            print("📊 COMPARING WITH ORIGINAL RESULTS")
            compare_with_original(comprehensive_results, original_file)
        
        print(f"\n{'='*80}")
        print("🎯 ENHANCED SEARCH SUMMARY")
        print("="*80)
        
        priority_total = priority_results['summary']['combined_potential']
        comprehensive_total = comprehensive_results['summary']['combined_potential']
        
        print(f"Priority terms search: {priority_total:,} potential articles")
        print(f"Comprehensive terms search: {comprehensive_total:,} potential articles")
        print(f"Reference target: 742 articles")
        print(f"Best coverage ratio: {comprehensive_total/742:.2f}x")
        
        print(f"\n✅ Enhanced location terms database successfully tested!")
        print(f"📈 Found {comprehensive_total:,} potential articles with comprehensive terms")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Enhanced search failed: {e}")
        logger.error(f"Enhanced search failed: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)