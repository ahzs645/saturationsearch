# Streamlined Automated Nechako Watershed Saturation Search

## Simplified Workflow (No DistillerSR Dependency)

**Current Manual Process:**
```
Database Searches → DistillerSR → Manual Screening → Zotero → Portal
```

**New Automated Process:**
```
Database APIs → Automated Processing → Zotero → Portal
```

## Core Automation Components

### **Phase 1: Direct Database Integration (Month 1)**

**1.1 API-Based Search Execution**
```python
def execute_saturation_search(date_from, date_to):
    """
    Direct API search replicating your exact methodology
    """
    # Build location query from your search terms
    location_terms = load_nechako_locations()
    geographic_filter = '("Canada" OR "British Columbia")'
    
    # Web of Science API
    wos_results = wos_api.search(
        query=f"({location_terms}) AND {geographic_filter}",
        date_range=(date_from, date_to),
        language="English",
        fields=["TI", "AB"]
    )
    
    # Additional databases
    scopus_results = scopus_api.search(similar_query)
    science_direct_results = sd_api.search(similar_query)
    
    return combine_results(wos_results, scopus_results, science_direct_results)
```

**1.2 Real-time Search Term Management**
- Database of all your location terms (lakes, rivers, communities)
- Version-controlled search terms
- Easy addition of new geographic locations
- Query optimization for database character limits

### **Phase 2: Advanced Duplicate Detection (Month 1-2)**

**2.1 Multi-Level Deduplication (Better than DistillerSR)**
```python
def advanced_duplicate_detection(articles, existing_zotero_library):
    """
    Modern deduplication superior to DistillerSR
    """
    
    # Level 1: Exact matches
    exact_matches = find_exact_duplicates(articles, ["DOI", "PMID"])
    
    # Level 2: High confidence matches
    high_confidence = fuzzy_match_titles(articles, threshold=0.95)
    
    # Level 3: Author + year + journal combinations
    author_year_matches = match_author_year_journal(articles)
    
    # Level 4: Abstract similarity (for articles without DOI)
    abstract_matches = semantic_similarity_matching(articles, threshold=0.85)
    
    # Level 5: Compare against existing 748 articles
    existing_matches = compare_with_existing_library(articles, existing_zotero_library)
    
    return deduplicated_articles, duplicate_report
```

**2.2 Quality Scoring System**
```python
def quality_assessment(article):
    """
    Automated quality and relevance scoring
    """
    score = 0
    confidence_factors = []
    
    # Geographic relevance scoring
    location_matches = count_location_term_matches(article)
    score += location_matches * 10
    
    # Content relevance (based on your 748 article patterns)
    content_score = classify_content_relevance(article)
    score += content_score
    
    # Exclusion rule checking
    if check_exclusion_criteria(article):
        score = 0  # Auto-exclude
    
    return score, confidence_factors
```

### **Phase 3: Automated Screening & Classification (Month 2)**

**3.1 Replace Manual DistillerSR Screening**
```python
def automated_screening(articles):
    """
    Automated screening replacing manual DistillerSR process
    """
    screened_articles = []
    
    for article in articles:
        # Apply your exact inclusion/exclusion criteria
        screening_result = {
            'article': article,
            'included': False,
            'confidence_score': 0,
            'reasons': [],
            'theme': None,
            'manual_review_required': False
        }
        
        # Geographic relevance check
        if geographic_relevance_check(article):
            screening_result['included'] = True
            screening_result['reasons'].append('Geographic match')
        
        # Language check (English only)
        if not is_english(article):
            screening_result['included'] = False
            screening_result['reasons'].append('Non-English')
        
        # UNBC exclusion check
        if is_unbc_non_nechako(article):
            screening_result['included'] = False
            screening_result['reasons'].append('UNBC non-Nechako research')
        
        # Thematic classification (Environment/Community/Health)
        if screening_result['included']:
            screening_result['theme'] = classify_theme(article)
        
        # Flag uncertain cases for manual review
        if screening_result['confidence_score'] < 0.8:
            screening_result['manual_review_required'] = True
        
        screened_articles.append(screening_result)
    
    return screened_articles
```

**3.2 Machine Learning Enhancement**
```python
# Train on your existing 748 articles for better classification
def train_classification_model(existing_articles_748):
    """
    Use your 748 articles as training data
    """
    # Extract features from titles, abstracts, themes
    features = extract_features(existing_articles_748)
    
    # Train models for:
    # - Relevance classification (include/exclude)
    # - Theme classification (Environment/Community/Health)
    # - Quality scoring
    
    return trained_models
```

### **Phase 4: Direct Zotero Integration (Month 2-3)**

**4.1 Seamless Zotero API Integration**
```python
def update_zotero_library(processed_articles, search_date):
    """
    Direct upload to Zotero with organized structure
    """
    
    # Create new subcollection for this search
    collection_name = f"SearchResults{search_date.strftime('%Y%m')}"
    collection_id = zotero.create_collection(collection_name)
    
    # Upload new articles
    for article in processed_articles:
        if article['included'] and not article['manual_review_required']:
            # Clean and standardize metadata
            clean_metadata = standardize_metadata(article)
            
            # Add to appropriate subcollection
            item_id = zotero.add_item(clean_metadata, collection_id)
            
            # Tag with theme and search terms
            zotero.add_tags(item_id, [article['theme'], 'Saturation Search'])
    
    # Create manual review collection if needed
    manual_review_articles = [a for a in processed_articles if a['manual_review_required']]
    if manual_review_articles:
        review_collection = zotero.create_collection(f"ManualReview{search_date.strftime('%Y%m')}")
        for article in manual_review_articles:
            zotero.add_item(article, review_collection)
```

**4.2 Smart Organization System**
```python
# Maintain organized Zotero structure
zotero_structure = {
    "Nechako Saturation Search": {
        "SearchResults202407": [],  # Latest search
        "SearchResults202404": [],  # Previous searches
        "On Portal": [],            # Already uploaded to portal
        "Manual Review Queue": [],   # Uncertain cases
        "Excluded Articles": [],     # For reference
        "Large Lake Monitoring": []  # Special collections
    }
}
```

### **Phase 5: Optional Portal Integration (Month 3-4)**

**5.1 Portal Upload Automation**
```python
def portal_integration(zotero_articles):
    """
    Optional automated portal uploads
    """
    # Export from Zotero
    portal_ready_articles = prepare_for_portal(zotero_articles)
    
    # Compare against existing portal content (avoiding your MATLAB script issues)
    new_articles = filter_existing_portal_content(portal_ready_articles)
    
    # Batch upload to portal
    upload_results = portal_api.batch_upload(new_articles)
    
    # Update Zotero "On Portal" collection
    update_portal_tracking(upload_results)
    
    return upload_results
```

## Technical Architecture

### **Streamlined System Design**
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Location Term │    │   Search API     │    │  Database APIs  │
│   Database      │───▶│   Orchestrator   │───▶│  (WoS, Scopus)  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Advanced      │    │   Processing     │    │   Raw Results   │
│   Deduplication │◀───│   Pipeline       │◀───│   (Combined)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
          │                                               
          ▼                                               
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Automated     │    │   Zotero API     │    │   Portal API    │
│   Screening     │───▶│   Integration    │───▶│   (Optional)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Implementation Timeline

### **Month 1: Core Foundation**
- [ ] Extract all location terms from your search documents
- [ ] Set up database API connections (Web of Science, Scopus)
- [ ] Implement advanced duplicate detection system
- [ ] Build geographic relevance checking
- [ ] Test against subset of your 748 articles

### **Month 2: Screening & Processing**
- [ ] Implement automated screening logic
- [ ] Create theme classification system
- [ ] Build quality scoring algorithms
- [ ] Set up manual review queue system
- [ ] Train ML models on your existing articles

### **Month 3: Integration & Testing**
- [ ] Integrate with Zotero API
- [ ] Create organized collection structure
- [ ] Run full retrospective test (1930-2022)
- [ ] Validate against your 748 baseline articles
- [ ] Refine algorithms based on results

### **Month 4: Production & Optimization**
- [ ] First live recurrent search (2023-current)
- [ ] Set up automated scheduling (quarterly/annual)
- [ ] Create monitoring and reporting system
- [ ] Optional portal integration
- [ ] Documentation and handover

## Cost Savings vs Original Approach

### **Eliminated Costs:**
- **DistillerSR License**: ~$10,000-15,000/year
- **Manual Screening Time**: ~80% reduction in person-hours
- **Review Coordination**: Automated reviewer assignment elimination

### **New Costs:**
- **Database APIs**: ~$7,000/year (Web of Science + Scopus)
- **Development**: ~$20,000-30,000 (one-time)
- **Cloud Infrastructure**: ~$1,000/year
- **Maintenance**: ~$5,000/year

**Net Savings**: ~$5,000-10,000/year after first year

## Quality Assurance Without DistillerSR

### **Validation Protocol**
1. **Retrospective Testing**: Run automated search for 1930-2022
2. **Baseline Comparison**: Must find ≥95% of your 748 articles
3. **False Positive Analysis**: Review excluded articles for patterns
4. **Manual Review Queue**: Human oversight for uncertain cases

### **Ongoing Quality Control**
- **Monthly Spot Checks**: Random sample validation
- **Annual Full Review**: Complete methodology assessment
- **Algorithm Updates**: Continuous improvement based on results
- **Expert Oversight**: Subject matter expert final review of edge cases

### **Success Metrics**
- **Recall Rate**: ≥95% of known relevant articles found
- **Precision Rate**: ≥90% of included articles are relevant
- **Processing Speed**: Complete search in <24 hours
- **Manual Review Load**: <10% of articles require human review

## Advantages of DistillerSR-Free Approach

### **Technical Benefits**
- **Better Deduplication**: Modern algorithms superior to DistillerSR
- **Faster Processing**: No manual bottlenecks
- **API Integration**: Seamless workflow automation
- **Scalability**: Easy to expand to other watersheds/regions

### **Operational Benefits**
- **Cost Effective**: Lower long-term operational costs
- **No Licensing Dependencies**: Own your entire workflow
- **Continuous Operation**: 24/7 automated monitoring
- **Consistent Results**: Eliminates inter-reviewer variability

### **Strategic Benefits**
- **Future-Proof**: Modern, maintainable technology stack
- **Transferable**: Methodology can be applied to other regions
- **Research Value**: Automated approach is publishable methodology
- **Community Access**: Direct public access via Zotero library

This streamlined approach eliminates the DistillerSR dependency while providing superior automation, better integration, and significant cost savings.