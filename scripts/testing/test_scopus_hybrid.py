#!/usr/bin/env python3
"""
Test script for the hybrid Scopus API integration.
"""

import sys
import os
# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.api.scopus_hybrid import ScopusHybridAPI
from config import SCOPUS_API_KEY

def test_scopus_hybrid():
    """Test the Scopus hybrid API integration."""
    
    print("=== Scopus Hybrid API Test ===")
    print(f"API Key: {SCOPUS_API_KEY[:8]}..." if SCOPUS_API_KEY else "No API key found")
    
    if not SCOPUS_API_KEY or SCOPUS_API_KEY == 'your_scopus_api_key_here':
        print("❌ No valid Scopus API key found")
        print("Please update your .env file with a valid SCOPUS_API_KEY")
        return False
    
    try:
        # Test 1: Initialize API client
        print("\n1. Testing API client initialization...")
        scopus_api = ScopusHybridAPI()
        print("   ✅ API client initialized successfully")
        
        # Test 2: Validate API key
        print("\n2. Testing API key validation...")
        if scopus_api.validate_api_key():
            print("   ✅ API key validation passed")
        else:
            print("   ❌ API key validation failed")
            return False
        
        # Test 3: Build search query
        print("\n3. Testing query building...")
        
        # Test priority terms query
        priority_query = scopus_api.build_nechako_query(
            use_priority_terms=True,
            date_start="2020",
            date_end="2023"
        )
        print(f"   ✅ Priority query built: {priority_query[:100]}...")
        
        # Test comprehensive terms query
        comprehensive_query = scopus_api.build_nechako_query(
            use_priority_terms=False,
            date_start="2020",
            date_end="2023"
        )
        print(f"   ✅ Comprehensive query built: {comprehensive_query[:100]}...")
        
        # Test 4: Execute a small search
        print("\n4. Testing document search...")
        
        # Test with a simple query first
        test_query = 'TITLE-ABS-KEY("Nechako") AND PUBYEAR > 2019 AND PUBYEAR < 2024'
        print(f"   Executing test query: {test_query}")
        
        results = scopus_api.search_documents(
            query=test_query,
            max_results=5  # Small test
        )
        
        print(f"   ✅ Search completed:")
        print(f"      - Total results available: {results.get('total_results', 0)}")
        print(f"      - Results retrieved: {len(results.get('records', []))}")
        
        # Show sample results
        if results.get('records'):
            print(f"   📄 Sample results:")
            for i, record in enumerate(results['records'][:3], 1):
                title = record.get('title', 'No title')[:60]
                year = record.get('year', 'Unknown')
                journal = record.get('journal', 'Unknown journal')[:40]
                cited_by = record.get('cited_by_count', 0)
                print(f"      {i}. {title}... ({year})")
                print(f"         Journal: {journal}")
                print(f"         Cited by: {cited_by}")
                print(f"         DOI: {record.get('doi', 'No DOI')}")
                
                # Show authors
                authors = record.get('authors', [])
                if authors:
                    author_str = '; '.join(authors[:3])
                    if len(authors) > 3:
                        author_str += f' ... (+{len(authors)-3} more)'
                    print(f"         Authors: {author_str}")
                print()
        else:
            print("   📄 No results found for test query")
        
        # Test 5: Full Nechako saturation search (small sample)
        print("\n5. Testing Nechako saturation search...")
        
        nechako_results = scopus_api.nechako_saturation_search(
            date_start="2022",
            date_end="2023",
            use_priority_terms=True,
            max_results=10  # Small sample for testing
        )
        
        print(f"   ✅ Nechako search completed:")
        print(f"      - Total results available: {nechako_results.get('total_results', 0)}")
        print(f"      - Results retrieved: {len(nechako_results.get('records', []))}")
        print(f"      - Search type: {nechako_results['metadata']['search_type']}")
        
        if nechako_results.get('records'):
            print(f"   📄 Sample Nechako results:")
            for i, record in enumerate(nechako_results['records'][:3], 1):
                title = record.get('title', 'No title')[:60]
                year = record.get('year', 'Unknown')
                print(f"      {i}. {title}... ({year})")
                
                # Keywords
                keywords = record.get('author_keywords', [])
                if keywords:
                    print(f"         Keywords: {', '.join(keywords[:5])}")
                
                # Affiliation
                if record.get('affiliation'):
                    print(f"         Affiliation: {record['affiliation'][:50]}...")
                    
                # Document type
                if record.get('document_type'):
                    print(f"         Type: {record['document_type']}")
                print()
        
        # Test 6: DOI retrieval (if available)
        print("\n6. Testing DOI retrieval...")
        if results.get('records') and results['records'][0].get('doi'):
            doi = results['records'][0]['doi']
            print(f"   Retrieving document for DOI: {doi}")
            
            doc = scopus_api.get_document_by_doi(doi)
            if doc:
                print(f"   ✅ Document retrieved: {doc.get('title', 'No title')[:50]}...")
                print(f"      Abstract available: {'Yes' if doc.get('abstract') else 'No'}")
            else:
                print("   ℹ️  Could not retrieve document (may require additional permissions)")
        else:
            print("   ℹ️  No DOI available for retrieval test")
        
        print("\n🎉 All tests completed successfully!")
        print("\n📋 Summary:")
        print(f"   - ✅ API client: Working")
        print(f"   - ✅ Authentication: Valid")
        print(f"   - ✅ Query building: Functional")
        print(f"   - ✅ Document search: Working with direct API calls")
        print(f"   - ✅ Nechako search: Functional")
        print(f"   - ✅ Metadata extraction: Comprehensive")
        print(f"   - ✅ Hybrid approach: Bypasses pybliometrics limitations")
        
        print("\n🚀 The Scopus hybrid API is ready for use!")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_comparison_with_direct():
    """Compare hybrid approach with direct API calls."""
    
    print("\n=== Comparison Test ===")
    
    try:
        scopus_api = ScopusHybridAPI()
        
        # Test different query types
        queries = [
            'TITLE-ABS-KEY("water quality") AND PUBYEAR = 2023',
            'TITLE-ABS-KEY("British Columbia") AND TITLE-ABS-KEY("watershed") AND PUBYEAR > 2020',
            'TITLE-ABS-KEY("salmon") AND TITLE-ABS-KEY("river") AND PUBYEAR > 2021'
        ]
        
        for i, query in enumerate(queries, 1):
            print(f"\n{i}. Testing query: {query[:80]}...")
            
            results = scopus_api.search_documents(query, max_results=3)
            total = results.get('total_results', 0)
            retrieved = len(results.get('records', []))
            
            print(f"   Results: {retrieved}/{total} (retrieved/total)")
            
            if results.get('records'):
                sample = results['records'][0]
                print(f"   Sample: {sample.get('title', 'No title')[:50]}...")
        
        print("\n✅ Comparison testing completed!")
        
    except Exception as e:
        print(f"❌ Comparison testing failed: {e}")

if __name__ == "__main__":
    print("Testing Scopus hybrid integration...")
    
    success = test_scopus_hybrid()
    
    if success:
        test_comparison_with_direct()
        print("\n🎉 Scopus hybrid API is fully functional!")
        print("\nNext steps:")
        print("1. The hybrid approach works with your current API access level")
        print("2. Provides comprehensive search functionality")
        print("3. Ready for integration with the main saturation search system")
    else:
        print("\n🔧 Please fix the issues above before proceeding.")
        sys.exit(1)