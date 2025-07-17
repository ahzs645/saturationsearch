#!/usr/bin/env python3
"""
Deduplication script for the functional search results.
Applies the 5-level duplicate detection algorithm to find unique articles.
"""

import sys
import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass, asdict
from fuzzywuzzy import fuzz
import difflib
import hashlib
import re
from collections import defaultdict

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/deduplication.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class DuplicateMatch:
    """Represents a duplicate match between two articles."""
    article1_id: str
    article2_id: str
    match_type: str
    confidence: float
    reason: str
    similarity_score: Optional[float] = None

@dataclass
class DeduplicationReport:
    """Report of deduplication process."""
    total_input_articles: int
    unique_articles: int
    duplicates_removed: int
    matches_by_type: Dict[str, int]
    duplicate_matches: List[DuplicateMatch]
    processing_time: float

class AdvancedDuplicateDetector:
    """
    Advanced multi-level duplicate detection system.
    
    Implements 5 levels of duplicate detection:
    1. Exact DOI/PMID matches
    2. High-confidence title matching (95%+)
    3. Author + Year + Journal combinations  
    4. Abstract semantic similarity
    5. Cross-database comparison
    """
    
    def __init__(self, 
                 title_threshold: float = 0.95,
                 abstract_threshold: float = 0.85):
        self.title_threshold = title_threshold
        self.abstract_threshold = abstract_threshold
        self.matches = []
        self.processed_pairs = set()
    
    def detect_duplicates(self, articles: List[Dict]) -> Tuple[List[Dict], DeduplicationReport]:
        """
        Detect and remove duplicates from article list.
        
        Args:
            articles: List of article dictionaries
            
        Returns:
            Tuple of (unique_articles, deduplication_report)
        """
        start_time = datetime.now()
        
        logger.info(f"Starting deduplication of {len(articles)} articles")
        
        # Reset state
        self.matches = []
        self.processed_pairs = set()
        
        # Add unique IDs to articles
        for i, article in enumerate(articles):
            article['_internal_id'] = f"art_{i:06d}"
            article['_source_db'] = article.get('_source_db', 'unknown')
        
        # Level 1: DOI/PMID exact matches
        logger.info("Level 1: DOI/PMID matching...")
        self._detect_doi_duplicates(articles)
        
        # Level 2: Title similarity matching
        logger.info("Level 2: Title similarity matching...")
        self._detect_title_duplicates(articles)
        
        # Level 3: Author + Year + Journal matching
        logger.info("Level 3: Author-Year-Journal matching...")
        self._detect_author_year_journal_duplicates(articles)
        
        # Level 4: Abstract similarity
        logger.info("Level 4: Abstract similarity matching...")
        self._detect_abstract_duplicates(articles)
        
        # Level 5: Cross-database fuzzy matching
        logger.info("Level 5: Cross-database fuzzy matching...")
        self._detect_cross_database_duplicates(articles)
        
        # Remove duplicates and generate report
        unique_articles, report = self._generate_final_results(articles, start_time)
        
        logger.info(f"Deduplication completed: {len(unique_articles)} unique articles from {len(articles)} input")
        
        return unique_articles, report
    
    def _detect_doi_duplicates(self, articles: List[Dict]):
        """Detect duplicates based on exact DOI matches."""
        doi_map = defaultdict(list)
        
        for article in articles:
            doi = self._normalize_doi(article.get('doi', ''))
            if doi:
                doi_map[doi].append(article['_internal_id'])
        
        for doi, article_ids in doi_map.items():
            if len(article_ids) > 1:
                for i in range(len(article_ids)):
                    for j in range(i + 1, len(article_ids)):
                        self._add_match(
                            article_ids[i], article_ids[j],
                            'doi_exact', 1.0, f'Identical DOI: {doi}'
                        )
    
    def _detect_title_duplicates(self, articles: List[Dict]):
        """Detect duplicates based on high-confidence title similarity."""
        for i in range(len(articles)):
            for j in range(i + 1, len(articles)):
                if self._is_pair_processed(articles[i]['_internal_id'], articles[j]['_internal_id']):
                    continue
                
                title1 = self._normalize_title(articles[i].get('title', ''))
                title2 = self._normalize_title(articles[j].get('title', ''))
                
                if not title1 or not title2:
                    continue
                
                similarity = fuzz.ratio(title1, title2) / 100.0
                
                if similarity >= self.title_threshold:
                    self._add_match(
                        articles[i]['_internal_id'], articles[j]['_internal_id'],
                        'title_similarity', similarity, 
                        f'High title similarity: {similarity:.2%}'
                    )
    
    def _detect_author_year_journal_duplicates(self, articles: List[Dict]):
        """Detect duplicates based on author + year + journal combinations."""
        signature_map = defaultdict(list)
        
        for article in articles:
            signature = self._create_author_year_journal_signature(article)
            if signature:
                signature_map[signature].append(article['_internal_id'])
        
        for signature, article_ids in signature_map.items():
            if len(article_ids) > 1:
                for i in range(len(article_ids)):
                    for j in range(i + 1, len(article_ids)):
                        if not self._is_pair_processed(article_ids[i], article_ids[j]):
                            self._add_match(
                                article_ids[i], article_ids[j],
                                'author_year_journal', 0.9,
                                f'Matching author-year-journal: {signature}'
                            )
    
    def _detect_abstract_duplicates(self, articles: List[Dict]):
        """Detect duplicates based on abstract similarity."""
        abstracts = []
        id_map = {}
        
        for article in articles:
            abstract = self._normalize_abstract(article.get('abstract', ''))
            if abstract and len(abstract) > 100:  # Only compare substantial abstracts
                abstracts.append(abstract)
                id_map[len(abstracts) - 1] = article['_internal_id']
        
        # Compare abstracts pairwise
        for i in range(len(abstracts)):
            for j in range(i + 1, len(abstracts)):
                id1, id2 = id_map[i], id_map[j]
                
                if self._is_pair_processed(id1, id2):
                    continue
                
                similarity = difflib.SequenceMatcher(None, abstracts[i], abstracts[j]).ratio()
                
                if similarity >= self.abstract_threshold:
                    self._add_match(
                        id1, id2, 'abstract_similarity', similarity,
                        f'High abstract similarity: {similarity:.2%}'
                    )
    
    def _detect_cross_database_duplicates(self, articles: List[Dict]):
        """Detect duplicates across different databases using fuzzy matching."""
        db_groups = defaultdict(list)
        
        # Group articles by source database
        for article in articles:
            db = article.get('_source_db', 'unknown')
            db_groups[db].append(article)
        
        # Compare articles across different databases
        db_list = list(db_groups.keys())
        for i in range(len(db_list)):
            for j in range(i + 1, len(db_list)):
                db1, db2 = db_list[i], db_list[j]
                self._compare_cross_database_groups(db_groups[db1], db_groups[db2])
    
    def _compare_cross_database_groups(self, group1: List[Dict], group2: List[Dict]):
        """Compare articles between two database groups."""
        for article1 in group1:
            for article2 in group2:
                if self._is_pair_processed(article1['_internal_id'], article2['_internal_id']):
                    continue
                
                # Multi-factor similarity check
                title_sim = self._title_similarity(article1, article2)
                author_sim = self._author_similarity(article1, article2)
                year_match = self._year_match(article1, article2)
                
                # Combined score with weights
                combined_score = (title_sim * 0.5 + author_sim * 0.3 + (1.0 if year_match else 0.0) * 0.2)
                
                if combined_score >= 0.8:  # High confidence cross-db match
                    self._add_match(
                        article1['_internal_id'], article2['_internal_id'],
                        'cross_database', combined_score,
                        f'Cross-database match (title:{title_sim:.2f}, author:{author_sim:.2f}, year:{year_match})'
                    )
    
    def _normalize_doi(self, doi: str) -> str:
        """Normalize DOI for comparison."""
        if not doi:
            return ''
        # Remove prefixes and normalize
        doi = re.sub(r'^(doi:|DOI:|https?://doi\.org/)', '', doi.strip())
        return doi.lower()
    
    def _normalize_title(self, title: str) -> str:
        """Normalize title for comparison."""
        if not title:
            return ''
        # Remove extra whitespace, punctuation, convert to lowercase
        title = re.sub(r'[^\w\s]', '', title.lower())
        title = re.sub(r'\s+', ' ', title).strip()
        return title
    
    def _normalize_abstract(self, abstract: str) -> str:
        """Normalize abstract for comparison."""
        if not abstract:
            return ''
        # Basic normalization
        abstract = re.sub(r'\s+', ' ', abstract.lower()).strip()
        return abstract
    
    def _create_author_year_journal_signature(self, article: Dict) -> str:
        """Create a signature for author + year + journal matching."""
        authors = article.get('authors', [])
        year = article.get('year', '')
        journal = article.get('journal', '')
        
        if not authors or not year or not journal:
            return ''
        
        # Use first author's last name + year + journal
        first_author = str(authors[0]).split(',')[0].split(' ')[-1].lower() if authors else ''
        year_str = str(year)
        journal_norm = re.sub(r'[^\w]', '', journal.lower())
        
        return f"{first_author}_{year_str}_{journal_norm}"
    
    def _title_similarity(self, article1: Dict, article2: Dict) -> float:
        """Calculate title similarity between two articles."""
        title1 = self._normalize_title(article1.get('title', ''))
        title2 = self._normalize_title(article2.get('title', ''))
        
        if not title1 or not title2:
            return 0.0
        
        return fuzz.ratio(title1, title2) / 100.0
    
    def _author_similarity(self, article1: Dict, article2: Dict) -> float:
        """Calculate author similarity between two articles."""
        authors1 = set(str(a).lower() for a in article1.get('authors', []))
        authors2 = set(str(a).lower() for a in article2.get('authors', []))
        
        if not authors1 or not authors2:
            return 0.0
        
        intersection = len(authors1.intersection(authors2))
        union = len(authors1.union(authors2))
        
        return intersection / union if union > 0 else 0.0
    
    def _year_match(self, article1: Dict, article2: Dict) -> bool:
        """Check if years match between two articles."""
        year1 = article1.get('year')
        year2 = article2.get('year')
        
        if not year1 or not year2:
            return False
        
        return str(year1) == str(year2)
    
    def _add_match(self, id1: str, id2: str, match_type: str, confidence: float, reason: str):
        """Add a duplicate match to the list."""
        pair_key = tuple(sorted([id1, id2]))
        if pair_key not in self.processed_pairs:
            self.matches.append(DuplicateMatch(id1, id2, match_type, confidence, reason))
            self.processed_pairs.add(pair_key)
    
    def _is_pair_processed(self, id1: str, id2: str) -> bool:
        """Check if a pair has already been processed."""
        pair_key = tuple(sorted([id1, id2]))
        return pair_key in self.processed_pairs
    
    def _generate_final_results(self, articles: List[Dict], start_time: datetime) -> Tuple[List[Dict], DeduplicationReport]:
        """Generate final deduplicated results and report."""
        # Build duplicate groups
        duplicate_groups = self._build_duplicate_groups()
        
        # Select representative articles from each group
        unique_articles = []
        articles_by_id = {art['_internal_id']: art for art in articles}
        processed_ids = set()
        
        for group in duplicate_groups:
            if not any(id in processed_ids for id in group):
                # Select the "best" representative from the group
                representative = self._select_representative(group, articles_by_id)
                unique_articles.append(representative)
                processed_ids.update(group)
        
        # Add articles that weren't part of any duplicate group
        for article in articles:
            if article['_internal_id'] not in processed_ids:
                unique_articles.append(article)
        
        # Clean up internal fields
        for article in unique_articles:
            article.pop('_internal_id', None)
        
        # Generate statistics
        matches_by_type = defaultdict(int)
        for match in self.matches:
            matches_by_type[match.match_type] += 1
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        report = DeduplicationReport(
            total_input_articles=len(articles),
            unique_articles=len(unique_articles),
            duplicates_removed=len(articles) - len(unique_articles),
            matches_by_type=dict(matches_by_type),
            duplicate_matches=self.matches,
            processing_time=processing_time
        )
        
        return unique_articles, report
    
    def _build_duplicate_groups(self) -> List[Set[str]]:
        """Build groups of duplicate articles."""
        groups = []
        id_to_group = {}
        
        for match in self.matches:
            id1, id2 = match.article1_id, match.article2_id
            
            group1 = id_to_group.get(id1)
            group2 = id_to_group.get(id2)
            
            if group1 is None and group2 is None:
                # Create new group
                new_group = {id1, id2}
                groups.append(new_group)
                id_to_group[id1] = new_group
                id_to_group[id2] = new_group
            elif group1 is not None and group2 is None:
                # Add id2 to existing group1
                group1.add(id2)
                id_to_group[id2] = group1
            elif group1 is None and group2 is not None:
                # Add id1 to existing group2
                group2.add(id1)
                id_to_group[id1] = group2
            elif group1 is not group2:
                # Merge two different groups
                merged_group = group1.union(group2)
                groups.remove(group1)
                groups.remove(group2)
                groups.append(merged_group)
                for id in merged_group:
                    id_to_group[id] = merged_group
        
        return groups
    
    def _select_representative(self, group: Set[str], articles_by_id: Dict[str, Dict]) -> Dict:
        """Select the best representative article from a duplicate group."""
        group_articles = [articles_by_id[id] for id in group]
        
        # Prioritize by: 1) Has DOI, 2) More complete metadata, 3) Source database preference
        def score_article(article):
            score = 0
            
            # Has DOI
            if article.get('doi'):
                score += 10
            
            # Complete title
            if article.get('title'):
                score += 5
            
            # Has abstract
            if article.get('abstract'):
                score += 3
            
            # Has authors
            if article.get('authors'):
                score += 2
            
            # Source database preference (Web of Science > Scopus)
            if article.get('_source_db') == 'web_of_science':
                score += 1
            
            return score
        
        return max(group_articles, key=score_article)

def load_search_results(filename: str) -> Tuple[List[Dict], List[Dict]]:
    """Load search results from JSON file and separate by database."""
    logger.info(f"Loading search results from {filename}")
    
    with open(filename, 'r') as f:
        data = json.load(f)
    
    wos_articles = data['database_results']['web_of_science']['records']
    scopus_articles = data['database_results']['scopus']['records']
    
    # Add source database tags
    for article in wos_articles:
        article['_source_db'] = 'web_of_science'
    
    for article in scopus_articles:
        article['_source_db'] = 'scopus'
    
    logger.info(f"Loaded {len(wos_articles)} WoS articles and {len(scopus_articles)} Scopus articles")
    
    return wos_articles, scopus_articles

def run_deduplication(search_results_file: str):
    """Run deduplication on search results."""
    print("="*80)
    print("DEDUPLICATION PROCESSING")
    print("="*80)
    
    # Load search results
    wos_articles, scopus_articles = load_search_results(search_results_file)
    all_articles = wos_articles + scopus_articles
    
    print(f"Input articles: {len(all_articles)} total")
    print(f"  - Web of Science: {len(wos_articles)}")
    print(f"  - Scopus: {len(scopus_articles)}")
    
    # Run deduplication
    detector = AdvancedDuplicateDetector()
    unique_articles, report = detector.detect_duplicates(all_articles)
    
    print("\n" + "="*50)
    print("DEDUPLICATION RESULTS")
    print("="*50)
    
    print(f"Total input articles: {report.total_input_articles}")
    print(f"Unique articles: {report.unique_articles}")
    print(f"Duplicates removed: {report.duplicates_removed}")
    print(f"Duplicate rate: {(report.duplicates_removed/report.total_input_articles)*100:.1f}%")
    print(f"Processing time: {report.processing_time:.2f} seconds")
    
    print(f"\nDuplicate matches by type:")
    for match_type, count in report.matches_by_type.items():
        print(f"  {match_type}: {count}")
    
    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Save unique articles
    unique_file = f"results/deduplicated_articles_{timestamp}.json"
    with open(unique_file, 'w') as f:
        json.dump({
            'unique_articles': unique_articles,
            'metadata': {
                'deduplication_date': datetime.now().isoformat(),
                'original_count': report.total_input_articles,
                'unique_count': report.unique_articles,
                'duplicates_removed': report.duplicates_removed
            }
        }, f, indent=2, default=str)
    
    # Save deduplication report
    report_file = f"results/deduplication_report_{timestamp}.json"
    with open(report_file, 'w') as f:
        json.dump(asdict(report), f, indent=2, default=str)
    
    print(f"\n📄 Results saved:")
    print(f"  Unique articles: {unique_file}")
    print(f"  Deduplication report: {report_file}")
    
    print(f"\n🎯 COMPARISON WITH REFERENCE:")
    print(f"  Reference target: 742 articles")
    print(f"  Our unique articles: {report.unique_articles}")
    print(f"  Coverage ratio: {report.unique_articles/742:.2f}x")
    
    return unique_articles, report

def main():
    """Main function."""
    # Ensure directories exist
    os.makedirs('logs', exist_ok=True)
    os.makedirs('results', exist_ok=True)
    
    # Find the most recent search results
    search_file = "results/functional_search_20250716_164537.json"
    
    if not os.path.exists(search_file):
        print(f"❌ Search results file not found: {search_file}")
        return False
    
    try:
        unique_articles, report = run_deduplication(search_file)
        print(f"\n✅ Deduplication completed successfully!")
        return True
    except Exception as e:
        print(f"\n❌ Deduplication failed: {e}")
        logger.error(f"Deduplication failed: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)