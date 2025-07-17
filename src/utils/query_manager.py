"""
Dynamic Query Size Management System
Integrates with existing API modules to provide automatic query splitting and progressive enhancement.
"""

import logging
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass
from abc import ABC, abstractmethod

from .chunked_search import ChunkedSearchManager, API_LIMITS
from .location_terms import (
    ENHANCED_NECHAKO_LOCATION_TERMS,
    build_comprehensive_location_query,
    get_location_terms_stats
)

logger = logging.getLogger(__name__)

@dataclass
class QueryResult:
    """Result container for query operations."""
    success: bool
    query: str
    terms_used: List[str]
    terms_excluded: List[str] = None
    query_length: int = 0
    chunk_info: Dict[str, Any] = None
    error_message: str = None

class QueryStrategy(ABC):
    """Abstract base class for query strategies."""
    
    @abstractmethod
    def build_query(self, api_type: str, use_priority_terms: bool = False) -> Union[QueryResult, List[QueryResult]]:
        """Build query according to strategy."""
        pass

class DirectQueryStrategy(QueryStrategy):
    """Strategy for direct, single query approach."""
    
    def build_query(self, api_type: str, use_priority_terms: bool = False) -> QueryResult:
        """Build a single comprehensive query."""
        query = build_comprehensive_location_query(use_priority_terms)
        query_length = len(query)
        max_length = API_LIMITS.get(api_type, API_LIMITS["default"])
        
        # Extract terms from query (simplified)
        terms_used = [term.strip('"') for term in query.split(' OR ')]
        
        if query_length <= max_length:
            return QueryResult(
                success=True,
                query=query,
                terms_used=terms_used,
                query_length=query_length
            )
        else:
            return QueryResult(
                success=False,
                query=query,
                terms_used=terms_used,
                query_length=query_length,
                error_message=f"Query length ({query_length}) exceeds {api_type} limit ({max_length})"
            )

class ChunkedQueryStrategy(QueryStrategy):
    """Strategy for chunked query approach."""
    
    def __init__(self, chunk_size: int = 50):
        self.chunk_size = chunk_size
    
    def build_query(self, api_type: str, use_priority_terms: bool = False) -> List[QueryResult]:
        """Build multiple chunked queries."""
        manager = ChunkedSearchManager(api_type, self.chunk_size)
        chunked_queries = manager.build_chunked_queries(use_priority_terms)
        
        results = []
        for chunk_id, query, terms in chunked_queries:
            query_length = len(query)
            max_length = API_LIMITS.get(api_type, API_LIMITS["default"])
            
            result = QueryResult(
                success=query_length <= max_length,
                query=query,
                terms_used=terms,
                query_length=query_length,
                chunk_info={"chunk_id": chunk_id, "chunk_size": len(terms)},
                error_message=None if query_length <= max_length else 
                             f"Chunk {chunk_id} exceeds limit ({query_length} > {max_length})"
            )
            results.append(result)
        
        return results

class ProgressiveQueryStrategy(QueryStrategy):
    """Strategy for progressive enhancement approach."""
    
    def build_query(self, api_type: str, use_priority_terms: bool = False) -> QueryResult:
        """Build query with progressive enhancement."""
        manager = ChunkedSearchManager(api_type)
        
        # Define base terms (essential) and enhancement terms (nice-to-have)
        if use_priority_terms:
            base_terms = ENHANCED_NECHAKO_LOCATION_TERMS["watershed_terms"]
            enhancement_terms = (
                ENHANCED_NECHAKO_LOCATION_TERMS["rivers"][:5] +
                ENHANCED_NECHAKO_LOCATION_TERMS["populated_places"][:5]
            )
        else:
            # For comprehensive, use watershed terms + top rivers as base
            base_terms = (
                ENHANCED_NECHAKO_LOCATION_TERMS["watershed_terms"] +
                ENHANCED_NECHAKO_LOCATION_TERMS["rivers"][:3]
            )
            # All other terms as enhancements
            enhancement_terms = []
            for category, terms in ENHANCED_NECHAKO_LOCATION_TERMS.items():
                if category not in ["watershed_terms", "rivers"]:
                    enhancement_terms.extend(terms)
                elif category == "rivers":
                    enhancement_terms.extend(terms[3:])  # Skip the first 3 already in base
        
        query, included_terms, excluded_terms = manager.progressive_search_query(
            base_terms, enhancement_terms
        )
        
        return QueryResult(
            success=True,
            query=query,
            terms_used=included_terms,
            terms_excluded=excluded_terms,
            query_length=len(query),
            chunk_info={
                "strategy": "progressive",
                "base_terms_count": len(base_terms),
                "enhancement_terms_count": len(enhancement_terms),
                "included_enhancement_count": len(included_terms) - len(base_terms),
                "excluded_count": len(excluded_terms)
            }
        )

class DynamicQueryManager:
    """
    Main query manager that automatically selects the best strategy
    based on query complexity and API limitations.
    """
    
    def __init__(self):
        self.strategies = {
            "direct": DirectQueryStrategy(),
            "chunked": ChunkedQueryStrategy(),
            "progressive": ProgressiveQueryStrategy()
        }
    
    def test_query_feasibility(self, api_type: str, use_priority_terms: bool = False) -> Dict[str, Any]:
        """
        Test different strategies to determine the best approach.
        
        Returns:
            Analysis of different strategies and recommendations
        """
        analysis = {
            "api_type": api_type,
            "use_priority_terms": use_priority_terms,
            "api_limit": API_LIMITS.get(api_type, API_LIMITS["default"]),
            "strategies": {},
            "recommended_strategy": None,
            "reasoning": ""
        }
        
        # Test direct strategy
        direct_result = self.strategies["direct"].build_query(api_type, use_priority_terms)
        analysis["strategies"]["direct"] = {
            "feasible": direct_result.success,
            "query_length": direct_result.query_length,
            "term_count": len(direct_result.terms_used),
            "api_calls_needed": 1 if direct_result.success else 0
        }
        
        # Test progressive strategy
        progressive_result = self.strategies["progressive"].build_query(api_type, use_priority_terms)
        analysis["strategies"]["progressive"] = {
            "feasible": progressive_result.success,
            "query_length": progressive_result.query_length,
            "term_count": len(progressive_result.terms_used),
            "terms_excluded": len(progressive_result.terms_excluded or []),
            "api_calls_needed": 1
        }
        
        # Test chunked strategy
        chunked_results = self.strategies["chunked"].build_query(api_type, use_priority_terms)
        successful_chunks = [r for r in chunked_results if r.success]
        analysis["strategies"]["chunked"] = {
            "feasible": len(successful_chunks) == len(chunked_results),
            "total_chunks": len(chunked_results),
            "successful_chunks": len(successful_chunks),
            "api_calls_needed": len(successful_chunks),
            "total_terms": sum(len(r.terms_used) for r in successful_chunks),
            "average_query_length": sum(r.query_length for r in successful_chunks) / len(successful_chunks) if successful_chunks else 0
        }
        
        # Determine recommendation
        if direct_result.success:
            analysis["recommended_strategy"] = "direct"
            analysis["reasoning"] = "Direct query fits within API limits - simplest approach"
        elif progressive_result.success and len(progressive_result.terms_excluded or []) < 10:
            analysis["recommended_strategy"] = "progressive"
            analysis["reasoning"] = f"Progressive enhancement includes most terms ({len(progressive_result.terms_used)}) in single query"
        elif analysis["strategies"]["chunked"]["feasible"]:
            analysis["recommended_strategy"] = "chunked"
            analysis["reasoning"] = f"Chunked approach needed - {analysis['strategies']['chunked']['total_chunks']} API calls required"
        else:
            analysis["recommended_strategy"] = "progressive"  # Fallback
            analysis["reasoning"] = "API limits too restrictive - progressive enhancement with reduced terms"
        
        return analysis
    
    def build_optimal_query(self, api_type: str, use_priority_terms: bool = False, 
                           force_strategy: Optional[str] = None) -> Union[QueryResult, List[QueryResult]]:
        """
        Build the optimal query using the best strategy for the given parameters.
        
        Args:
            api_type: API type (scopus, wos, zotero, etc.)
            use_priority_terms: Whether to use only priority terms
            force_strategy: Force a specific strategy (direct, chunked, progressive)
            
        Returns:
            QueryResult or list of QueryResults depending on strategy
        """
        if force_strategy and force_strategy in self.strategies:
            strategy = force_strategy
        else:
            # Auto-select strategy
            analysis = self.test_query_feasibility(api_type, use_priority_terms)
            strategy = analysis["recommended_strategy"]
        
        logger.info(f"Using {strategy} strategy for {api_type} API")
        return self.strategies[strategy].build_query(api_type, use_priority_terms)
    
    def format_query_for_api(self, query_result: QueryResult, api_type: str, 
                            additional_filters: Optional[Dict[str, str]] = None) -> str:
        """
        Format a query result for specific API syntax.
        
        Args:
            query_result: Result from build_optimal_query
            api_type: Target API type
            additional_filters: Additional filters like date ranges, language, etc.
            
        Returns:
            Formatted query string ready for API
        """
        base_query = query_result.query
        
        # Apply API-specific formatting
        if api_type.lower() == "scopus":
            # Convert to Scopus TITLE-ABS-KEY format
            terms = [term.strip('"') for term in base_query.split(' OR ')]
            formatted_terms = [f'TITLE-ABS-KEY("{term}")' for term in terms]
            location_query = " OR ".join(formatted_terms)
            
            # Add filters
            filters = []
            if additional_filters:
                if "start_year" in additional_filters and "end_year" in additional_filters:
                    filters.append(f"PUBYEAR > {int(additional_filters['start_year'])-1}")
                    filters.append(f"PUBYEAR < {int(additional_filters['end_year'])+1}")
                if additional_filters.get("language", "").lower() == "english":
                    filters.append("LANGUAGE(english)")
                if additional_filters.get("document_types"):
                    filters.append(f"DOCTYPE({additional_filters['document_types']})")
            
            if filters:
                return f"({location_query}) AND {' AND '.join(filters)}"
            else:
                return f"({location_query})"
                
        elif api_type.lower() in ["wos", "web_of_science"]:
            # Convert to Web of Science TS format
            formatted_query = f"TS=({base_query})"
            
            # Add filters
            if additional_filters:
                if "start_year" in additional_filters and "end_year" in additional_filters:
                    formatted_query += f" AND PY=({additional_filters['start_year']}-{additional_filters['end_year']})"
                if additional_filters.get("language", "").lower() == "english":
                    formatted_query += " AND LA=(English)"
            
            return formatted_query
        
        else:
            # Default format - return as-is
            return base_query


def quick_query_test(api_type: str = "scopus", use_priority_terms: bool = False) -> None:
    """
    Quick test of query building capabilities.
    """
    print(f"\nQUICK QUERY TEST - {api_type.upper()}")
    print("=" * 50)
    
    manager = DynamicQueryManager()
    
    # Test feasibility
    analysis = manager.test_query_feasibility(api_type, use_priority_terms)
    
    print(f"API Limit: {analysis['api_limit']} characters")
    print(f"Priority Terms Only: {use_priority_terms}")
    print(f"Recommended Strategy: {analysis['recommended_strategy']}")
    print(f"Reasoning: {analysis['reasoning']}")
    
    print(f"\nStrategy Analysis:")
    for strategy, stats in analysis["strategies"].items():
        print(f"  {strategy.title()}:")
        print(f"    • Feasible: {stats['feasible']}")
        print(f"    • API calls needed: {stats.get('api_calls_needed', 'N/A')}")
        if 'query_length' in stats:
            print(f"    • Query length: {stats['query_length']} chars")
        if 'term_count' in stats:
            print(f"    • Terms included: {stats['term_count']}")
    
    # Build and show optimal query
    result = manager.build_optimal_query(api_type, use_priority_terms)
    
    if isinstance(result, list):
        print(f"\nOptimal Query (Chunked - {len(result)} chunks):")
        for i, chunk_result in enumerate(result[:2]):  # Show first 2 chunks
            print(f"  Chunk {i+1}: {chunk_result.query_length} chars, {len(chunk_result.terms_used)} terms")
            if i < 1:  # Show query for first chunk only
                print(f"    Query: {chunk_result.query[:100]}...")
    else:
        print(f"\nOptimal Query ({analysis['recommended_strategy']}):")
        print(f"  Length: {result.query_length} chars")
        print(f"  Terms: {len(result.terms_used)}")
        if result.terms_excluded:
            print(f"  Excluded: {len(result.terms_excluded)} terms")
        print(f"  Query: {result.query[:150]}...")


if __name__ == "__main__":
    # Test different API configurations
    test_configs = [
        ("scopus", True),
        ("scopus", False),
        ("wos", True),
        ("zotero", True)
    ]
    
    for api_type, priority_only in test_configs:
        quick_query_test(api_type, priority_only)