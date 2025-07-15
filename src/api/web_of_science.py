"""
Web of Science API integration for automated literature searches.
Replicates the exact methodology used in the original saturation search.
"""

import requests
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json

from ..utils.location_terms import build_location_query, build_priority_location_query
from config import WOS_API_KEY, API_RATE_LIMIT_DELAY, GEOGRAPHIC_FILTER, DEFAULT_LANGUAGE

logger = logging.getLogger(__name__)

class WebOfScienceAPI:
    """
    Web of Science API client for automated literature searches.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Web of Science API client.
        
        Args:
            api_key (str, optional): WoS API key. If None, uses config.WOS_API_KEY
        """
        self.api_key = api_key or WOS_API_KEY
        if not self.api_key:
            raise ValueError("Web of Science API key is required")
            
        self.base_url = "https://api.clarivate.com/apis/wos-starter/v1"
        self.session = requests.Session()
        self.session.headers.update({
            "X-ApiKey": self.api_key,
            "Content-Type": "application/json"
        })
        
    def search(self, 
               query: str,
               date_start: str = "1930-01-01",
               date_end: Optional[str] = None,
               max_results: int = 1000,
               language: str = DEFAULT_LANGUAGE) -> Dict:
        """
        Execute a literature search using Web of Science API.
        
        Args:
            query (str): Search query string
            date_start (str): Start date in YYYY-MM-DD format
            date_end (str): End date in YYYY-MM-DD format (defaults to today)
            max_results (int): Maximum number of results to retrieve
            language (str): Language filter
            
        Returns:
            Dict: Search results with metadata
        """
        if date_end is None:
            date_end = datetime.now().strftime("%Y-%m-%d")
            
        # Build the complete query
        full_query = f"({query}) AND {GEOGRAPHIC_FILTER}"
        
        logger.info(f"Executing WoS search: {full_query[:100]}...")
        logger.info(f"Date range: {date_start} to {date_end}")
        
        params = {
            "databaseId": "WOS",
            "usrQuery": full_query,
            "count": min(max_results, 100),  # API limit per request
            "firstRecord": 1,
            "lang": "en",
            "timeSpan": f"{date_start}+{date_end}",
            "searchFields": "TS",  # Topic search (title, abstract, keywords)
        }
        
        try:
            # Execute initial search
            results = self._execute_paginated_search(params, max_results)
            
            logger.info(f"Retrieved {len(results.get('records', []))} articles from WoS")
            
            return {
                'source': 'Web of Science',
                'query': full_query,
                'date_range': (date_start, date_end),
                'total_results': results.get('QueryResult', {}).get('RecordsFound', 0),
                'retrieved_results': len(results.get('records', [])),
                'records': results.get('records', []),
                'search_metadata': {
                    'search_time': datetime.now().isoformat(),
                    'api_version': 'v1',
                    'database': 'WOS'
                }
            }
            
        except Exception as e:
            logger.error(f"WoS search failed: {str(e)}")
            raise
    
    def nechako_saturation_search(self,
                                 date_start: str = "1930-01-01", 
                                 date_end: Optional[str] = None,
                                 use_priority_terms: bool = False) -> Dict:
        """
        Execute the exact Nechako Watershed saturation search methodology.
        
        Args:
            date_start (str): Start date for search
            date_end (str): End date for search  
            use_priority_terms (bool): If True, use only major water bodies/communities
            
        Returns:
            Dict: Search results following original methodology
        """
        logger.info("Starting Nechako Watershed saturation search")
        
        # Build location query based on extracted terms
        if use_priority_terms:
            location_query = build_priority_location_query()
            logger.info("Using priority location terms for focused search")
        else:
            location_query = build_location_query()
            logger.info("Using all location terms for comprehensive search")
        
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
            'geographic_filter': GEOGRAPHIC_FILTER,
            'replicates_original': True
        }
        
        return results
    
    def _execute_paginated_search(self, base_params: Dict, max_results: int) -> Dict:
        """
        Execute a paginated search to retrieve all results up to max_results.
        
        Args:
            base_params (Dict): Base search parameters
            max_results (int): Maximum number of results to retrieve
            
        Returns:
            Dict: Combined results from all pages
        """
        all_records = []
        current_record = 1
        
        while len(all_records) < max_results:
            # Update pagination parameters
            params = base_params.copy()
            params['firstRecord'] = current_record
            params['count'] = min(100, max_results - len(all_records))
            
            # Execute request
            response = self._make_request("/documents", params)
            
            if not response or 'Data' not in response:
                break
                
            records = response['Data']['Records']['records']['REC']
            if not records:
                break
                
            # Handle single record vs list
            if isinstance(records, dict):
                records = [records]
                
            all_records.extend(records)
            
            # Check if we've retrieved all available results
            query_result = response['QueryResult']
            records_found = int(query_result['RecordsFound'])
            
            if len(all_records) >= records_found:
                break
                
            current_record += len(records)
            
            # Rate limiting
            time.sleep(API_RATE_LIMIT_DELAY)
        
        return {
            'QueryResult': response.get('QueryResult', {}),
            'records': all_records
        }
    
    def _make_request(self, endpoint: str, params: Dict) -> Optional[Dict]:
        """
        Make a request to the Web of Science API with error handling.
        
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
            logger.error(f"WoS API request failed: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response text: {e.response.text}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse WoS API response: {str(e)}")
            return None
    
    def validate_api_key(self) -> bool:
        """
        Validate that the API key is working.
        
        Returns:
            bool: True if API key is valid
        """
        try:
            # Simple test query
            params = {
                "databaseId": "WOS",
                "usrQuery": "water",
                "count": 1,
                "firstRecord": 1
            }
            
            response = self._make_request("/documents", params)
            return response is not None
            
        except Exception as e:
            logger.error(f"API key validation failed: {str(e)}")
            return False
    
    def get_usage_stats(self) -> Dict:
        """
        Get API usage statistics (if available).
        
        Returns:
            Dict: Usage statistics
        """
        # This would depend on the specific WoS API implementation
        # For now, return basic info
        return {
            'api_status': 'connected' if self.validate_api_key() else 'disconnected',
            'base_url': self.base_url,
            'rate_limit_delay': API_RATE_LIMIT_DELAY
        }


def convert_wos_record_to_standard_format(record: Dict) -> Dict:
    """
    Convert a Web of Science record to a standardized format.
    
    Args:
        record (Dict): Raw WoS record
        
    Returns:
        Dict: Standardized article record
    """
    try:
        # Extract basic metadata
        uid = record.get('UID', '')
        
        # Extract title
        title = ""
        if 'static_data' in record and 'summary' in record['static_data']:
            titles = record['static_data']['summary'].get('titles', {}).get('title', [])
            if titles:
                title = titles[0].get('content', '') if isinstance(titles, list) else titles.get('content', '')
        
        # Extract authors
        authors = []
        if 'static_data' in record and 'summary' in record['static_data']:
            names = record['static_data']['summary'].get('names', {}).get('name', [])
            if names:
                if isinstance(names, list):
                    authors = [name.get('display_name', '') for name in names if name.get('role') == 'author']
                else:
                    if names.get('role') == 'author':
                        authors = [names.get('display_name', '')]
        
        # Extract publication year
        year = ""
        if 'static_data' in record and 'summary' in record['static_data']:
            pub_info = record['static_data']['summary'].get('pub_info', {})
            year = pub_info.get('pubyear', '')
        
        # Extract journal
        journal = ""
        if 'static_data' in record and 'summary' in record['static_data']:
            titles = record['static_data']['summary'].get('titles', {}).get('title', [])
            for title_entry in titles if isinstance(titles, list) else [titles]:
                if title_entry.get('type') == 'source':
                    journal = title_entry.get('content', '')
                    break
        
        # Extract abstract
        abstract = ""
        if 'static_data' in record and 'fullrecord_metadata' in record['static_data']:
            abstracts = record['static_data']['fullrecord_metadata'].get('abstracts', {}).get('abstract', [])
            if abstracts:
                abstract = abstracts[0].get('abstract_text', {}).get('p', '') if isinstance(abstracts, list) else abstracts.get('abstract_text', {}).get('p', '')
        
        # Extract DOI
        doi = ""
        if 'dynamic_data' in record and 'cluster_related' in record['dynamic_data']:
            identifiers = record['dynamic_data']['cluster_related'].get('identifiers', {}).get('identifier', [])
            for identifier in identifiers if isinstance(identifiers, list) else [identifiers]:
                if identifier.get('type') == 'doi':
                    doi = identifier.get('value', '')
                    break
        
        return {
            'uid': uid,
            'title': title,
            'authors': authors,
            'year': year,
            'journal': journal,
            'abstract': abstract,
            'doi': doi,
            'source': 'Web of Science',
            'raw_record': record
        }
        
    except Exception as e:
        logger.error(f"Failed to convert WoS record: {str(e)}")
        return {
            'uid': record.get('UID', ''),
            'title': '',
            'authors': [],
            'year': '',
            'journal': '',
            'abstract': '',
            'doi': '',
            'source': 'Web of Science',
            'conversion_error': str(e),
            'raw_record': record
        }