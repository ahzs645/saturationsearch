#!/usr/bin/env python3
"""
Test script for the new Web of Science Starter API integration.
"""

import sys
import os
# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.api.web_of_science_starter import WebOfScienceStarterAPI
from config import WOS_API_KEY

def test_wos_starter_api():
    """Test the Web of Science Starter API integration."""
    
    print("=== Web of Science Starter API Test ===")
    print(f"API Key: {WOS_API_KEY[:8]}..." if WOS_API_KEY else "No API key found")
    
    if not WOS_API_KEY or WOS_API_KEY == 'your_web_of_science_api_key_here':
        print("❌ No valid Web of Science API key found")
        print("Please update your .env file with a valid WOS_API_KEY")
        return False
    
    try:
        # Test 1: Initialize API client
        print("\n1. Testing API client initialization...")
        wos_api = WebOfScienceStarterAPI()
        print("   ✅ API client initialized successfully")
        
        # Test 2: Validate API key
        print("\n2. Testing API key validation...")
        if wos_api.validate_api_key():
            print("   ✅ API key validation passed")
        else:
            print("   ❌ API key validation failed")
            return False
        
        # Test 3: Build search query
        print("\n3. Testing query building...")
        
        # Test priority terms query
        priority_query = wos_api.build_nechako_query(
            use_priority_terms=True,
            date_start="2020-01-01",
            date_end="2023-12-31"
        )
        print(f"   ✅ Priority query built: {priority_query[:100]}...")
        
        # Test comprehensive terms query  
        comprehensive_query = wos_api.build_nechako_query(
            use_priority_terms=False,
            date_start="2020-01-01", 
            date_end="2023-12-31"
        )
        print(f"   ✅ Comprehensive query built: {comprehensive_query[:100]}...")
        
        # Test 4: Execute a small search
        print("\n4. Testing document search...")
        
        # Test with a simple query first
        test_query = 'TS="Nechako" AND PY=(2020-2023)'
        print(f"   Executing test query: {test_query}")
        
        results = wos_api.search_documents(
            query=test_query,
            max_results=5,  # Small test
            database="WOS"
        )
        
        print(f"   ✅ Search completed:")
        print(f"      - Total results available: {results.get('total_results', 0)}")
        print(f"      - Results retrieved: {len(results.get('records', []))}")
        print(f"      - Pages retrieved: {results['metadata']['pages_retrieved']}")
        
        # Show sample results
        if results.get('records'):
            print(f"   📄 Sample results:")
            for i, record in enumerate(results['records'][:3], 1):
                title = record.get('title', 'No title')[:60]
                year = record.get('year', 'Unknown')
                journal = record.get('journal', 'Unknown journal')[:40]
                print(f"      {i}. {title}... ({year}) - {journal}")
        else:
            print("   📄 No results found for test query")
        
        # Test 5: Full Nechako saturation search (small sample)
        print("\n5. Testing Nechako saturation search...")
        
        nechako_results = wos_api.nechako_saturation_search(
            date_start="2022-01-01",
            date_end="2023-12-31", 
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
                authors = record.get('authors', [])
                author_str = ', '.join(authors[:2]) if authors else 'Unknown authors'
                if len(authors) > 2:
                    author_str += ' et al.'
                print(f"      {i}. {title}... ({year})")
                print(f"         Authors: {author_str}")
                print(f"         DOI: {record.get('doi', 'No DOI')}")
                print(f"         Times cited: {record.get('times_cited', 0)}")
                print()
        
        print("🎉 All tests completed successfully!")
        print("\n📋 Summary:")
        print(f"   - ✅ API client: Working")
        print(f"   - ✅ Authentication: Valid")
        print(f"   - ✅ Query building: Functional") 
        print(f"   - ✅ Document search: Working")
        print(f"   - ✅ Nechako search: Functional")
        
        print("\n🚀 The new Web of Science Starter API is ready for use!")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_api_features():
    """Test specific API features and capabilities."""
    
    print("\n=== Testing API Features ===")
    
    try:
        wos_api = WebOfScienceStarterAPI()
        
        # Test DOI lookup
        print("\n1. Testing DOI lookup...")
        # Use a known DOI for testing (you can replace with a real one)
        test_doi = "10.1038/nature12373"  # Example DOI
        
        doi_result = wos_api.get_document_by_doi(test_doi)
        if doi_result:
            print(f"   ✅ Found document by DOI: {doi_result.get('title', 'No title')[:50]}...")
        else:
            print(f"   ℹ️  No document found for DOI: {test_doi}")
        
        # Test different databases
        print("\n2. Testing different databases...")
        databases = ["WOS", "BIOABS", "BCI"]
        
        for db in databases:
            try:
                result = wos_api.search_documents(
                    query='TS="water quality" AND PY=2023',
                    max_results=1,
                    database=db
                )
                total = result.get('total_results', 0)
                print(f"   ✅ {db}: {total} results available")
            except Exception as e:
                print(f"   ⚠️  {db}: {str(e)}")
        
        print("\n✅ Feature testing completed!")
        
    except Exception as e:
        print(f"❌ Feature testing failed: {e}")

if __name__ == "__main__":
    print("Testing Web of Science Starter API integration...")
    
    success = test_wos_starter_api()
    
    if success:
        test_api_features()
        print("\n🎉 Web of Science Starter API is fully functional!")
        print("\nNext steps:")
        print("1. Update the main saturation search to use the new API")
        print("2. Test with your other API keys (Scopus)")
        print("3. Run a full saturation search")
    else:
        print("\n🔧 Please fix the issues above before proceeding.")
        sys.exit(1)