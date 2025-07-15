"""
Scopus API integration for automated literature searches.
Provides alternative/supplementary search capability to Web of Science.
"""

import requests
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import json

from ..utils.location_terms import build_location_query, build_priority_location_query
from config import SCOPUS_API_KEY, API_RATE_LIMIT_DELAY, DEFAULT_LANGUAGE

logger = logging.getLogger(__name__)

class ScopusAPI:
    """
    Scopus API client for automated literature searches.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Scopus API client.
        
        Args:
            api_key (str, optional): Scopus API key. If None, uses config.SCOPUS_API_KEY
        """
        self.api_key = api_key or SCOPUS_API_KEY
        if not self.api_key:
            raise ValueError("Scopus API key is required")
            
        self.base_url = "https://api.elsevier.com/content"
        self.session = requests.Session()
        self.session.headers.update({
            "X-ELS-APIKey": self.api_key,
            "Accept": "application/json"
        })
        
    def search(self, 
               query: str,
               date_start: str = "1930",
               date_end: Optional[str] = None,
               max_results: int = 1000) -> Dict:
        """
        Execute a literature search using Scopus API.
        
        Args:
            query (str): Search query string
            date_start (str): Start year (YYYY format)
            date_end (str): End year (YYYY format, defaults to current year)
            max_results (int): Maximum number of results to retrieve
            
        Returns:
            Dict: Search results with metadata
        """
        if date_end is None:
            date_end = str(datetime.now().year)
            
        # Build Scopus-specific query with geographic filter
        geographic_terms = "(AFFILCOUNTRY(Canada) OR AFFILCOUNTRY(\"British Columbia\"))"
        full_query = f"({query}) AND {geographic_terms} AND PUBYEAR > {date_start} AND PUBYEAR < {int(date_end) + 1}"
        
        logger.info(f"Executing Scopus search: {full_query[:100]}...")
        logger.info(f"Date range: {date_start} to {date_end}")
        
        try:
            # Execute paginated search
            results = self._execute_paginated_search(full_query, max_results)
            
            logger.info(f"Retrieved {len(results.get('entries', []))} articles from Scopus")
            
            return {
                'source': 'Scopus',
                'query': full_query,
                'date_range': (date_start, date_end),
                'total_results': results.get('opensearch:totalResults', 0),
                'retrieved_results': len(results.get('entries', [])),
                'records': results.get('entries', []),
                'search_metadata': {
                    'search_time': datetime.now().isoformat(),
                    'api_version': 'v1',
                    'database': 'Scopus'
                }
            }
            
        except Exception as e:
            logger.error(f"Scopus search failed: {str(e)}")
            raise
    
    def nechako_saturation_search(self,
                                 date_start: str = "1930",
                                 date_end: Optional[str] = None,
                                 use_priority_terms: bool = False) -> Dict:
        """
        Execute Nechako Watershed search using Scopus database.
        
        Args:
            date_start (str): Start year for search
            date_end (str): End year for search  
            use_priority_terms (bool): If True, use only major water bodies/communities
            
        Returns:
            Dict: Search results
        """
        logger.info("Starting Nechako Watershed search in Scopus")
        
        # Build location query
        if use_priority_terms:
            location_query = self._convert_to_scopus_query(build_priority_location_query())
            logger.info("Using priority location terms for Scopus search")
        else:
            location_query = self._convert_to_scopus_query(build_location_query())
            logger.info("Using all location terms for Scopus search")
        
        # Execute the search
        results = self.search(
            query=location_query,
            date_start=date_start,
            date_end=date_end,
            max_results=1000
        )
        
        # Add methodology metadata
        results['methodology'] = {
            'search_type': 'Nechako Watershed Saturation Search',
            'location_terms_used': 'priority' if use_priority_terms else 'comprehensive',
            'database': 'Scopus',
            'complementary_to_wos': True
        }
        
        return results
    
    def _convert_to_scopus_query(self, wos_query: str) -> str:
        """
        Convert Web of Science query format to Scopus format.
        
        Args:
            wos_query (str): Query in WoS format
            
        Returns:
            str: Query in Scopus format
        """
        # Scopus uses different field codes
        # For now, search in title, abstract, and keywords
        scopus_query = wos_query.replace(' OR ', ' OR ')
        
        # Wrap the entire query to search in title, abstract, and keywords
        scopus_query = f"TITLE-ABS-KEY({scopus_query})"
        
        return scopus_query
    
    def _execute_paginated_search(self, query: str, max_results: int) -> Dict:
        """
        Execute a paginated search to retrieve all results.
        
        Args:
            query (str): Search query
            max_results (int): Maximum number of results to retrieve
            
        Returns:
            Dict: Combined results from all pages
        """
        all_entries = []
        start_index = 0
        count_per_request = min(25, max_results)  # Scopus limit is 25 per request
        
        while len(all_entries) < max_results:
            params = {
                'query': query,
                'start': start_index,
                'count': min(count_per_request, max_results - len(all_entries)),
                'view': 'COMPLETE'  # Get full details
            }
            
            response = self._make_request("/search/scopus", params)
            
            if not response or 'search-results' not in response:
                break
                
            search_results = response['search-results']
            entries = search_results.get('entry', [])
            
            if not entries:
                break
                
            all_entries.extend(entries)
            
            # Check if we've retrieved all available results
            total_results = int(search_results.get('opensearch:totalResults', 0))
            
            if len(all_entries) >= total_results:
                break
                
            start_index += len(entries)
            
            # Rate limiting
            time.sleep(API_RATE_LIMIT_DELAY)
        
        return {
            'opensearch:totalResults': total_results if 'total_results' in locals() else len(all_entries),
            'entries': all_entries
        }
    
    def _make_request(self, endpoint: str, params: Dict) -> Optional[Dict]:
        """
        Make a request to the Scopus API with error handling.
        
        Args:
            endpoint (str): API endpoint
            params (Dict): Request parameters
            
        Returns:
            Optional[Dict]: Response data or None if failed
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Scopus API request failed: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response text: {e.response.text}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Scopus API response: {str(e)}")
            return None
    
    def validate_api_key(self) -> bool:
        """
        Validate that the API key is working.
        
        Returns:
            bool: True if API key is valid
        """
        try:
            params = {
                'query': 'TITLE-ABS-KEY(water)',
                'count': 1
            }
            
            response = self._make_request("/search/scopus", params)
            return response is not None
            
        except Exception as e:
            logger.error(f"Scopus API key validation failed: {str(e)}")
            return False
    
    def get_usage_stats(self) -> Dict:
        """
        Get API usage statistics.
        
        Returns:
            Dict: Usage statistics
        """
        return {
            'api_status': 'connected' if self.validate_api_key() else 'disconnected',
            'base_url': self.base_url,
            'rate_limit_delay': API_RATE_LIMIT_DELAY
        }


def convert_scopus_record_to_standard_format(record: Dict) -> Dict:
    """
    Convert a Scopus record to standardized format.
    
    Args:
        record (Dict): Raw Scopus record
        
    Returns:
        Dict: Standardized article record
    """
    try:
        # Extract basic metadata
        eid = record.get('eid', '')
        
        # Extract title
        title = record.get('dc:title', '')
        
        # Extract authors
        authors = []
        if 'author' in record:
            author_list = record['author']
            if isinstance(author_list, list):
                authors = [author.get('authname', '') for author in author_list]
            else:
                authors = [author_list.get('authname', '')]
        
        # Extract publication year
        year = record.get('prism:coverDate', '')
        if year:
            year = year.split('-')[0]  # Extract year from date
        
        # Extract journal
        journal = record.get('prism:publicationName', '')
        
        # Extract abstract
        abstract = record.get('dc:description', '')
        
        # Extract DOI
        doi = record.get('prism:doi', '')
        
        # Extract other identifiers
        pmid = record.get('pubmed-id', '')
        
        return {
            'uid': eid,
            'title': title,
            'authors': authors,
            'year': year,
            'journal': journal,
            'abstract': abstract,
            'doi': doi,
            'pmid': pmid,
            'source': 'Scopus',
            'raw_record': record
        }
        
    except Exception as e:
        logger.error(f"Failed to convert Scopus record: {str(e)}")
        return {
            'uid': record.get('eid', ''),
            'title': '',
            'authors': [],
            'year': '',
            'journal': '',
            'abstract': '',
            'doi': '',
            'pmid': '',
            'source': 'Scopus',
            'conversion_error': str(e),
            'raw_record': record
        }