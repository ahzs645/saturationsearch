# AI Assistant Instructions: Automated Nechako Saturation Search Implementation

## Context for AI Assistant

I need you to help me implement an automated literature search system that replicates my existing manual "saturation search" methodology for the Nechako Watershed. The system should:

1. **Replicate existing methodology** that found 748 articles (1930-2022)
2. **Automate for recurrent use** (quarterly/annually) 
3. **Eliminate DistillerSR dependency** 
4. **Output to organized Zotero library**
5. **Optionally upload to web portal**

## Step 1: Extract and Organize Search Terms

**Task:** Help me extract all location terms from my search documents and organize them into a searchable database.

**Your Instructions:**
1. **Parse my search term documents** to extract:
   - **Lakes**: ~200+ lake names (e.g., "Takla Lake", "Ootsa Lake", "Stuart Lake")
   - **Rivers/Creeks**: ~150+ waterway names (e.g., "Nechako River", "Stuart River") 
   - **Communities**: First Nations communities (e.g., "Tl'azt'en", "Nak'azdli")
   - **Cities/Towns**: (e.g., "Burns Lake", "Fort St. James", "Vanderhoof")

2. **Create structured data format:**
```python
location_terms = {
    "lakes": ["Takla Lake", "Ootsa Lake", "Stuart Lake", ...],
    "rivers": ["Nechako River", "Stuart River", "Tachie River", ...],
    "communities": ["Tl'azt'en", "Nak'azdli", "Stellat'en", ...],
    "cities": ["Burns Lake", "Fort St. James", "Vanderhoof", ...]
}
```

3. **Build Boolean query constructor:**
```python
def build_location_query(location_terms):
    """Build Web of Science compatible boolean query"""
    all_terms = []
    for category, terms in location_terms.items():
        for term in terms:
            all_terms.append(f'"{term}"')
    
    return " OR ".join(all_terms)
```

**Expected Output:** Python script that loads location terms and builds search queries.

## Step 2: Set Up Database API Connections

**Task:** Help me set up API connections to replicate my exact search methodology.

**Your Instructions:**

1. **Web of Science API Setup:**
```python
import requests

class WebOfScienceAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.clarivate.com/apis/wos-starter/v1"
    
    def search(self, query, date_start="1930-01-01", date_end=None):
        """
        Replicate the exact WoS search:
        Search 1: (all location terms)
        Search 2: ("Canada" OR "British Columbia") 
        Search 3: Search 1 AND Search 2
        """
        if date_end is None:
            date_end = datetime.now().strftime("%Y-%m-%d")
        
        # Build the exact query structure from original research
        location_query = build_location_query(location_terms)
        geographic_filter = '("Canada" OR "British Columbia")'
        full_query = f"({location_query}) AND {geographic_filter}"
        
        params = {
            "databaseId": "WOS",
            "usrQuery": full_query,
            "count": 100,
            "firstRecord": 1,
            "lang": "en",
            "timeSpan": f"{date_start}+{date_end}"
        }
        
        # Execute search and handle pagination
        return self._execute_search(params)
```

2. **Additional Database APIs:**
   - Set up Scopus API connection
   - Set up Science Direct API (if available)
   - Create fallback web scraping for Academic Search Complete

**Expected Output:** Working API classes that can execute the exact searches from my original methodology.

## Step 3: Implement Advanced Duplicate Detection

**Task:** Create duplicate detection system superior to DistillerSR.

**Your Instructions:**

1. **Multi-level deduplication algorithm:**
```python
import difflib
from fuzzywuzzy import fuzz

def advanced_duplicate_detection(articles):
    """
    Implement 5-level duplicate detection:
    1. Exact DOI/PMID matches
    2. High-confidence title matching (95%+)
    3. Author + Year + Journal combinations  
    4. Abstract semantic similarity
    5. Comparison with existing 748 baseline articles
    """
    
    duplicates_found = {
        'exact_matches': [],
        'title_matches': [],
        'author_year_matches': [],
        'abstract_matches': [],
        'baseline_matches': []
    }
    
    # Level 1: Exact identifier matches
    seen_dois = set()
    seen_pmids = set()
    
    # Level 2: Fuzzy title matching
    def title_similarity(title1, title2):
        return fuzz.ratio(title1.lower().strip(), title2.lower().strip())
    
    # Level 3: Author-year-journal matching
    def author_year_key(article):
        authors = article.get('authors', [''])
        year = article.get('year', '')
        journal = article.get('journal', '')
        return f"{authors[0]}_{year}_{journal}"
    
    # Implement full deduplication logic
    return unique_articles, duplicates_found
```

2. **Validation against my 748 baseline:**
```python
def validate_against_baseline(new_articles, baseline_748_articles):
    """
    Compare new search results against my known 748 articles
    to ensure we're not missing anything and identify truly new articles
    """
    matches = []
    new_articles_only = []
    
    # Compare against baseline and flag matches
    return matches, new_articles_only
```

**Expected Output:** Robust deduplication system with detailed reporting on what duplicates were found and why.

## Step 4: Automate Screening and Classification

**Task:** Replace manual DistillerSR screening with automated system based on my criteria.

**Your Instructions:**

1. **Implement my exact inclusion/exclusion criteria:**
```python
def automated_screening(article):
    """
    Apply my exact screening criteria:
    
    INCLUSION:
    - English language
    - Date range: 1930-present  
    - Conducted within/about Nechako Watershed
    - Focus on populations in watershed
    
    EXCLUSION:
    - Non-English
    - Outside geographic scope
    - UNBC research not specific to Nechako (timber engineering, astronomy)
    """
    
    screening_result = {
        'included': False,
        'confidence_score': 0.0,
        'reasons': [],
        'theme': None,  # Environment/Community/Health
        'manual_review_needed': False
    }
    
    # Language check
    if not is_english(article):
        screening_result['reasons'].append('Non-English')
        return screening_result
    
    # Geographic relevance
    geographic_score = calculate_geographic_relevance(article)
    if geographic_score < 0.3:
        screening_result['reasons'].append('Outside geographic scope')
        return screening_result
    
    # UNBC exclusion check
    if is_unbc_non_nechako(article):
        screening_result['reasons'].append('UNBC non-Nechako research')
        return screening_result
    
    # If passed all checks
    screening_result['included'] = True
    screening_result['theme'] = classify_theme(article)
    screening_result['confidence_score'] = calculate_confidence(article)
    
    # Flag for manual review if confidence is low
    if screening_result['confidence_score'] < 0.8:
        screening_result['manual_review_needed'] = True
    
    return screening_result
```

2. **Theme classification (Environment/Community/Health):**
```python
def classify_theme(article):
    """
    Classify articles into my three main themes based on
    title, abstract, and keywords analysis
    """
    # Use keyword matching and ML classification
    # trained on my existing 748 articles
    pass
```

**Expected Output:** Automated screening system that applies my exact criteria with confidence scoring.

## Step 5: Zotero Integration

**Task:** Set up direct integration with Zotero API to organize results exactly like my current structure.

**Your Instructions:**

1. **Zotero API setup:**
```python
from pyzotero import zotero

class ZoteroManager:
    def __init__(self, library_id, api_key):
        self.zot = zotero.Zotero(library_id, 'group', api_key)
    
    def create_search_collection(self, search_date):
        """
        Create organized collection structure:
        - SearchResultsYYYYMM (for this search)
        - Manual Review Queue (uncertain articles)
        - Excluded Articles (for reference)
        """
        collection_name = f"SearchResults{search_date.strftime('%Y%m')}"
        return self.zot.create_collection({'name': collection_name})
    
    def upload_articles(self, articles, collection_id):
        """
        Upload processed articles with proper metadata
        """
        for article in articles:
            # Clean and standardize metadata
            zotero_item = convert_to_zotero_format(article)
            
            # Add tags for theme and search info
            zotero_item['tags'] = [
                {'tag': article['theme']}, 
                {'tag': 'Saturation Search'},
                {'tag': f'Search{datetime.now().strftime("%Y%m")}'}
            ]
            
            # Upload to Zotero
            self.zot.create_item(zotero_item, collection_id)
```

2. **Maintain my existing organization:**
```python
# Replicate my current Zotero structure
def organize_zotero_library():
    collections = {
        "SearchResults202407": "Latest search results",
        "On Portal": "Articles already uploaded to portal", 
        "Manual Review Queue": "Articles needing human review",
        "Large Lake Monitoring": "Special LLMS documents",
        "Excluded Articles": "For reference and learning"
    }
    return collections
```

**Expected Output:** Seamless Zotero integration that maintains my exact organizational structure.

## Step 6: Validation and Testing

**Task:** Create validation system to ensure the automated approach matches my original results.

**Your Instructions:**

1. **Retrospective validation:**
```python
def validate_methodology():
    """
    Run automated search for 1930-2022 period and compare 
    against my known 748 articles
    """
    
    # Execute full search with original parameters
    automated_results = run_full_search("1930-01-01", "2022-12-31")
    
    # Compare against my 748 baseline
    baseline_articles = load_baseline_748_articles()
    
    validation_report = {
        'articles_found': len(automated_results),
        'baseline_matched': count_baseline_matches(automated_results, baseline_articles),
        'recall_rate': baseline_matched / 748,
        'new_articles_found': identify_new_articles(automated_results, baseline_articles),
        'missed_articles': identify_missed_articles(automated_results, baseline_articles)
    }
    
    return validation_report
```

2. **Success criteria:**
   - Must find ≥95% of my 748 baseline articles
   - <5% false positive rate
   - <10% manual review queue
   - Processing time <24 hours

**Expected Output:** Validation report showing system accurately replicates my methodology.

## Step 7: Scheduling and Monitoring

**Task:** Set up automated scheduling for recurrent searches.

**Your Instructions:**

1. **Automated scheduling:**
```python
import schedule
import time

def setup_automated_searches():
    """
    Schedule regular searches:
    - Monthly: Monitor for new publications
    - Quarterly: Full incremental search
    - Annually: Complete methodology review
    """
    
    # Monthly monitoring
    schedule.every().month.do(monitor_new_publications)
    
    # Quarterly full search
    schedule.every(3).months.do(run_incremental_search)
    
    # Annual full review
    schedule.every().year.do(run_annual_review)
    
    while True:
        schedule.run_pending()
        time.sleep(60)
```

2. **Monitoring and reporting:**
```python
def generate_search_report(search_results):
    """
    Create summary report of each search:
    - Total articles found
    - New articles vs duplicates
    - Theme breakdown
    - Quality metrics
    - Articles requiring manual review
    """
    return report
```

**Expected Output:** Fully automated system that runs recurrent searches with monitoring and reporting.

## Implementation Checklist

**Phase 1 (Week 1-2):**
- [ ] Extract all location terms from my documents
- [ ] Set up Web of Science API connection
- [ ] Test basic search functionality
- [ ] Implement duplicate detection algorithms

**Phase 2 (Week 3-4):**
- [ ] Build automated screening system
- [ ] Implement theme classification
- [ ] Set up Zotero API integration
- [ ] Create organized collection structure

**Phase 3 (Week 5-6):**
- [ ] Run retrospective validation (1930-2022)
- [ ] Compare results against my 748 baseline
- [ ] Refine algorithms based on validation
- [ ] Set up quality monitoring

**Phase 4 (Week 7-8):**
- [ ] Implement automated scheduling
- [ ] Create reporting dashboard
- [ ] Run first live search (2023-current)
- [ ] Document system and create user guide

## Expected Deliverables

1. **Python Scripts:**
   - Search term database and query builder
   - API integration classes
   - Duplicate detection system
   - Automated screening algorithms
   - Zotero integration functions

2. **Validation Report:**
   - Comparison against 748 baseline articles
   - Recall and precision metrics
   - Error analysis and recommendations

3. **Automated System:**
   - Scheduled search execution
   - Organized Zotero output
   - Quality monitoring and reporting
   - Manual review queue management

4. **Documentation:**
   - System architecture overview
   - User guide for operation
   - Maintenance and troubleshooting guide
   - API configuration instructions

## Success Metrics

- **Accuracy**: ≥95% recall of my 748 baseline articles
- **Efficiency**: Process completion in <24 hours
- **Quality**: <10% articles requiring manual review
- **Cost**: <$10,000/year total operational cost
- **Sustainability**: Minimal manual intervention required

**Please help me implement each phase step-by-step, starting with Phase 1.**