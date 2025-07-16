"""
Hybrid Scopus API integration using direct API calls for search functionality.
This approach works with limited API access levels while still providing comprehensive results.
"""

import os
import time
import logging
import requests
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Import from parent directory
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from config import SCOPUS_API_KEY, API_RATE_LIMIT_DELAY, GEOGRAPHIC_FILTER, DEFAULT_LANGUAGE

logger = logging.getLogger(__name__)

class ScopusHybridAPI:
    """
    Hybrid Scopus API client using direct API calls for search functionality.
    
    This approach works with limited API access levels and provides comprehensive
    metadata for the Nechako Watershed saturation search.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Scopus hybrid API client.
        
        Args:
            api_key (str, optional): Scopus API key. If None, uses config.SCOPUS_API_KEY
        """
        self.api_key = api_key or SCOPUS_API_KEY
        if not self.api_key:
            raise ValueError("Scopus API key is required")
        
        self.base_url = "https://api.elsevier.com"
        self.session = requests.Session()
        self.session.headers.update({
            "X-ELS-APIKey": self.api_key,
            "Accept": "application/json"
        })
        
        logger.info("Scopus hybrid API client initialized")
    
    def validate_api_key(self) -> bool:
        """
        Validate the API key by making a simple test request.
        
        Returns:
            bool: True if API key is valid, False otherwise
        """
        try:
            # Test with abstract retrieval (usually works with basic access)
            url = f"{self.base_url}/content/abstract/doi/10.1016/j.softx.2019.100263"
            
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                logger.info("API key validation successful")
                return True
            else:
                logger.error(f"API key validation failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"API key validation error: {e}")
            return False
    
    def build_nechako_query(self,
                           use_priority_terms: bool = False,
                           date_start: str = "1930",
                           date_end: Optional[str] = None) -> str:
        """
        Build a Scopus query for Nechako Watershed research.
        
        Args:
            use_priority_terms (bool): Use priority location terms only
            date_start (str): Start year (YYYY)
            date_end (str): End year (YYYY, defaults to current year)
            
        Returns:
            str: Scopus query string
        """
        if date_end is None:
            date_end = str(datetime.now().year)
        
        # Ensure we have years only
        if '-' in date_start:
            date_start = date_start.split('-')[0]
        if '-' in date_end:
            date_end = date_end.split('-')[0]
        
        # Location terms for Nechako Watershed
        if use_priority_terms:
            location_terms = [
                "Nechako",
                "Fraser River", 
                "British Columbia",
                "Vanderhoof",
                "Prince George"
            ]
        else:
            # More comprehensive terms
            location_terms = [
                "Nechako",
                "Fraser River",
                "British Columbia",
                "Vanderhoof", 
                "Prince George",
                "Blackwater River",
                "Stuart River",
                "Nautley River",
                "Endako River",
                "Central Interior",
                "BC Interior", 
                "Carrier Sekani",
                "Omineca",
                "Bulkley Valley",
                "Fort St. James",
                "Burns Lake",
                "Fraser Lake"
            ]
        
        # Build location query using TITLE-ABS-KEY (searches title, abstract, and keywords)
        location_parts = []
        for term in location_terms:
            location_parts.append(f'TITLE-ABS-KEY("{term}")')
        location_query = " OR ".join(location_parts)
        
        # Core research themes related to watersheds
        theme_terms = [
            "watershed",
            "hydrology",
            "water quality",
            "aquatic ecosystem", 
            "fisheries",
            "salmon",
            "environmental assessment",
            "water resources",
            "river ecology",
            "biodiversity",
            "conservation",
            "climate change",
            "forestry",
            "land use",
            "First Nations",
            "indigenous"
        ]
        
        theme_parts = []
        for term in theme_terms:
            theme_parts.append(f'TITLE-ABS-KEY("{term}")')
        theme_query = " OR ".join(theme_parts)
        
        # Combine queries
        query_parts = [
            f"({location_query})",
            f"({theme_query})",
            f"PUBYEAR > {int(date_start)-1} AND PUBYEAR < {int(date_end)+1}"
        ]
        
        # Add language filter if specified
        if DEFAULT_LANGUAGE and DEFAULT_LANGUAGE.lower() == "english":
            query_parts.append('LANGUAGE(english)')
        
        # Add document type filters (exclude non-research content)
        query_parts.append('DOCTYPE(ar OR re OR cp OR ch)')  # Articles, reviews, conference papers, book chapters
        
        query = " AND ".join(query_parts)
        
        logger.info(f"Built Scopus query: {query[:200]}...")
        return query
    
    def search_documents(self,
                        query: str,
                        max_results: int = 1000,
                        start_index: int = 0) -> Dict:
        """
        Search for documents using Scopus API via direct HTTP calls.
        
        Args:
            query (str): Scopus query string
            max_results (int): Maximum number of results to retrieve
            start_index (int): Starting index for pagination
            
        Returns:
            Dict: Search results with metadata
        """
        logger.info(f"Executing Scopus search")
        logger.info(f"Query: {query}")
        
        search_metadata = {
            'query': query,
            'search_time': datetime.now().isoformat(),
            'total_results': 0,
            'retrieved_results': 0
        }
        
        all_documents = []
        current_start = start_index
        count_per_request = min(25, max_results)  # Scopus API limit is 25 per request
        
        try:
            while len(all_documents) < max_results:
                # Build request parameters
                params = {
                    'query': query,
                    'start': current_start,
                    'count': min(count_per_request, max_results - len(all_documents)),
                    'sort': 'relevancy',
                    'field': 'dc:identifier,dc:title,dc:creator,prism:publicationName,prism:coverDate,prism:doi,citedby-count,prism:aggregationType,authkeywords,affilname,prism:pageRange,prism:volume,prism:issueIdentifier,eid,subtype,subtypeDescription,prism:issn'
                }
                
                url = f"{self.base_url}/content/search/scopus"
                
                logger.info(f"Fetching results {current_start} to {current_start + params['count']}")
                
                response = self.session.get(url, params=params, timeout=30)
                
                if response.status_code != 200:
                    logger.error(f"Search request failed: {response.status_code}")
                    logger.error(f"Response: {response.text}")
                    break
                
                data = response.json()
                search_results = data.get('search-results', {})
                
                # Update total results on first request
                if current_start == start_index:
                    total_results = int(search_results.get('opensearch:totalResults', 0))
                    search_metadata['total_results'] = total_results
                    logger.info(f"Total results available: {total_results}")
                
                # Process entries
                entries = search_results.get('entry', [])
                if not entries:
                    logger.info("No more results available")
                    break
                
                # Convert entries to standard format
                for entry in entries:
                    if len(all_documents) >= max_results:
                        break
                    
                    doc = self._convert_entry_to_standard_format(entry)
                    all_documents.append(doc)
                
                # Check if we got fewer results than requested (last page)
                if len(entries) < params['count']:
                    logger.info("Reached last page of results")
                    break
                
                current_start += len(entries)
                
                # Rate limiting
                if API_RATE_LIMIT_DELAY > 0:
                    time.sleep(API_RATE_LIMIT_DELAY)
            
            search_metadata['retrieved_results'] = len(all_documents)
            logger.info(f"Retrieved {len(all_documents)} documents")
            
        except Exception as e:
            logger.error(f"Search execution failed: {e}")
            search_metadata['error'] = str(e)
        
        return {
            'records': all_documents,
            'metadata': search_metadata,
            'total_results': search_metadata['total_results'],
            'retrieved_results': search_metadata['retrieved_results']
        }
    
    def nechako_saturation_search(self,
                                 date_start: str = "1930",
                                 date_end: Optional[str] = None,
                                 use_priority_terms: bool = False,
                                 max_results: int = 1000) -> Dict:
        """
        Execute the Nechako Watershed saturation search on Scopus.
        
        Args:
            date_start (str): Start year (YYYY or YYYY-MM-DD)
            date_end (str): End year (YYYY or YYYY-MM-DD)
            use_priority_terms (bool): Use priority location terms only
            max_results (int): Maximum results to retrieve
            
        Returns:
            Dict: Search results
        """
        logger.info("Starting Nechako Watershed saturation search on Scopus")
        logger.info(f"Date range: {date_start} to {date_end or 'present'}")
        logger.info(f"Using {'priority' if use_priority_terms else 'comprehensive'} location terms")
        
        # Build the search query
        query = self.build_nechako_query(
            use_priority_terms=use_priority_terms,
            date_start=date_start,
            date_end=date_end
        )
        
        # Execute the search
        results = self.search_documents(
            query=query,
            max_results=max_results
        )
        
        # Add search parameters to metadata
        results['metadata'].update({
            'search_type': 'Nechako Watershed Saturation Search (Scopus Hybrid)',
            'date_start': date_start,
            'date_end': date_end,
            'use_priority_terms': use_priority_terms,
            'max_results': max_results,
            'database': 'Scopus'
        })
        
        return results
    
    def _convert_entry_to_standard_format(self, entry: Dict) -> Dict:
        """
        Convert Scopus API entry to standard format.
        
        Args:
            entry (Dict): Entry from Scopus search results
            
        Returns:
            Dict: Standardized document format
        """
        # Extract authors
        authors = []
        if 'dc:creator' in entry:
            # dc:creator can be a string or list
            creator = entry['dc:creator']
            if isinstance(creator, list):
                authors = creator
            elif isinstance(creator, str):
                # Split by semicolon if multiple authors in one string
                authors = [author.strip() for author in creator.split(';')]
        
        # Extract publication year
        year = None
        if 'prism:coverDate' in entry:
            try:
                year = int(entry['prism:coverDate'].split('-')[0])
            except (ValueError, AttributeError):
                pass
        
        # Extract keywords
        keywords = []
        if 'authkeywords' in entry and entry['authkeywords']:
            # Keywords are semicolon-separated
            keywords = [kw.strip() for kw in entry['authkeywords'].split(';') if kw.strip()]
        
        # Extract pages
        pages = entry.get('prism:pageRange', '') or ''
        
        return {
            'title': entry.get('dc:title', '') or '',
            'authors': authors,
            'abstract': '',  # Not available in search results
            'year': year,
            'journal': entry.get('prism:publicationName', '') or '',
            'volume': entry.get('prism:volume', '') or '',
            'issue': entry.get('prism:issueIdentifier', '') or '',
            'pages': pages,
            'doi': entry.get('prism:doi', '') or '',
            'url': f"https://www.scopus.com/record/display.uri?eid={entry.get('eid', '')}" if entry.get('eid') else '',
            'keywords': keywords,
            'document_type': entry.get('prism:aggregationType', '') or '',
            'cited_by_count': int(entry.get('citedby-count', 0) or 0),
            'eid': entry.get('eid', '') or '',
            'scopus_id': entry.get('dc:identifier', '').replace('SCOPUS_ID:', '') if entry.get('dc:identifier') else '',
            'source': 'Scopus (Hybrid API)',
            'retrieved_date': datetime.now().isoformat(),
            'affiliation': entry.get('affilname', '') or '',
            'author_keywords': keywords,
            'issn': entry.get('prism:issn', '') or '',
            'subtype': entry.get('subtype', '') or '',
            'subtype_description': entry.get('subtypeDescription', '') or ''
        }
    
    def get_document_by_doi(self, doi: str) -> Optional[Dict]:
        """
        Retrieve a specific document by DOI.
        
        Args:
            doi (str): Document DOI
            
        Returns:
            Optional[Dict]: Document data if found, None otherwise
        """
        try:
            url = f"{self.base_url}/content/abstract/doi/{doi}"
            
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                # Extract from abstract retrieval response
                abs_response = data.get('abstracts-retrieval-response', {})
                coredata = abs_response.get('coredata', {})
                
                return {
                    'title': coredata.get('dc:title', ''),
                    'doi': doi,
                    'abstract': abs_response.get('abstract', {}).get('ce:para', ''),
                    'journal': coredata.get('prism:publicationName', ''),
                    'year': int(coredata.get('prism:coverDisplayDate', '').split('-')[0]) if coredata.get('prism:coverDisplayDate') else None,
                    'cited_by_count': int(coredata.get('citedby-count', 0)),
                    'source': 'Scopus (Direct API)'
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving document by DOI {doi}: {e}")
            return None


def convert_scopus_hybrid_record_to_standard_format(record: Dict) -> Dict:
    """
    Convert a Scopus hybrid record to standard format.
    This is a helper function for compatibility with existing code.
    
    Args:
        record (Dict): Record from hybrid API
        
    Returns:
        Dict: Standardized record format
    """
    # This function assumes the record is already converted
    # But provides additional standardization if needed
    
    standardized = record.copy()
    
    # Ensure required fields exist
    required_fields = ['title', 'authors', 'abstract', 'year', 'journal', 'doi', 'source']
    for field in required_fields:
        if field not in standardized:
            standardized[field] = '' if field != 'authors' else []
    
    # Ensure year is integer or None
    if standardized.get('year') and isinstance(standardized['year'], str):
        try:
            standardized['year'] = int(standardized['year'])
        except ValueError:
            standardized['year'] = None
    
    # Standardize source
    if 'source' not in standardized or not standardized['source']:
        standardized['source'] = 'Scopus'
    
    return standardized