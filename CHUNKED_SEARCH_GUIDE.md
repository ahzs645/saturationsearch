# Chunked Search Implementation Guide

## Overview

This implementation provides smart query management for the Nechako Watershed saturation search system, automatically handling large location term databases that exceed API character limits.

## Key Features

### 1. **Automatic Query Strategy Selection**
- **Direct Query**: When all terms fit within API limits (fastest)
- **Progressive Enhancement**: Builds queries incrementally until hitting limits (balanced)
- **Chunked Search**: Splits queries into multiple API calls (comprehensive)

### 2. **API-Specific Optimization**
- **Scopus**: 7,000 character limit with TITLE-ABS-KEY formatting
- **Web of Science**: 8,000 character limit with TS= formatting  
- **Zotero**: 6,000 character conservative limit
- **Auto-detection**: System automatically selects optimal strategy per API

### 3. **Smart Term Management**
- **Priority Terms**: 206 high-impact terms (watershed_terms, top rivers, major places)
- **Comprehensive Terms**: 1,591+ terms including all creeks, lakes, physiography
- **Variant Generation**: Automatic accent variants and watercourse synonyms

## Quick Start

### Basic Usage

```bash
# Analyze optimal strategy for Scopus with priority terms
python scripts/search/smart_search.py --analyze-only --api scopus --priority

# Compare strategies across all APIs
python scripts/search/smart_search.py --compare --priority

# Execute smart search (dry run by default)
python scripts/search/smart_search.py --api scopus --priority

# Execute actual search
python scripts/search/smart_search.py --api scopus --priority --execute
```

### Advanced Usage

```bash
# Force chunked strategy for comprehensive coverage
python scripts/search/smart_search.py --api scopus --strategy chunked --execute

# Progressive enhancement for balanced approach
python scripts/search/smart_search.py --api scopus --strategy progressive --execute

# Run across all available APIs
python scripts/search/smart_search.py --api all --priority --execute
```

## Implementation Details

### Query Strategy Decision Tree

1. **Priority Terms (Fast Option)**
   - 206 terms → ~3,789 characters
   - ✅ **Recommended**: Direct query for all APIs
   - **Result**: Single API call, high-impact terms only

2. **Comprehensive Terms (Complete Option)**  
   - 1,591+ terms → ~30,285 characters
   - ⚠️ **Too Large**: Exceeds all API limits
   - **Auto-Selected Strategy**:
     - **Scopus/WoS**: Chunked (38 API calls)
     - **Alternative**: Progressive enhancement (370 terms in 1 call)

### Category-Based Chunking

The system chunks terms by category and size:

```python
# Category priorities for chunking
categories = [
    "watershed_terms",    # 8 terms - highest priority
    "rivers",            # 24 terms - major watercourses  
    "populated_places",  # 48 terms - cities and towns
    "physiography",      # 35 terms - mountains, plateaus
    "creeks",           # 244 terms - chunked by size
    "lakes",            # 140+ terms - chunked by size
    # ... other categories
]
```

### Query Length Analysis

| API | Limit | Priority Query | Comprehensive Query | Strategy |
|-----|-------|---------------|---------------------|----------|
| Scopus | 7,000 chars | 3,789 chars ✅ | 30,285 chars ❌ | Direct → Chunked |
| Web of Science | 8,000 chars | 3,789 chars ✅ | 30,285 chars ❌ | Direct → Chunked |
| Zotero | 6,000 chars | 3,789 chars ✅ | 30,285 chars ❌ | Direct → Chunked |

## Progressive Enhancement Details

When using progressive enhancement, the system:

1. **Starts with base terms** (essential watershed identifiers)
2. **Adds enhancement terms** one by one until hitting character limit
3. **Reports what was included/excluded** for transparency

Example progressive query build:
```
Base terms: ["Nechako", "Nechako Watershed", "Fraser River"] → 337 chars
+ Enhancement: Adding rivers, places, physiography...
Final query: 370 terms, 7,000 chars (Scopus limit reached)
Excluded: 1,221 terms (mostly creeks and lakes)
```

## Performance Recommendations

### For Speed (Research/Exploration)
```bash
# Use priority terms - single API call
python scripts/search/smart_search.py --api scopus --priority --execute
```
- **Result**: ~3,800 characters, 206 terms, 1 API call
- **Coverage**: High-impact locations, major rivers, key places

### For Completeness (Final Search)
```bash
# Use chunked approach - comprehensive coverage
python scripts/search/smart_search.py --api scopus --strategy chunked --execute
```
- **Result**: 38 API calls, 1,591+ terms, complete coverage
- **Coverage**: Every creek, lake, physiographic feature

### For Balance (Most Common)
```bash
# Use progressive enhancement - automatic optimization
python scripts/search/smart_search.py --api scopus --strategy progressive --execute
```
- **Result**: 1 API call, 370 terms, 7,000 characters
- **Coverage**: All priority terms + as many others as fit

## Integration with Existing APIs

The chunked search system integrates seamlessly with existing API modules:

### Scopus Integration
```python
from src.utils.query_manager import DynamicQueryManager

manager = DynamicQueryManager()
query_result = manager.build_optimal_query("scopus", use_priority_terms=True)
formatted_query = manager.format_query_for_api(query_result, "scopus")

# Use with existing ScopusHybridAPI
api = ScopusHybridAPI()
results = api.search_articles(formatted_query)
```

### Custom Implementation
```python
from src.utils.chunked_search import ChunkedSearchManager

# Create chunked queries manually
manager = ChunkedSearchManager("scopus", chunk_size=50)
queries = manager.build_chunked_queries(use_priority_terms=False)

for chunk_id, query, terms in queries:
    print(f"Chunk {chunk_id}: {len(query)} chars, {len(terms)} terms")
    # Execute each chunk with your API client
```

## Deduplication Strategy

The system handles overlapping terms across categories:

- **Total raw terms**: 620+ across 9 categories
- **Unique canonical terms**: ~580 (accounting for duplicates)
- **Variant generation**: Accent variants, watercourse synonyms
- **Final expanded set**: 1,591+ searchable terms

## Error Handling

The system includes robust error handling:

1. **Query too long**: Automatic chunking or progressive fallback
2. **API unavailable**: Graceful degradation, continue with available APIs
3. **Empty results**: Logged warnings, execution continues
4. **Rate limiting**: Built-in delays between chunked API calls

## Monitoring and Analysis

### Query Analysis Tools
```bash
# Test query lengths without executing
python -m src.utils.chunked_search

# Analyze efficiency across APIs  
python -m src.utils.query_manager

# Full comparison analysis
python scripts/search/smart_search.py --compare
```

### Performance Metrics
- **Chunking efficiency**: Percentage of queries within API limits
- **Term coverage**: How many location terms included
- **API call count**: Total requests needed
- **Execution time**: End-to-end search duration

## Best Practices

1. **Start with priority terms** for exploration and validation
2. **Use progressive enhancement** for balanced coverage
3. **Reserve chunked searches** for final comprehensive searches
4. **Monitor API rate limits** when using chunked approach
5. **Test query strategies** before executing large searches
6. **Review excluded terms** in progressive enhancement

## Troubleshooting

### Common Issues

1. **"Query too long" errors**
   - Solution: System should auto-chunk, check force_strategy parameter

2. **Too many API calls**
   - Solution: Use priority terms or progressive enhancement

3. **Missing API modules**
   - Solution: Check imports, some APIs may not be configured

4. **Empty results**
   - Solution: Review query formatting for specific API requirements

### Debug Commands
```bash
# Check what terms are being generated
python -c "from src.utils.location_terms import get_location_terms_stats; print(get_location_terms_stats())"

# Analyze specific API strategy
python scripts/search/smart_search.py --analyze-only --api scopus

# Test chunking without execution
python scripts/search/smart_search.py --api scopus --priority  # dry run by default
```

## Configuration

The system uses these configuration parameters:

```python
# API character limits (in src/utils/chunked_search.py)
API_LIMITS = {
    "scopus": 7000,
    "wos": 8000, 
    "zotero": 6000,
    "default": 6000
}

# Chunking parameters
max_chunk_size = 50  # Maximum terms per chunk
```

Adjust these values based on your specific API limits and performance requirements.