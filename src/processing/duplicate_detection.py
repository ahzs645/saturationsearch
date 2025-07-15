"""
Advanced duplicate detection system for literature search results.
Implements multi-level deduplication superior to DistillerSR.
"""

import logging
from typing import Dict, List, Tuple, Set, Optional
from dataclasses import dataclass
from fuzzywuzzy import fuzz
import difflib
import hashlib
import re
from collections import defaultdict

from config import TITLE_SIMILARITY_THRESHOLD, ABSTRACT_SIMILARITY_THRESHOLD

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
    5. Comparison with existing baseline articles
    """
    
    def __init__(self, 
                 title_threshold: float = TITLE_SIMILARITY_THRESHOLD,
                 abstract_threshold: float = ABSTRACT_SIMILARITY_THRESHOLD):
        """
        Initialize the duplicate detector.
        
        Args:
            title_threshold (float): Threshold for title similarity matching
            abstract_threshold (float): Threshold for abstract similarity matching
        """
        self.title_threshold = title_threshold
        self.abstract_threshold = abstract_threshold
        
    def detect_duplicates(self, 
                         articles: List[Dict],
                         baseline_articles: Optional[List[Dict]] = None) -> Tuple[List[Dict], DeduplicationReport]:
        """
        Detect and remove duplicates from a list of articles.
        
        Args:
            articles (List[Dict]): List of articles to deduplicate
            baseline_articles (List[Dict], optional): Existing baseline articles for comparison
            
        Returns:
            Tuple[List[Dict], DeduplicationReport]: Unique articles and deduplication report
        """
        import time
        start_time = time.time()
        
        logger.info(f"Starting deduplication of {len(articles)} articles")
        
        # Track all duplicate matches
        all_matches = []
        
        # Level 1: Exact identifier matches
        logger.info("Level 1: Checking exact DOI/PMID matches")
        exact_matches = self._find_exact_matches(articles)
        all_matches.extend(exact_matches)
        
        # Level 2: High-confidence title matching
        logger.info("Level 2: Checking title similarity matches")
        title_matches = self._find_title_matches(articles)
        all_matches.extend(title_matches)
        
        # Level 3: Author-year-journal matching
        logger.info("Level 3: Checking author-year-journal matches")
        author_year_matches = self._find_author_year_journal_matches(articles)
        all_matches.extend(author_year_matches)
        
        # Level 4: Abstract similarity matching
        logger.info("Level 4: Checking abstract similarity matches")
        abstract_matches = self._find_abstract_matches(articles)
        all_matches.extend(abstract_matches)
        
        # Level 5: Baseline comparison (if provided)
        baseline_matches = []
        if baseline_articles:
            logger.info("Level 5: Checking against baseline articles")
            baseline_matches = self._find_baseline_matches(articles, baseline_articles)
            all_matches.extend(baseline_matches)
        
        # Remove duplicates and generate report
        unique_articles = self._remove_duplicates(articles, all_matches)
        
        # Generate statistics
        matches_by_type = defaultdict(int)
        for match in all_matches:
            matches_by_type[match.match_type] += 1
        
        processing_time = time.time() - start_time
        
        report = DeduplicationReport(
            total_input_articles=len(articles),
            unique_articles=len(unique_articles),
            duplicates_removed=len(articles) - len(unique_articles),
            matches_by_type=dict(matches_by_type),
            duplicate_matches=all_matches,
            processing_time=processing_time
        )
        
        logger.info(f"Deduplication complete: {len(unique_articles)} unique articles from {len(articles)} input articles")
        logger.info(f"Removed {len(articles) - len(unique_articles)} duplicates in {processing_time:.2f} seconds")
        
        return unique_articles, report
    
    def _find_exact_matches(self, articles: List[Dict]) -> List[DuplicateMatch]:
        """Find articles with exact DOI or PMID matches."""
        matches = []
        
        # Build lookup dictionaries
        doi_lookup = {}
        pmid_lookup = {}
        
        for i, article in enumerate(articles):
            doi = self._clean_identifier(article.get('doi', ''))
            pmid = self._clean_identifier(article.get('pmid', ''))
            
            # Check DOI matches
            if doi:
                if doi in doi_lookup:
                    matches.append(DuplicateMatch(
                        article1_id=str(doi_lookup[doi]),
                        article2_id=str(i),
                        match_type="exact_doi",
                        confidence=1.0,
                        reason=f"Identical DOI: {doi}"
                    ))
                else:
                    doi_lookup[doi] = i
            
            # Check PMID matches
            if pmid:
                if pmid in pmid_lookup:
                    matches.append(DuplicateMatch(
                        article1_id=str(pmid_lookup[pmid]),
                        article2_id=str(i),
                        match_type="exact_pmid",
                        confidence=1.0,
                        reason=f"Identical PMID: {pmid}"
                    ))
                else:
                    pmid_lookup[pmid] = i
        
        logger.info(f"Found {len(matches)} exact identifier matches")
        return matches
    
    def _find_title_matches(self, articles: List[Dict]) -> List[DuplicateMatch]:
        """Find articles with highly similar titles."""
        matches = []
        
        for i in range(len(articles)):
            for j in range(i + 1, len(articles)):
                title1 = self._clean_title(articles[i].get('title', ''))
                title2 = self._clean_title(articles[j].get('title', ''))
                
                if not title1 or not title2:
                    continue
                
                similarity = fuzz.ratio(title1, title2) / 100.0
                
                if similarity >= self.title_threshold:
                    matches.append(DuplicateMatch(
                        article1_id=str(i),
                        article2_id=str(j),
                        match_type="title_similarity",
                        confidence=similarity,
                        reason=f"Title similarity: {similarity:.2f}",
                        similarity_score=similarity
                    ))
        
        logger.info(f"Found {len(matches)} title similarity matches")
        return matches
    
    def _find_author_year_journal_matches(self, articles: List[Dict]) -> List[DuplicateMatch]:
        """Find articles with matching author-year-journal combinations."""
        matches = []
        author_year_journal_lookup = {}
        
        for i, article in enumerate(articles):
            key = self._generate_author_year_journal_key(article)
            
            if key and key in author_year_journal_lookup:
                matches.append(DuplicateMatch(
                    article1_id=str(author_year_journal_lookup[key]),
                    article2_id=str(i),
                    match_type="author_year_journal",
                    confidence=0.9,
                    reason=f"Matching author-year-journal: {key}"
                ))
            elif key:
                author_year_journal_lookup[key] = i
        
        logger.info(f"Found {len(matches)} author-year-journal matches")
        return matches
    
    def _find_abstract_matches(self, articles: List[Dict]) -> List[DuplicateMatch]:
        """Find articles with similar abstracts."""
        matches = []
        
        # Only check articles without DOI (to avoid double-processing)
        no_doi_articles = []
        for i, article in enumerate(articles):
            if not self._clean_identifier(article.get('doi', '')):
                no_doi_articles.append((i, article))
        
        for i in range(len(no_doi_articles)):
            for j in range(i + 1, len(no_doi_articles)):
                idx1, article1 = no_doi_articles[i]
                idx2, article2 = no_doi_articles[j]
                
                abstract1 = self._clean_abstract(article1.get('abstract', ''))
                abstract2 = self._clean_abstract(article2.get('abstract', ''))
                
                if not abstract1 or not abstract2 or len(abstract1) < 50 or len(abstract2) < 50:
                    continue
                
                similarity = self._calculate_semantic_similarity(abstract1, abstract2)
                
                if similarity >= self.abstract_threshold:
                    matches.append(DuplicateMatch(
                        article1_id=str(idx1),
                        article2_id=str(idx2),
                        match_type="abstract_similarity",
                        confidence=similarity,
                        reason=f"Abstract similarity: {similarity:.2f}",
                        similarity_score=similarity
                    ))
        
        logger.info(f"Found {len(matches)} abstract similarity matches")
        return matches
    
    def _find_baseline_matches(self, articles: List[Dict], baseline_articles: List[Dict]) -> List[DuplicateMatch]:
        """Find articles that match existing baseline articles."""
        matches = []
        
        # Create efficient lookup for baseline articles
        baseline_dois = set()
        baseline_titles = {}
        
        for baseline_article in baseline_articles:
            doi = self._clean_identifier(baseline_article.get('doi', ''))
            if doi:
                baseline_dois.add(doi)
            
            title = self._clean_title(baseline_article.get('title', ''))
            if title:
                baseline_titles[title] = baseline_article
        
        # Check each new article against baseline
        for i, article in enumerate(articles):
            # Check DOI matches
            doi = self._clean_identifier(article.get('doi', ''))
            if doi and doi in baseline_dois:
                matches.append(DuplicateMatch(
                    article1_id="baseline",
                    article2_id=str(i),
                    match_type="baseline_doi_match",
                    confidence=1.0,
                    reason=f"Matches baseline article DOI: {doi}"
                ))
                continue
            
            # Check title matches
            title = self._clean_title(article.get('title', ''))
            if title:
                for baseline_title in baseline_titles.keys():
                    similarity = fuzz.ratio(title, baseline_title) / 100.0
                    if similarity >= self.title_threshold:
                        matches.append(DuplicateMatch(
                            article1_id="baseline",
                            article2_id=str(i),
                            match_type="baseline_title_match",
                            confidence=similarity,
                            reason=f"Matches baseline article title: {similarity:.2f}",
                            similarity_score=similarity
                        ))
                        break
        
        logger.info(f"Found {len(matches)} baseline matches")
        return matches
    
    def _remove_duplicates(self, articles: List[Dict], matches: List[DuplicateMatch]) -> List[Dict]:
        """Remove duplicate articles based on detected matches."""
        # Build set of article indices to remove
        indices_to_remove = set()
        
        for match in matches:
            # Always keep the first article (lower index)
            if match.article1_id != "baseline" and match.article2_id != "baseline":
                idx1 = int(match.article1_id)
                idx2 = int(match.article2_id)
                indices_to_remove.add(max(idx1, idx2))
            elif match.article1_id == "baseline":
                # Remove articles that match baseline
                indices_to_remove.add(int(match.article2_id))
        
        # Create list of unique articles
        unique_articles = []
        for i, article in enumerate(articles):
            if i not in indices_to_remove:
                unique_articles.append(article)
        
        return unique_articles
    
    def _clean_identifier(self, identifier: str) -> str:
        """Clean and normalize identifiers (DOI, PMID)."""
        if not identifier:
            return ""
        
        # Remove common prefixes and normalize
        identifier = identifier.strip().lower()
        identifier = re.sub(r'^(doi:|pmid:)', '', identifier)
        identifier = re.sub(r'^https?://.*?/', '', identifier)  # Remove URL prefixes
        
        return identifier
    
    def _clean_title(self, title: str) -> str:
        """Clean and normalize titles for comparison."""
        if not title:
            return ""
        
        # Normalize whitespace and punctuation
        title = re.sub(r'\s+', ' ', title.strip())
        title = re.sub(r'[^\w\s]', '', title)  # Remove punctuation
        title = title.lower()
        
        return title
    
    def _clean_abstract(self, abstract: str) -> str:
        """Clean and normalize abstracts for comparison."""
        if not abstract:
            return ""
        
        # Remove common prefixes
        abstract = re.sub(r'^(abstract:?|summary:?)', '', abstract, flags=re.IGNORECASE)
        
        # Normalize whitespace
        abstract = re.sub(r'\s+', ' ', abstract.strip())
        abstract = abstract.lower()
        
        return abstract
    
    def _generate_author_year_journal_key(self, article: Dict) -> str:
        """Generate a key for author-year-journal matching."""
        authors = article.get('authors', [])
        year = str(article.get('year', '')).strip()
        journal = article.get('journal', '').strip()
        
        if not authors or not year or not journal:
            return ""
        
        # Use first author's last name
        first_author = authors[0] if isinstance(authors, list) else str(authors)
        first_author_last = first_author.split(',')[0].split()[-1] if first_author else ""
        
        # Normalize journal name
        journal_normalized = re.sub(r'[^\w\s]', '', journal.lower())
        journal_normalized = re.sub(r'\s+', ' ', journal_normalized).strip()
        
        if not first_author_last or not journal_normalized:
            return ""
        
        return f"{first_author_last.lower()}_{year}_{journal_normalized}"
    
    def _calculate_semantic_similarity(self, text1: str, text2: str) -> float:
        """Calculate semantic similarity between two texts."""
        # Simple implementation using difflib
        # In production, could use more sophisticated NLP methods
        return difflib.SequenceMatcher(None, text1, text2).ratio()


def analyze_duplicate_patterns(report: DeduplicationReport) -> Dict:
    """
    Analyze patterns in duplicate detection for quality assessment.
    
    Args:
        report (DeduplicationReport): Deduplication report
        
    Returns:
        Dict: Analysis of duplicate patterns
    """
    analysis = {
        'duplicate_rate': report.duplicates_removed / report.total_input_articles if report.total_input_articles > 0 else 0,
        'most_common_match_type': max(report.matches_by_type.items(), key=lambda x: x[1])[0] if report.matches_by_type else None,
        'match_type_distribution': report.matches_by_type,
        'confidence_distribution': {},
        'high_confidence_matches': 0,
        'low_confidence_matches': 0
    }
    
    # Analyze confidence distribution
    confidences = [match.confidence for match in report.duplicate_matches]
    if confidences:
        analysis['confidence_distribution'] = {
            'mean': sum(confidences) / len(confidences),
            'min': min(confidences),
            'max': max(confidences)
        }
        
        analysis['high_confidence_matches'] = len([c for c in confidences if c >= 0.9])
        analysis['low_confidence_matches'] = len([c for c in confidences if c < 0.7])
    
    return analysis