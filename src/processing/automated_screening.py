"""
Automated screening and classification system for literature search results.
Replaces manual DistillerSR screening with automated inclusion/exclusion criteria.
"""

import logging
import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
import pickle

from ..utils.location_terms import is_nechako_relevant, count_location_matches
from config import CONFIDENCE_THRESHOLD, MANUAL_REVIEW_THRESHOLD, THEMES, UNBC_EXCLUSION_KEYWORDS

logger = logging.getLogger(__name__)

class ScreeningResult(Enum):
    """Screening decision outcomes."""
    INCLUDED = "included"
    EXCLUDED = "excluded"
    MANUAL_REVIEW = "manual_review"

class Theme(Enum):
    """Article theme classifications."""
    ENVIRONMENT = "Environment"
    COMMUNITY = "Community"
    HEALTH = "Health"
    UNKNOWN = "Unknown"

@dataclass
class ScreeningDecision:
    """Result of automated screening for a single article."""
    article_id: str
    decision: ScreeningResult
    theme: Optional[Theme]
    confidence_score: float
    inclusion_reasons: List[str]
    exclusion_reasons: List[str]
    geographic_relevance_score: float
    location_matches: Dict
    manual_review_reasons: List[str]

@dataclass
class ScreeningReport:
    """Summary report of screening process."""
    total_articles: int
    included_articles: int
    excluded_articles: int
    manual_review_articles: int
    theme_distribution: Dict[str, int]
    exclusion_reasons: Dict[str, int]
    average_confidence: float
    processing_time: float

class AutomatedScreener:
    """
    Automated screening system that applies inclusion/exclusion criteria.
    
    Implements the exact screening criteria from the original methodology:
    - English language only
    - Geographic relevance to Nechako Watershed
    - Date range compliance (1930-present)
    - UNBC exclusion criteria
    - Theme classification
    """
    
    def __init__(self):
        """Initialize the automated screener."""
        self.theme_classifier = None
        self.vectorizer = None
        self._download_nltk_data()
        
    def _download_nltk_data(self):
        """Download required NLTK data."""
        try:
            nltk.download('punkt', quiet=True)
            nltk.download('stopwords', quiet=True)
        except Exception as e:
            logger.warning(f"Failed to download NLTK data: {e}")
    
    def screen_articles(self, articles: List[Dict]) -> Tuple[List[ScreeningDecision], ScreeningReport]:
        """
        Screen a list of articles using automated criteria.
        
        Args:
            articles (List[Dict]): Articles to screen
            
        Returns:
            Tuple[List[ScreeningDecision], ScreeningReport]: Screening decisions and summary report
        """
        import time
        start_time = time.time()
        
        logger.info(f"Starting automated screening of {len(articles)} articles")
        
        decisions = []
        theme_counts = {theme.value: 0 for theme in Theme}
        exclusion_counts = {}
        
        for i, article in enumerate(articles):
            decision = self._screen_single_article(article, str(i))
            decisions.append(decision)
            
            # Update statistics
            if decision.theme:
                theme_counts[decision.theme.value] += 1
            
            for reason in decision.exclusion_reasons:
                exclusion_counts[reason] = exclusion_counts.get(reason, 0) + 1
        
        # Generate summary statistics
        included_count = len([d for d in decisions if d.decision == ScreeningResult.INCLUDED])
        excluded_count = len([d for d in decisions if d.decision == ScreeningResult.EXCLUDED])
        manual_review_count = len([d for d in decisions if d.decision == ScreeningResult.MANUAL_REVIEW])
        
        confidences = [d.confidence_score for d in decisions]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        processing_time = time.time() - start_time
        
        report = ScreeningReport(
            total_articles=len(articles),
            included_articles=included_count,
            excluded_articles=excluded_count,
            manual_review_articles=manual_review_count,
            theme_distribution=theme_counts,
            exclusion_reasons=exclusion_counts,
            average_confidence=avg_confidence,
            processing_time=processing_time
        )
        
        logger.info(f"Screening complete: {included_count} included, {excluded_count} excluded, {manual_review_count} manual review")
        logger.info(f"Processing time: {processing_time:.2f} seconds")
        
        return decisions, report
    
    def _screen_single_article(self, article: Dict, article_id: str) -> ScreeningDecision:
        """
        Screen a single article against inclusion/exclusion criteria.
        
        Args:
            article (Dict): Article to screen
            article_id (str): Article identifier
            
        Returns:
            ScreeningDecision: Screening decision
        """
        inclusion_reasons = []
        exclusion_reasons = []
        manual_review_reasons = []
        
        # Extract article text for analysis
        title = article.get('title', '')
        abstract = article.get('abstract', '')
        combined_text = f"{title} {abstract}"
        
        # 1. Language check (English only)
        if not self._is_english(combined_text):
            exclusion_reasons.append("Non-English language")
            return ScreeningDecision(
                article_id=article_id,
                decision=ScreeningResult.EXCLUDED,
                theme=None,
                confidence_score=0.95,
                inclusion_reasons=inclusion_reasons,
                exclusion_reasons=exclusion_reasons,
                geographic_relevance_score=0.0,
                location_matches={},
                manual_review_reasons=manual_review_reasons
            )
        
        # 2. Date range check (1930-present)
        year = article.get('year', '')
        if year and self._is_valid_year(year):
            if int(year) < 1930:
                exclusion_reasons.append(f"Publication year {year} before 1930")
            else:
                inclusion_reasons.append(f"Valid publication year: {year}")
        else:
            manual_review_reasons.append("Invalid or missing publication year")
        
        # 3. Geographic relevance check
        is_relevant, geo_score, location_matches = is_nechako_relevant(combined_text)
        
        if is_relevant:
            inclusion_reasons.append(f"Geographic relevance score: {geo_score:.2f}")
            inclusion_reasons.append(f"Location matches: {location_matches['total']}")
        else:
            if geo_score < 0.1:
                exclusion_reasons.append("No Nechako Watershed location terms found")
            else:
                manual_review_reasons.append(f"Low geographic relevance: {geo_score:.2f}")
        
        # 4. UNBC exclusion check
        if self._check_unbc_exclusion(combined_text):
            exclusion_reasons.append("UNBC non-Nechako research (timber engineering, astronomy, etc.)")
        
        # 5. Additional quality checks
        if len(combined_text.strip()) < 50:
            manual_review_reasons.append("Very short title/abstract")
        
        # Calculate overall confidence score
        confidence_score = self._calculate_confidence_score(
            is_relevant, geo_score, location_matches, 
            len(inclusion_reasons), len(exclusion_reasons), len(combined_text)
        )
        
        # Make screening decision
        if exclusion_reasons:
            decision = ScreeningResult.EXCLUDED
            theme = None
        elif confidence_score >= CONFIDENCE_THRESHOLD and is_relevant:
            decision = ScreeningResult.INCLUDED
            theme = self._classify_theme(combined_text)
        else:
            decision = ScreeningResult.MANUAL_REVIEW
            theme = self._classify_theme(combined_text) if is_relevant else None
            if confidence_score < MANUAL_REVIEW_THRESHOLD:
                manual_review_reasons.append(f"Low confidence score: {confidence_score:.2f}")
        
        return ScreeningDecision(
            article_id=article_id,
            decision=decision,
            theme=theme,
            confidence_score=confidence_score,
            inclusion_reasons=inclusion_reasons,
            exclusion_reasons=exclusion_reasons,
            geographic_relevance_score=geo_score,
            location_matches=location_matches,
            manual_review_reasons=manual_review_reasons
        )
    
    def _is_english(self, text: str) -> bool:
        """
        Determine if text is in English.
        
        Args:
            text (str): Text to analyze
            
        Returns:
            bool: True if text appears to be English
        """
        if not text.strip():
            return False
        
        # Simple heuristic: check for common English words
        english_indicators = [
            'the', 'and', 'or', 'of', 'in', 'to', 'a', 'is', 'that', 'for',
            'with', 'as', 'by', 'on', 'from', 'this', 'study', 'research',
            'analysis', 'results', 'data', 'water', 'river', 'lake'
        ]
        
        text_lower = text.lower()
        english_word_count = sum(1 for word in english_indicators if word in text_lower)
        
        # If we find at least 3 common English words, assume it's English
        return english_word_count >= 3
    
    def _is_valid_year(self, year_str: str) -> bool:
        """Check if year string represents a valid year."""
        try:
            year = int(year_str)
            return 1900 <= year <= 2030
        except (ValueError, TypeError):
            return False
    
    def _check_unbc_exclusion(self, text: str) -> bool:
        """
        Check if article should be excluded based on UNBC non-Nechako criteria.
        
        Args:
            text (str): Article text to check
            
        Returns:
            bool: True if should be excluded
        """
        text_lower = text.lower()
        
        # Check for UNBC exclusion keywords
        for keyword in UNBC_EXCLUSION_KEYWORDS:
            if keyword.lower() in text_lower:
                # Also check if it's NOT related to Nechako
                nechako_terms = ['nechako', 'stuart lake', 'fraser lake', 'vanderhoof']
                has_nechako_context = any(term in text_lower for term in nechako_terms)
                
                if not has_nechako_context:
                    return True
        
        return False
    
    def _classify_theme(self, text: str) -> Theme:
        """
        Classify article theme based on content.
        
        Args:
            text (str): Article text
            
        Returns:
            Theme: Classified theme
        """
        if self.theme_classifier is not None:
            # Use trained classifier if available
            try:
                prediction = self.theme_classifier.predict([text])[0]
                return Theme(prediction)
            except Exception as e:
                logger.warning(f"Theme classification failed: {e}")
        
        # Fallback to keyword-based classification
        return self._classify_theme_by_keywords(text)
    
    def _classify_theme_by_keywords(self, text: str) -> Theme:
        """
        Classify theme using keyword matching.
        
        Args:
            text (str): Article text
            
        Returns:
            Theme: Classified theme
        """
        text_lower = text.lower()
        
        # Environment keywords
        environment_keywords = [
            'water quality', 'ecosystem', 'habitat', 'fish', 'salmon', 'trout',
            'pollution', 'contamination', 'sediment', 'temperature', 'flow',
            'hydrology', 'watershed', 'stream', 'river', 'lake', 'wetland',
            'biodiversity', 'species', 'environmental', 'ecology', 'conservation'
        ]
        
        # Community keywords
        community_keywords = [
            'first nations', 'indigenous', 'aboriginal', 'community', 'cultural',
            'traditional', 'social', 'economic', 'development', 'land use',
            'resource management', 'stakeholder', 'governance', 'policy',
            'treaty', 'consultation', 'capacity building', 'employment'
        ]
        
        # Health keywords
        health_keywords = [
            'health', 'disease', 'mortality', 'survival', 'growth', 'reproduction',
            'toxicity', 'contamination', 'mercury', 'heavy metals', 'pathogen',
            'stress', 'biomarker', 'epidemiology', 'public health', 'exposure'
        ]
        
        # Count keyword matches
        env_score = sum(1 for keyword in environment_keywords if keyword in text_lower)
        comm_score = sum(1 for keyword in community_keywords if keyword in text_lower)
        health_score = sum(1 for keyword in health_keywords if keyword in text_lower)
        
        # Determine theme based on highest score
        scores = {'Environment': env_score, 'Community': comm_score, 'Health': health_score}
        max_theme = max(scores.keys(), key=lambda k: scores[k])
        
        if scores[max_theme] > 0:
            return Theme(max_theme)
        else:
            return Theme.UNKNOWN
    
    def _calculate_confidence_score(self, 
                                  is_relevant: bool,
                                  geo_score: float,
                                  location_matches: Dict,
                                  inclusion_reasons_count: int,
                                  exclusion_reasons_count: int,
                                  text_length: int) -> float:
        """
        Calculate confidence score for screening decision.
        
        Args:
            is_relevant (bool): Geographic relevance
            geo_score (float): Geographic relevance score
            location_matches (Dict): Location term matches
            inclusion_reasons_count (int): Number of inclusion reasons
            exclusion_reasons_count (int): Number of exclusion reasons
            text_length (int): Length of article text
            
        Returns:
            float: Confidence score (0.0 to 1.0)
        """
        if exclusion_reasons_count > 0:
            return 0.95  # High confidence in exclusion
        
        if not is_relevant:
            return 0.2  # Low confidence if not geographically relevant
        
        confidence = 0.3  # Base confidence
        
        # Geographic relevance contribution (40% of score)
        confidence += geo_score * 0.4
        
        # Location matches contribution (20% of score)
        if location_matches['total'] > 0:
            location_bonus = min(location_matches['total'] * 0.05, 0.2)
            confidence += location_bonus
        
        # Text quality contribution (10% of score)
        if text_length > 200:
            confidence += 0.1
        elif text_length > 100:
            confidence += 0.05
        
        return min(confidence, 1.0)
    
    def train_theme_classifier(self, training_articles: List[Dict]):
        """
        Train theme classifier on existing labeled articles.
        
        Args:
            training_articles (List[Dict]): Articles with theme labels for training
        """
        logger.info(f"Training theme classifier on {len(training_articles)} articles")
        
        try:
            # Prepare training data
            texts = []
            labels = []
            
            for article in training_articles:
                title = article.get('title', '')
                abstract = article.get('abstract', '')
                combined_text = f"{title} {abstract}"
                
                theme = article.get('theme', '')
                if combined_text.strip() and theme in [t.value for t in Theme]:
                    texts.append(combined_text)
                    labels.append(theme)
            
            if len(texts) < 10:
                logger.warning("Insufficient training data for theme classifier")
                return
            
            # Create and train pipeline
            self.theme_classifier = Pipeline([
                ('tfidf', TfidfVectorizer(max_features=1000, stop_words='english')),
                ('classifier', MultinomialNB())
            ])
            
            self.theme_classifier.fit(texts, labels)
            
            logger.info("Theme classifier training completed")
            
        except Exception as e:
            logger.error(f"Theme classifier training failed: {e}")
            self.theme_classifier = None
    
    def save_classifier(self, filepath: str):
        """Save trained classifier to file."""
        if self.theme_classifier is not None:
            with open(filepath, 'wb') as f:
                pickle.dump(self.theme_classifier, f)
            logger.info(f"Classifier saved to {filepath}")
    
    def load_classifier(self, filepath: str):
        """Load trained classifier from file."""
        try:
            with open(filepath, 'rb') as f:
                self.theme_classifier = pickle.load(f)
            logger.info(f"Classifier loaded from {filepath}")
        except Exception as e:
            logger.error(f"Failed to load classifier: {e}")


def generate_screening_summary(decisions: List[ScreeningDecision]) -> Dict:
    """
    Generate detailed summary of screening results.
    
    Args:
        decisions (List[ScreeningDecision]): List of screening decisions
        
    Returns:
        Dict: Summary statistics and insights
    """
    included = [d for d in decisions if d.decision == ScreeningResult.INCLUDED]
    excluded = [d for d in decisions if d.decision == ScreeningResult.EXCLUDED]
    manual_review = [d for d in decisions if d.decision == ScreeningResult.MANUAL_REVIEW]
    
    # Theme distribution for included articles
    theme_dist = {}
    for decision in included:
        theme = decision.theme.value if decision.theme else 'Unknown'
        theme_dist[theme] = theme_dist.get(theme, 0) + 1
    
    # Top exclusion reasons
    exclusion_reasons = {}
    for decision in excluded:
        for reason in decision.exclusion_reasons:
            exclusion_reasons[reason] = exclusion_reasons.get(reason, 0) + 1
    
    # Geographic relevance statistics
    geo_scores = [d.geographic_relevance_score for d in decisions if d.geographic_relevance_score > 0]
    
    return {
        'screening_summary': {
            'total_articles': len(decisions),
            'included': len(included),
            'excluded': len(excluded),
            'manual_review': len(manual_review),
            'inclusion_rate': len(included) / len(decisions) if decisions else 0
        },
        'theme_distribution': theme_dist,
        'top_exclusion_reasons': dict(sorted(exclusion_reasons.items(), key=lambda x: x[1], reverse=True)[:5]),
        'geographic_relevance': {
            'mean_score': sum(geo_scores) / len(geo_scores) if geo_scores else 0,
            'articles_with_location_matches': len([d for d in decisions if d.location_matches.get('total', 0) > 0])
        },
        'quality_metrics': {
            'high_confidence_decisions': len([d for d in decisions if d.confidence_score >= 0.8]),
            'low_confidence_decisions': len([d for d in decisions if d.confidence_score < 0.6]),
            'average_confidence': sum(d.confidence_score for d in decisions) / len(decisions) if decisions else 0
        }
    }