"""
Web of Science Starter API integration using the official Python client.
Provides improved search capabilities for the Nechako Watershed saturation search.
"""

import os
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import clarivate.wos_starter.client
from clarivate.wos_starter.client.rest import ApiException

# Import from parent directory since this is a new file
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from config import WOS_API_KEY, API_RATE_LIMIT_DELAY, GEOGRAPHIC_FILTER, DEFAULT_LANGUAGE

logger = logging.getLogger(__name__)

class WebOfScienceStarterAPI:
    """
    Web of Science Starter API client using the official Python client.
    
    Provides advanced search capabilities with proper field tags and
    better metadata handling for the Nechako Watershed saturation search.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Web of Science Starter API client.
        
        Args:
            api_key (str, optional): WoS API key. If None, uses config.WOS_API_KEY
        """
        self.api_key = api_key or WOS_API_KEY
        if not self.api_key:
            raise ValueError("Web of Science API key is required")
        
        # Configure the client
        self.configuration = clarivate.wos_starter.client.Configuration(
            host="https://api.clarivate.com/apis/wos-starter/v1"
        )
        self.configuration.api_key['ClarivateApiKeyAuth'] = self.api_key
        
        self.api_client = clarivate.wos_starter.client.ApiClient(self.configuration)
        self.documents_api = clarivate.wos_starter.client.DocumentsApi(self.api_client)
        
        logger.info("Web of Science Starter API client initialized")
    
    def validate_api_key(self) -> bool:
        """
        Validate the API key by making a simple test request.
        
        Returns:
            bool: True if API key is valid, False otherwise
        """
        try:
            # Make a simple test query
            response = self.documents_api.documents_get(
                q="PY=2023",  # Simple query for year 2023
                db="WOS",
                limit=1
            )
            logger.info("API key validation successful")
            return True
        except ApiException as e:
            if e.status == 401:
                logger.error("API key validation failed: Unauthorized")
            else:
                logger.error(f"API key validation failed: {e}")
            return False
        except Exception as e:
            logger.error(f"API key validation error: {e}")
            return False
    
    def build_nechako_query(self, 
                           use_priority_terms: bool = False,
                           date_start: str = "1930-01-01",
                           date_end: Optional[str] = None) -> str:
        """
        Build a Web of Science query for Nechako Watershed research.
        
        Args:
            use_priority_terms (bool): Use priority location terms only
            date_start (str): Start date (YYYY-MM-DD)
            date_end (str): End date (YYYY-MM-DD, defaults to current year)
            
        Returns:
            str: Web of Science query string
        """
        if date_end is None:
            date_end = str(datetime.now().year)
        else:
            date_end = date_end.split('-')[0]  # Extract year
        
        date_start_year = date_start.split('-')[0]  # Extract year
        
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
                "Carrier Sekani"
            ]
        
        # Build topic search (TS) for location terms
        location_query = " OR ".join([f'"{term}"' for term in location_terms])
        
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
            "land use"
        ]
        
        theme_query = " OR ".join([f'"{term}"' for term in theme_terms])
        
        # Combine location and theme searches
        query_parts = [
            f"TS=({location_query})",
            f"TS=({theme_query})",
            f"PY=({date_start_year}-{date_end})"
        ]
        
        # Add language filter if specified
        if DEFAULT_LANGUAGE and DEFAULT_LANGUAGE.lower() == "english":
            query_parts.append("LA=(English)")
        
        query = " AND ".join(query_parts)
        
        logger.info(f"Built query: {query[:200]}...")
        return query
    
    def search_documents(self,
                        query: str,
                        max_results: int = 1000,
                        database: str = "WOS") -> Dict:
        """
        Search for documents using the Web of Science Starter API.
        
        Args:
            query (str): Web of Science query string
            max_results (int): Maximum number of results to retrieve
            database (str): Database to search (WOS, BIOABS, etc.)
            
        Returns:
            Dict: Search results with metadata
        """
        logger.info(f"Executing search in {database} database")
        logger.info(f"Query: {query}")
        
        all_documents = []
        page = 1
        limit = min(50, max_results)  # API allows max 50 per page
        
        search_metadata = {
            'query': query,
            'database': database,
            'search_time': datetime.now().isoformat(),
            'total_results': 0,
            'retrieved_results': 0,
            'pages_retrieved': 0
        }
        
        try:
            while len(all_documents) < max_results:
                logger.info(f"Fetching page {page}, limit {limit}")
                
                try:
                    response = self.documents_api.documents_get(
                        q=query,
                        db=database,
                        limit=limit,
                        page=page,
                        sort_field="RS+D",  # Relevance descending
                        detail="full"  # Get full details
                    )
                    
                    # Handle response object structure - use 'hits' attribute
                    response_data = getattr(response, 'hits', [])
                    
                    if not response_data:
                        logger.info("No more results available")
                        break
                    
                    # Update metadata on first page
                    if page == 1:
                        total_results = getattr(response.metadata, 'total', 0) if hasattr(response, 'metadata') else 0
                        search_metadata['total_results'] = total_results
                        logger.info(f"Total results available: {total_results}")
                    
                    # Add documents from this page
                    for doc in response_data:
                        if len(all_documents) >= max_results:
                            break
                        all_documents.append(self._convert_document_to_standard_format(doc))
                    
                    search_metadata['retrieved_results'] = len(all_documents)
                    search_metadata['pages_retrieved'] = page
                    
                    logger.info(f"Retrieved {len(response_data)} documents from page {page}")
                    
                    # Check if we have all available results
                    total_results = getattr(response.metadata, 'total', 0) if hasattr(response, 'metadata') else 0
                    if len(response_data) < limit or page * limit >= total_results:
                        logger.info("Retrieved all available results")
                        break
                    
                    page += 1
                    
                    # Rate limiting
                    if API_RATE_LIMIT_DELAY > 0:
                        time.sleep(API_RATE_LIMIT_DELAY)
                        
                except ApiException as e:
                    logger.error(f"API error on page {page}: {e}")
                    if e.status == 429:  # Rate limit
                        logger.info("Rate limit hit, waiting 60 seconds...")
                        time.sleep(60)
                        continue
                    else:
                        break
                        
        except Exception as e:
            logger.error(f"Search execution failed: {e}")
            search_metadata['error'] = str(e)
        
        logger.info(f"Search completed: {len(all_documents)} documents retrieved")
        
        return {
            'records': all_documents,
            'metadata': search_metadata,
            'total_results': search_metadata['total_results'],
            'retrieved_results': search_metadata['retrieved_results']
        }
    
    def nechako_saturation_search(self,
                                 date_start: str = "1930-01-01", 
                                 date_end: Optional[str] = None,
                                 use_priority_terms: bool = False,
                                 max_results: int = 1000) -> Dict:
        """
        Execute the Nechako Watershed saturation search.
        
        Args:
            date_start (str): Start date (YYYY-MM-DD)
            date_end (str): End date (YYYY-MM-DD)
            use_priority_terms (bool): Use priority location terms only
            max_results (int): Maximum results to retrieve
            
        Returns:
            Dict: Search results
        """
        logger.info("Starting Nechako Watershed saturation search")
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
            max_results=max_results,
            database="WOS"
        )
        
        # Add search parameters to metadata
        results['metadata'].update({
            'search_type': 'Nechako Watershed Saturation Search',
            'date_start': date_start,
            'date_end': date_end,
            'use_priority_terms': use_priority_terms,
            'max_results': max_results
        })
        
        return results
    
    def _convert_document_to_standard_format(self, doc) -> Dict:
        """
        Convert Web of Science document to standard format used by the system.
        
        Args:
            doc: Document object from WoS API
            
        Returns:
            Dict: Standardized document format
        """
        # Extract authors
        authors = []
        if hasattr(doc, 'names') and doc.names and hasattr(doc.names, 'authors'):
            for author in doc.names.authors:
                if hasattr(author, 'display_name'):
                    authors.append(author.display_name)
                elif hasattr(author, 'last_name') and hasattr(author, 'first_name'):
                    authors.append(f"{author.last_name}, {author.first_name}")
        
        # Extract DOI
        doi = ""
        if hasattr(doc, 'identifiers') and doc.identifiers:
            if hasattr(doc.identifiers, 'doi'):
                doi = doc.identifiers.doi or ""
        
        # Extract journal/source
        journal = ""
        if hasattr(doc, 'source') and doc.source:
            if hasattr(doc.source, 'source_title'):
                journal = doc.source.source_title or ""
        
        # Extract publication year
        year = None
        if hasattr(doc, 'source') and doc.source and hasattr(doc.source, 'published_date'):
            try:
                if doc.source.published_date:
                    year = int(doc.source.published_date.split('-')[0])
            except (ValueError, AttributeError):
                pass
        
        # Extract volume, issue, pages
        volume = ""
        issue = ""
        pages = ""
        if hasattr(doc, 'source') and doc.source:
            if hasattr(doc.source, 'volume'):
                volume = doc.source.volume or ""
            if hasattr(doc.source, 'issue'):
                issue = doc.source.issue or ""
            if hasattr(doc.source, 'pages') and doc.source.pages:
                if hasattr(doc.source.pages, 'range'):
                    pages = doc.source.pages.range or ""
        
        # Extract keywords
        keywords = []
        if hasattr(doc, 'keywords') and doc.keywords:
            if hasattr(doc.keywords, 'author_keywords'):
                keywords.extend(doc.keywords.author_keywords or [])
        
        # Extract URL
        url = ""
        if hasattr(doc, 'links') and doc.links:
            for link in doc.links:
                if hasattr(link, 'url') and link.url:
                    url = link.url
                    break
        
        return {
            'title': getattr(doc, 'title', '') or '',
            'authors': authors,
            'abstract': '',  # Not available in starter API
            'year': year,
            'journal': journal,
            'volume': volume,
            'issue': issue,
            'pages': pages,
            'doi': doi,
            'url': url,
            'keywords': keywords,
            'document_type': getattr(doc, 'document_type', '') or '',
            'times_cited': getattr(doc, 'times_cited', 0) or 0,
            'uid': getattr(doc, 'uid', '') or '',
            'source': 'Web of Science Starter API',
            'retrieved_date': datetime.now().isoformat()
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
            query = f'DO="{doi}"'
            response = self.documents_api.documents_get(
                q=query,
                db="WOS",
                limit=1
            )
            
            response_data = getattr(response, 'hits', [])
            
            if response_data and len(response_data) > 0:
                return self._convert_document_to_standard_format(response_data[0])
            
            return None
            
        except ApiException as e:
            logger.error(f"Error retrieving document by DOI {doi}: {e}")
            return None
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if hasattr(self.api_client, 'close'):
            self.api_client.close()


def convert_wos_starter_record_to_standard_format(record: Dict) -> Dict:
    """
    Convert a Web of Science Starter API record to standard format.
    This is a helper function for compatibility with existing code.
    
    Args:
        record (Dict): Raw WoS record
        
    Returns:
        Dict: Standardized record format
    """
    # This function assumes the record is already converted by the API class
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
    
    return standardized