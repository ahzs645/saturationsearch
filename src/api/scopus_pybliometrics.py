"""
Scopus API integration using pybliometrics for the Nechako Watershed saturation search.
Provides improved search capabilities and better metadata handling.
"""

import os
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path

# Configure pybliometrics
import pybliometrics
from pybliometrics.scopus import ScopusSearch, AbstractRetrieval
from pybliometrics.scopus import exception
Scopus401Error = exception.Scopus401Error
Scopus404Error = exception.Scopus404Error
Scopus429Error = exception.Scopus429Error
ScopusQueryError = exception.ScopusQueryError

# Import from parent directory
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from config import SCOPUS_API_KEY, API_RATE_LIMIT_DELAY, GEOGRAPHIC_FILTER, DEFAULT_LANGUAGE

logger = logging.getLogger(__name__)

class ScopusPybliometricsAPI:
    """
    Scopus API client using pybliometrics library.
    
    Provides advanced search capabilities with comprehensive metadata
    handling for the Nechako Watershed saturation search.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Scopus API client using pybliometrics.
        
        Args:
            api_key (str, optional): Scopus API key. If None, uses config.SCOPUS_API_KEY
        """
        self.api_key = api_key or SCOPUS_API_KEY
        if not self.api_key:
            raise ValueError("Scopus API key is required")
        
        # Configure pybliometrics
        self._configure_pybliometrics()
        
        logger.info("Scopus pybliometrics API client initialized")
    
    def _configure_pybliometrics(self):
        """Configure pybliometrics with API key and settings."""
        # Create config directory if it doesn't exist
        config_dir = Path.home() / ".config"
        config_dir.mkdir(parents=True, exist_ok=True)
        
        # Create config file with API key
        config_file = config_dir / "pybliometrics.cfg"
        
        # Always update/create config to ensure our key is used
        config_content = f"""[Directories]
AbstractRetrieval = {config_dir}/pybliometrics/abstract_retrieval
AuthorRetrieval = {config_dir}/pybliometrics/author_retrieval  
AuthorSearch = {config_dir}/pybliometrics/author_search
AffiliationRetrieval = {config_dir}/pybliometrics/affiliation_retrieval
AffiliationSearch = {config_dir}/pybliometrics/affiliation_search
CitationOverview = {config_dir}/pybliometrics/citation_overview
ScopusSearch = {config_dir}/pybliometrics/scopus_search
SerialSearch = {config_dir}/pybliometrics/serial_search
SerialTitle = {config_dir}/pybliometrics/serial_title
PlumXMetrics = {config_dir}/pybliometrics/plumx

[Authentication]
APIKey = {self.api_key}

[Requests]
Timeout = 20
Retries = 5
"""
        
        # Write config file
        with open(config_file, 'w') as f:
            f.write(config_content)
        logger.info(f"Created/updated pybliometrics configuration at {config_file}")
        
        # Create cache directories
        cache_base = config_dir / "pybliometrics"
        cache_base.mkdir(parents=True, exist_ok=True)
        
        # Initialize pybliometrics with the config file
        import pybliometrics.scopus
        pybliometrics.scopus.init()
    
    def _needs_config_update(self, config_file: Path) -> bool:
        """Check if config file needs updating with our API key."""
        try:
            with open(config_file, 'r') as f:
                content = f.read()
                return f"APIKey = {self.api_key}" not in content
        except Exception:
            return True
    
    def validate_api_key(self) -> bool:
        """
        Validate the API key by making a simple test request.
        
        Returns:
            bool: True if API key is valid, False otherwise
        """
        try:
            # Make a simple test search
            test_search = ScopusSearch("TITLE(test)", max_entries=1)
            logger.info("API key validation successful")
            return True
        except Scopus401Error:
            logger.error("API key validation failed: Unauthorized (401)")
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
                        max_results: int = 1000) -> Dict:
        """
        Search for documents using Scopus API via pybliometrics.
        
        Args:
            query (str): Scopus query string
            max_results (int): Maximum number of results to retrieve
            
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
        
        try:
            # Execute search using pybliometrics
            search = ScopusSearch(
                query,
                max_entries=max_results,
                subscriber=True  # We have a subscription
            )
            
            # Get total results count
            search_metadata['total_results'] = search.get_results_size() or 0
            logger.info(f"Total results available: {search_metadata['total_results']}")
            
            # Process results
            if search.results:
                for result in search.results:
                    doc = self._convert_search_result_to_standard_format(result)
                    all_documents.append(doc)
                    
                    if len(all_documents) >= max_results:
                        break
            
            search_metadata['retrieved_results'] = len(all_documents)
            logger.info(f"Retrieved {len(all_documents)} documents")
            
        except Scopus429Error as e:
            logger.error(f"Rate limit exceeded: {e}")
            search_metadata['error'] = "Rate limit exceeded. Please wait before retrying."
        except ScopusQueryError as e:
            logger.error(f"Query error: {e}")
            search_metadata['error'] = f"Invalid query: {str(e)}"
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
            'search_type': 'Nechako Watershed Saturation Search (Scopus)',
            'date_start': date_start,
            'date_end': date_end,
            'use_priority_terms': use_priority_terms,
            'max_results': max_results,
            'database': 'Scopus'
        })
        
        return results
    
    def _convert_search_result_to_standard_format(self, result) -> Dict:
        """
        Convert pybliometrics search result to standard format.
        
        Args:
            result: Search result from pybliometrics
            
        Returns:
            Dict: Standardized document format
        """
        # Extract authors
        authors = []
        if hasattr(result, 'author_names') and result.author_names:
            # Split the author string (format: "Last1, First1; Last2, First2")
            author_list = result.author_names.split(';')
            authors = [author.strip() for author in author_list]
        
        # Extract publication year
        year = None
        if hasattr(result, 'coverDate') and result.coverDate:
            try:
                year = int(result.coverDate.split('-')[0])
            except (ValueError, AttributeError):
                pass
        
        # Extract keywords
        keywords = []
        if hasattr(result, 'authkeywords') and result.authkeywords:
            # Keywords are semicolon-separated
            keywords = [kw.strip() for kw in result.authkeywords.split(';') if kw.strip()]
        
        return {
            'title': getattr(result, 'title', '') or '',
            'authors': authors,
            'abstract': getattr(result, 'description', '') or '',  # Note: Full abstract requires AbstractRetrieval
            'year': year,
            'journal': getattr(result, 'publicationName', '') or '',
            'volume': getattr(result, 'volume', '') or '',
            'issue': getattr(result, 'issueIdentifier', '') or '',
            'pages': getattr(result, 'pageRange', '') or '',
            'doi': getattr(result, 'doi', '') or '',
            'url': f"https://www.scopus.com/record/display.uri?eid={result.eid}" if hasattr(result, 'eid') else '',
            'keywords': keywords,
            'document_type': getattr(result, 'aggregationType', '') or '',
            'cited_by_count': int(getattr(result, 'citedby_count', 0) or 0),
            'eid': getattr(result, 'eid', '') or '',
            'scopus_id': getattr(result, 'scopus_id', '') or '',
            'source': 'Scopus (pybliometrics)',
            'retrieved_date': datetime.now().isoformat(),
            'affiliation': getattr(result, 'affiliation_name', '') or '',
            'author_keywords': keywords,
            'index_keywords': [],  # Would need AbstractRetrieval for these
            'funding': getattr(result, 'fund_sponsor', '') or ''
        }
    
    def get_document_abstract(self, eid: str) -> Optional[str]:
        """
        Retrieve full abstract for a document using its EID.
        
        Args:
            eid (str): Scopus EID
            
        Returns:
            Optional[str]: Abstract text if available
        """
        try:
            ab = AbstractRetrieval(eid)
            return ab.abstract
        except Scopus404Error:
            logger.warning(f"Document not found: {eid}")
            return None
        except Exception as e:
            logger.error(f"Error retrieving abstract for {eid}: {e}")
            return None
    
    def enrich_with_abstracts(self, documents: List[Dict], batch_size: int = 10) -> List[Dict]:
        """
        Enrich documents with full abstracts (rate-limited).
        
        Args:
            documents (List[Dict]): Documents to enrich
            batch_size (int): Number of abstracts to retrieve before pausing
            
        Returns:
            List[Dict]: Documents with abstracts added
        """
        logger.info(f"Enriching {len(documents)} documents with abstracts")
        
        enriched = 0
        for i, doc in enumerate(documents):
            if doc.get('eid') and not doc.get('abstract'):
                abstract = self.get_document_abstract(doc['eid'])
                if abstract:
                    doc['abstract'] = abstract
                    enriched += 1
                
                # Rate limiting
                if (i + 1) % batch_size == 0:
                    logger.info(f"Enriched {enriched} documents so far...")
                    time.sleep(API_RATE_LIMIT_DELAY)
        
        logger.info(f"Enriched {enriched} documents with abstracts")
        return documents


def convert_scopus_pybliometrics_record_to_standard_format(record: Dict) -> Dict:
    """
    Convert a Scopus pybliometrics record to standard format.
    This is a helper function for compatibility with existing code.
    
    Args:
        record (Dict): Record from pybliometrics
        
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