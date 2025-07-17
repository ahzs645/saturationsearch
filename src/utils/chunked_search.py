"""
Chunked search utilities for handling large location term queries.
Implements progressive enhancement and query size management.
"""

import logging
from typing import Dict, List, Set, Tuple, Optional, Any
from collections import defaultdict
import math

from .location_terms import (
    ENHANCED_NECHAKO_LOCATION_TERMS,
    generate_accent_variants,
    generate_watercourse_variants,
    canonicalize
)

logger = logging.getLogger(__name__)

# API-specific character limits
API_LIMITS = {
    "scopus": 7000,      # Scopus query limit
    "wos": 8000,         # Web of Science limit
    "zotero": 6000,      # Conservative limit for Zotero
    "default": 6000      # Default conservative limit
}

class ChunkedSearchManager:
    """
    Manages chunked search operations with progressive enhancement.
    """
    
    def __init__(self, api_type: str = "scopus", max_chunk_size: int = 50):
        self.api_type = api_type.lower()
        self.max_query_length = API_LIMITS.get(self.api_type, API_LIMITS["default"])
        self.max_chunk_size = max_chunk_size
        
    def chunk_terms_by_category(self, use_priority_terms: bool = False) -> Dict[str, List[List[str]]]:
        """
        Chunk location terms by category and size to stay under API limits.
        
        Args:
            use_priority_terms: If True, use only priority categories
            
        Returns:
            Dict mapping category names to lists of term chunks
        """
        chunks = {}
        
        if use_priority_terms:
            # Priority categories for smaller, focused searches
            priority_categories = ["watershed_terms", "rivers", "populated_places"]
            categories_to_use = {k: v for k, v in ENHANCED_NECHAKO_LOCATION_TERMS.items() 
                               if k in priority_categories}
        else:
            categories_to_use = ENHANCED_NECHAKO_LOCATION_TERMS
            
        for category, terms in categories_to_use.items():
            # Generate variants for terms to get realistic query size
            expanded_terms = []
            for term in terms:
                expanded_terms.append(term)
                # Add accent variants
                for variant in generate_accent_variants(term):
                    if variant != term and variant not in expanded_terms:
                        expanded_terms.append(variant)
                # Add watercourse variants for relevant terms
                if any(suffix in term.lower() for suffix in ["creek", "river", "brook", "stream"]):
                    for variant in generate_watercourse_variants(term):
                        if variant != term and variant not in expanded_terms:
                            expanded_terms.append(variant)
            
            # Chunk terms within the category
            category_chunks = self._chunk_terms_list(expanded_terms)
            chunks[category] = category_chunks
            
        return chunks
    
    def _chunk_terms_list(self, terms: List[str]) -> List[List[str]]:
        """
        Split a list of terms into chunks that fit within query limits.
        """
        if not terms:
            return []
            
        chunks = []
        current_chunk = []
        
        for term in terms:
            # Test if adding this term would exceed limits
            test_chunk = current_chunk + [term]
            test_query = self._build_chunk_query(test_chunk)
            
            if len(test_query) > self.max_query_length and current_chunk:
                # Current chunk is full, start a new one
                chunks.append(current_chunk)
                current_chunk = [term]
            else:
                current_chunk.append(term)
                
            # Also check if chunk size limit is reached
            if len(current_chunk) >= self.max_chunk_size:
                chunks.append(current_chunk)
                current_chunk = []
        
        # Add the last chunk if it has content
        if current_chunk:
            chunks.append(current_chunk)
            
        return chunks
    
    def _build_chunk_query(self, terms: List[str]) -> str:
        """
        Build a query string from a chunk of terms.
        """
        quoted_terms = [f'"{term}"' for term in terms]
        return " OR ".join(quoted_terms)
    
    def build_chunked_queries(self, use_priority_terms: bool = False) -> List[Tuple[str, str, List[str]]]:
        """
        Build all chunked queries ready for API execution.
        
        Returns:
            List of tuples: (category, query_string, terms_in_chunk)
        """
        chunked_categories = self.chunk_terms_by_category(use_priority_terms)
        queries = []
        
        for category, chunks in chunked_categories.items():
            for i, chunk in enumerate(chunks):
                query = self._build_chunk_query(chunk)
                chunk_id = f"{category}_chunk_{i+1}"
                queries.append((chunk_id, query, chunk))
                
        return queries
    
    def test_query_lengths(self, use_priority_terms: bool = False) -> Dict[str, Any]:
        """
        Test and report on query lengths before execution.
        
        Returns:
            Statistics about query sizes and chunking requirements
        """
        queries = self.build_chunked_queries(use_priority_terms)
        
        stats = {
            "api_type": self.api_type,
            "max_query_length": self.max_query_length,
            "total_chunks": len(queries),
            "queries": [],
            "longest_query": 0,
            "shortest_query": float('inf'),
            "average_query_length": 0,
            "queries_over_limit": 0
        }
        
        total_length = 0
        for chunk_id, query, terms in queries:
            query_length = len(query)
            total_length += query_length
            
            query_info = {
                "chunk_id": chunk_id,
                "length": query_length,
                "term_count": len(terms),
                "within_limit": query_length <= self.max_query_length,
                "sample_terms": terms[:3]  # First 3 terms as sample
            }
            stats["queries"].append(query_info)
            
            # Update statistics
            stats["longest_query"] = max(stats["longest_query"], query_length)
            stats["shortest_query"] = min(stats["shortest_query"], query_length)
            
            if query_length > self.max_query_length:
                stats["queries_over_limit"] += 1
        
        if queries:
            stats["average_query_length"] = total_length / len(queries)
        else:
            stats["shortest_query"] = 0
            
        return stats
    
    def progressive_search_query(self, base_terms: List[str], 
                                enhancement_terms: List[str]) -> Tuple[str, List[str], List[str]]:
        """
        Build query progressively until hitting character limit.
        
        Args:
            base_terms: Essential terms that must be included
            enhancement_terms: Additional terms to add if space allows
            
        Returns:
            Tuple of (final_query, included_terms, excluded_terms)
        """
        # Start with base terms
        included_terms = base_terms.copy()
        excluded_terms = []
        
        # Build base query
        current_query = self._build_chunk_query(base_terms)
        
        # Try to add enhancement terms one by one
        for term in enhancement_terms:
            test_terms = included_terms + [term]
            test_query = self._build_chunk_query(test_terms)
            
            if len(test_query) <= self.max_query_length:
                # Term fits, add it
                included_terms.append(term)
                current_query = test_query
            else:
                # Term doesn't fit, exclude it
                excluded_terms.append(term)
        
        return current_query, included_terms, excluded_terms


def chunks_of(lst: List[Any], n: int) -> List[List[Any]]:
    """
    Yield successive n-sized chunks from lst.
    """
    chunks = []
    for i in range(0, len(lst), n):
        chunks.append(lst[i:i + n])
    return chunks


def chunked_nechako_search_queries(api_type: str = "scopus", 
                                   chunk_size: int = 50,
                                   use_priority_terms: bool = False) -> List[Dict[str, Any]]:
    """
    Generate chunked search queries for Nechako watershed terms.
    
    Args:
        api_type: API type for query format and limits
        chunk_size: Maximum terms per chunk
        use_priority_terms: Whether to use only priority terms
        
    Returns:
        List of query dictionaries ready for API execution
    """
    manager = ChunkedSearchManager(api_type, chunk_size)
    chunked_queries = manager.build_chunked_queries(use_priority_terms)
    
    search_queries = []
    for chunk_id, query, terms in chunked_queries:
        search_queries.append({
            "chunk_id": chunk_id,
            "query": query,
            "terms": terms,
            "term_count": len(terms),
            "query_length": len(query),
            "api_type": api_type
        })
    
    return search_queries


def get_priority_terms() -> Dict[str, List[str]]:
    """
    Get priority terms organized by category.
    These are the most important terms for focused searches.
    """
    return {
        "watershed_terms": ENHANCED_NECHAKO_LOCATION_TERMS["watershed_terms"],
        "rivers": ENHANCED_NECHAKO_LOCATION_TERMS["rivers"][:10],  # Top 10 rivers
        "populated_places": ENHANCED_NECHAKO_LOCATION_TERMS["populated_places"][:15],  # Top 15 places
        "physiography": ENHANCED_NECHAKO_LOCATION_TERMS["physiography"][:8]  # Top 8 features
    }


def analyze_chunking_efficiency(api_type: str = "scopus", use_priority_terms: bool = False) -> Dict[str, Any]:
    """
    Analyze the efficiency of the chunking approach.
    
    Returns:
        Analysis report with recommendations
    """
    manager = ChunkedSearchManager(api_type)
    stats = manager.test_query_lengths(use_priority_terms)
    
    # Calculate efficiency metrics
    total_terms = sum(len(ENHANCED_NECHAKO_LOCATION_TERMS[cat]) for cat in 
                     (get_priority_terms().keys() if use_priority_terms else ENHANCED_NECHAKO_LOCATION_TERMS.keys()))
    
    analysis = {
        "chunking_stats": stats,
        "total_original_terms": total_terms,
        "chunks_needed": stats["total_chunks"],
        "average_terms_per_chunk": total_terms / stats["total_chunks"] if stats["total_chunks"] > 0 else 0,
        "chunking_efficiency": 1 - (stats["queries_over_limit"] / stats["total_chunks"]) if stats["total_chunks"] > 0 else 1,
        "recommendations": []
    }
    
    # Generate recommendations
    if stats["queries_over_limit"] > 0:
        analysis["recommendations"].append(
            f"⚠️  {stats['queries_over_limit']} queries exceed the {API_LIMITS[api_type]} character limit. "
            f"Consider reducing chunk size from {manager.max_chunk_size} terms."
        )
    
    if stats["average_query_length"] < API_LIMITS[api_type] * 0.7:
        analysis["recommendations"].append(
            f"✅ Average query length ({stats['average_query_length']:.0f} chars) is well under the limit. "
            f"Could potentially use larger chunks for fewer API calls."
        )
    
    if stats["total_chunks"] > 20:
        analysis["recommendations"].append(
            f"⏰ {stats['total_chunks']} chunks will require many API calls. "
            f"Consider using priority terms only for faster results."
        )
    
    return analysis


if __name__ == "__main__":
    # Test chunking functionality
    print("CHUNKED SEARCH ANALYSIS")
    print("=" * 50)
    
    # Test with different configurations
    configs = [
        ("scopus", False, "Scopus - Comprehensive"),
        ("scopus", True, "Scopus - Priority Only"),
        ("wos", False, "Web of Science - Comprehensive"),
        ("zotero", True, "Zotero - Priority Only")
    ]
    
    for api_type, use_priority, description in configs:
        print(f"\n{description}:")
        analysis = analyze_chunking_efficiency(api_type, use_priority)
        
        stats = analysis["chunking_stats"]
        print(f"  • Total chunks: {stats['total_chunks']}")
        print(f"  • Average query length: {stats['average_query_length']:.0f} chars")
        print(f"  • Queries over limit: {stats['queries_over_limit']}")
        print(f"  • Efficiency: {analysis['chunking_efficiency']:.1%}")
        
        if analysis["recommendations"]:
            print(f"  • Recommendations:")
            for rec in analysis["recommendations"]:
                print(f"    {rec}")