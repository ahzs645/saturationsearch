"""
Zotero API integration for organizing and managing literature search results.
Maintains the exact organizational structure from the original methodology.
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import json
from pyzotero import zotero

from config import ZOTERO_API_KEY, ZOTERO_LIBRARY_ID, ZOTERO_LIBRARY_TYPE

logger = logging.getLogger(__name__)

class ZoteroManager:
    """
    Zotero API manager for organizing saturation search results.
    
    Maintains organized collection structure:
    - SearchResults[YYYYMM] (for each search)
    - Manual Review Queue (uncertain articles)
    - Excluded Articles (for reference)
    - On Portal (articles uploaded to portal)
    """
    
    def __init__(self, 
                 library_id: str = None,
                 api_key: str = None,
                 library_type: str = None):
        """
        Initialize Zotero manager.
        
        Args:
            library_id (str): Zotero library ID
            api_key (str): Zotero API key
            library_type (str): Library type ('user' or 'group')
        """
        self.library_id = library_id or ZOTERO_LIBRARY_ID
        self.api_key = api_key or ZOTERO_API_KEY
        self.library_type = library_type or ZOTERO_LIBRARY_TYPE
        
        if not all([self.library_id, self.api_key]):
            raise ValueError("Zotero library ID and API key are required")
        
        try:
            self.zot = zotero.Zotero(self.library_id, self.library_type, self.api_key)
            logger.info(f"Connected to Zotero {self.library_type} library: {self.library_id}")
        except Exception as e:
            logger.error(f"Failed to connect to Zotero: {e}")
            raise
    
    def create_search_collection_structure(self, search_date: datetime) -> Dict[str, str]:
        """
        Create organized collection structure for a new search.
        
        Args:
            search_date (datetime): Date of the search
            
        Returns:
            Dict[str, str]: Mapping of collection names to collection IDs
        """
        search_id = search_date.strftime("%Y%m")
        
        collections = {
            f"SearchResults{search_id}": f"Results from search conducted {search_date.strftime('%B %Y')}",
            f"ManualReview{search_id}": f"Articles requiring manual review from {search_date.strftime('%B %Y')} search",
            f"Excluded{search_id}": f"Excluded articles from {search_date.strftime('%B %Y')} search (for reference)"
        }
        
        collection_ids = {}
        
        for collection_name, description in collections.items():
            try:
                # Check if collection already exists
                existing_collections = self.zot.collections()
                existing_names = {coll['data']['name']: coll['key'] for coll in existing_collections}
                
                if collection_name in existing_names:
                    collection_ids[collection_name] = existing_names[collection_name]
                    logger.info(f"Using existing collection: {collection_name}")
                else:
                    # Create new collection
                    collection_data = {
                        'name': collection_name,
                        'description': description
                    }
                    
                    result = self.zot.create_collection(collection_data)
                    collection_ids[collection_name] = result['key']
                    logger.info(f"Created collection: {collection_name}")
                    
            except Exception as e:
                logger.error(f"Failed to create collection {collection_name}: {e}")
                raise
        
        return collection_ids
    
    def upload_articles(self, 
                       articles: List[Dict],
                       collection_id: str,
                       search_metadata: Dict = None) -> Dict:
        """
        Upload articles to a Zotero collection.
        
        Args:
            articles (List[Dict]): Articles to upload
            collection_id (str): Target collection ID
            search_metadata (Dict): Metadata about the search
            
        Returns:
            Dict: Upload results and statistics
        """
        logger.info(f"Uploading {len(articles)} articles to Zotero collection {collection_id}")
        
        upload_results = {
            'successful_uploads': 0,
            'failed_uploads': 0,
            'skipped_duplicates': 0,
            'errors': [],
            'uploaded_items': []
        }
        
        # Get existing items in collection to avoid duplicates
        existing_items = self._get_existing_items(collection_id)
        existing_dois = {item.get('DOI', '').lower() for item in existing_items if item.get('DOI')}
        existing_titles = {self._normalize_title(item.get('title', '')) for item in existing_items if item.get('title')}
        
        for i, article in enumerate(articles):
            try:
                # Check for duplicates
                article_doi = article.get('doi', '').lower()
                article_title = self._normalize_title(article.get('title', ''))
                
                if article_doi and article_doi in existing_dois:
                    upload_results['skipped_duplicates'] += 1
                    logger.debug(f"Skipping duplicate DOI: {article_doi}")
                    continue
                
                if article_title and article_title in existing_titles:
                    upload_results['skipped_duplicates'] += 1
                    logger.debug(f"Skipping duplicate title: {article_title[:50]}...")
                    continue
                
                # Convert to Zotero format
                zotero_item = self._convert_to_zotero_format(article, search_metadata)
                
                # Upload to Zotero
                result = self.zot.create_item(zotero_item)
                
                # Add to collection
                if collection_id:
                    self.zot.addto_collection(collection_id, result)
                
                upload_results['successful_uploads'] += 1
                upload_results['uploaded_items'].append({
                    'item_key': result['key'],
                    'title': article.get('title', '')[:100]
                })
                
                logger.debug(f"Uploaded article {i+1}: {article.get('title', '')[:50]}...")
                
            except Exception as e:
                upload_results['failed_uploads'] += 1
                error_msg = f"Failed to upload article {i+1}: {str(e)}"
                upload_results['errors'].append(error_msg)
                logger.error(error_msg)
        
        logger.info(f"Upload complete: {upload_results['successful_uploads']} successful, "
                   f"{upload_results['failed_uploads']} failed, "
                   f"{upload_results['skipped_duplicates']} duplicates skipped")
        
        return upload_results
    
    def organize_screening_results(self, 
                                 screening_decisions: List,
                                 search_date: datetime) -> Dict:
        """
        Organize screening results into appropriate Zotero collections.
        
        Args:
            screening_decisions (List): List of screening decisions
            search_date (datetime): Date of the search
            
        Returns:
            Dict: Organization results
        """
        logger.info("Organizing screening results into Zotero collections")
        
        # Create collection structure
        collections = self.create_search_collection_structure(search_date)
        
        # Group articles by decision
        included_articles = []
        manual_review_articles = []
        excluded_articles = []
        
        for decision in screening_decisions:
            # Note: This assumes screening_decisions contains the original articles
            # You may need to adjust based on your actual data structure
            article = decision.get('article', {})
            
            if decision.decision.value == 'included':
                included_articles.append(self._add_screening_metadata(article, decision))
            elif decision.decision.value == 'manual_review':
                manual_review_articles.append(self._add_screening_metadata(article, decision))
            elif decision.decision.value == 'excluded':
                excluded_articles.append(self._add_screening_metadata(article, decision))
        
        # Upload to respective collections
        results = {}
        
        search_id = search_date.strftime("%Y%m")
        
        if included_articles:
            collection_id = collections[f"SearchResults{search_id}"]
            results['included'] = self.upload_articles(included_articles, collection_id)
        
        if manual_review_articles:
            collection_id = collections[f"ManualReview{search_id}"]
            results['manual_review'] = self.upload_articles(manual_review_articles, collection_id)
        
        if excluded_articles:
            collection_id = collections[f"Excluded{search_id}"]
            results['excluded'] = self.upload_articles(excluded_articles, collection_id)
        
        return results
    
    def _get_existing_items(self, collection_id: str) -> List[Dict]:
        """Get existing items in a collection."""
        try:
            items = self.zot.collection_items(collection_id)
            return [item['data'] for item in items]
        except Exception as e:
            logger.warning(f"Failed to get existing items: {e}")
            return []
    
    def _normalize_title(self, title: str) -> str:
        """Normalize title for duplicate detection."""
        import re
        if not title:
            return ""
        
        # Remove punctuation and normalize whitespace
        normalized = re.sub(r'[^\w\s]', '', title.lower())
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return normalized
    
    def _convert_to_zotero_format(self, article: Dict, search_metadata: Dict = None) -> Dict:
        """
        Convert article to Zotero item format.
        
        Args:
            article (Dict): Article data
            search_metadata (Dict): Search metadata
            
        Returns:
            Dict: Zotero-formatted item
        """
        # Determine item type
        item_type = self._determine_item_type(article)
        
        # Base item structure
        zotero_item = {
            'itemType': item_type,
            'title': article.get('title', ''),
            'abstractNote': article.get('abstract', ''),
            'date': str(article.get('year', '')),
            'language': 'en',
            'url': article.get('url', ''),
            'DOI': article.get('doi', ''),
        }
        
        # Add authors
        authors = article.get('authors', [])
        if authors:
            zotero_item['creators'] = []
            for author in authors:
                if isinstance(author, str):
                    # Parse author string
                    author_parts = author.split(',')
                    if len(author_parts) >= 2:
                        zotero_item['creators'].append({
                            'creatorType': 'author',
                            'lastName': author_parts[0].strip(),
                            'firstName': author_parts[1].strip()
                        })
                    else:
                        zotero_item['creators'].append({
                            'creatorType': 'author',
                            'name': author.strip()
                        })
        
        # Add publication details based on item type
        if item_type == 'journalArticle':
            zotero_item['publicationTitle'] = article.get('journal', '')
            zotero_item['volume'] = article.get('volume', '')
            zotero_item['issue'] = article.get('issue', '')
            zotero_item['pages'] = article.get('pages', '')
        elif item_type == 'conferencePaper':
            zotero_item['proceedingsTitle'] = article.get('journal', '')
        
        # Add tags
        tags = ['Saturation Search']
        
        if search_metadata:
            search_date = search_metadata.get('search_time', '')
            if search_date:
                tags.append(f'Search{search_date[:7].replace("-", "")}')  # YYYYMM format
            
            source = search_metadata.get('database', '')
            if source:
                tags.append(source)
        
        # Add theme tag if available
        theme = article.get('theme', '')
        if theme:
            tags.append(theme)
        
        # Add location relevance tag
        location_matches = article.get('location_matches', {})
        if location_matches and location_matches.get('total', 0) > 0:
            tags.append('Nechako Watershed')
        
        zotero_item['tags'] = [{'tag': tag} for tag in tags]
        
        # Add extra fields for tracking
        zotero_item['extra'] = self._build_extra_field(article, search_metadata)
        
        return zotero_item
    
    def _determine_item_type(self, article: Dict) -> str:
        """
        Determine appropriate Zotero item type.
        
        Args:
            article (Dict): Article data
            
        Returns:
            str: Zotero item type
        """
        journal = article.get('journal', '').lower()
        
        # Conference proceedings indicators
        conference_indicators = [
            'proceedings', 'conference', 'symposium', 'workshop',
            'congress', 'meeting', 'convention'
        ]
        
        if any(indicator in journal for indicator in conference_indicators):
            return 'conferencePaper'
        
        # Default to journal article
        return 'journalArticle'
    
    def _build_extra_field(self, article: Dict, search_metadata: Dict = None) -> str:
        """Build the extra field with search metadata."""
        extra_lines = []
        
        # Source database
        source = article.get('source', '')
        if source:
            extra_lines.append(f"Source: {source}")
        
        # Search metadata
        if search_metadata:
            search_time = search_metadata.get('search_time', '')
            if search_time:
                extra_lines.append(f"Search Date: {search_time[:10]}")
        
        # Geographic relevance
        geo_score = article.get('geographic_relevance_score', 0)
        if geo_score > 0:
            extra_lines.append(f"Geographic Relevance: {geo_score:.2f}")
        
        # Location matches
        location_matches = article.get('location_matches', {})
        if location_matches and location_matches.get('total', 0) > 0:
            extra_lines.append(f"Location Matches: {location_matches['total']}")
        
        return '\n'.join(extra_lines)
    
    def _add_screening_metadata(self, article: Dict, decision) -> Dict:
        """Add screening decision metadata to article."""
        article_with_metadata = article.copy()
        
        article_with_metadata.update({
            'screening_decision': decision.decision.value,
            'confidence_score': decision.confidence_score,
            'theme': decision.theme.value if decision.theme else None,
            'geographic_relevance_score': decision.geographic_relevance_score,
            'location_matches': decision.location_matches,
            'inclusion_reasons': decision.inclusion_reasons,
            'exclusion_reasons': decision.exclusion_reasons,
            'manual_review_reasons': decision.manual_review_reasons
        })
        
        return article_with_metadata
    
    def get_collection_statistics(self) -> Dict:
        """Get statistics about collections and items."""
        try:
            collections = self.zot.collections()
            stats = {
                'total_collections': len(collections),
                'collections': {}
            }
            
            for collection in collections:
                collection_name = collection['data']['name']
                collection_key = collection['key']
                
                # Get item count
                try:
                    items = self.zot.collection_items(collection_key)
                    item_count = len(items)
                except:
                    item_count = 0
                
                stats['collections'][collection_name] = {
                    'key': collection_key,
                    'item_count': item_count
                }
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get collection statistics: {e}")
            return {'error': str(e)}
    
    def validate_connection(self) -> bool:
        """Validate Zotero API connection."""
        try:
            # Try to get library information
            items = self.zot.items(limit=1)
            logger.info("Zotero connection validated successfully")
            return True
        except Exception as e:
            logger.error(f"Zotero connection validation failed: {e}")
            return False


def export_to_portal_format(zotero_items: List[Dict]) -> List[Dict]:
    """
    Export Zotero items to format suitable for portal upload.
    
    Args:
        zotero_items (List[Dict]): Zotero items
        
    Returns:
        List[Dict]: Portal-ready items
    """
    portal_items = []
    
    for item in zotero_items:
        portal_item = {
            'title': item.get('title', ''),
            'authors': item.get('creators', []),
            'abstract': item.get('abstractNote', ''),
            'year': item.get('date', ''),
            'journal': item.get('publicationTitle', ''),
            'doi': item.get('DOI', ''),
            'url': item.get('url', ''),
            'tags': [tag['tag'] for tag in item.get('tags', [])],
            'source': 'Nechako Saturation Search'
        }
        
        portal_items.append(portal_item)
    
    return portal_items