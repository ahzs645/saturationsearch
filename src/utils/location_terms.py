"""
Enhanced Nechako Watershed Location Terms Database
Addresses gaps identified in gap analysis and adds comprehensive coverage.
"""

import unicodedata
import re
from typing import Dict, List, Set
from collections import defaultdict

# Enhanced location terms with all categories and missing terms
ENHANCED_NECHAKO_LOCATION_TERMS = {
    # Major rivers and primary watercourses
    "rivers": [
        "Nechako River", "Fraser River", "Stuart River", "Stellako River", 
        "Endako River", "Nadina River", "Chelaslie River", "Cheslatta River",
        "Entiako River", "Kuzkwa River", "Necoslie River", "Nithi River",
        "Ocock River", "Sakeniche River", "Sinkut River", "St. Thomas River",
        "Tachie River", "Tetachuck River", "Tsilcoh River", "Driftwood River",
        "Chilako River", "Chezko River", "Blanchet River", "Middle River"
    ],
    
    # Creeks and smaller watercourses (including missing ones from gap analysis)
    "creeks": [
        "Aird Creek", "Alf Creek", "Allen Creek", "Allin Creek", "Andrews Creek",
        "Angly Creek", "Ankwill Creek", "Arethusa Creek", "Aslin Creek", "Baker Creek",
        "Banguarel Creek", "Baptiste Creek", "Bates Creek", "Beach Creek", "Bearcub Creek",
        "Beaverdale Creek", "Beaverdam Creek", "Beaverley Creek", "Belisle Creek", "Belzile Creek",
        "Benoit Creek", "Big Bend Creek", "Bird Creek", "Bivouac Creek", "Blackburne Creek",
        "Bone Creek", "Breadalbane Creek", "Breeze Creek", "Brooks Creek", "Burnstead Creek",
        "Butcherflats Creek", "Butterfield Creek", "Cabin Creek", "Campbell Creek", "Camsell Creek",
        "Capoose Creek", "Chedakuz Creek", "Chehischic Creek", "Cheskwa Creek", "Chikamin Creek",
        "Chilco Creek", "Chillo Creek", "Chinohchey Creek", "Chowsunkut Creek", "Clarke Creek",
        "Clatlatiently Creek", "Clear Creek", "Cluculz Creek", "Coles Creek", "Colley Creek",
        "Comb Creek", "Cordella Creek", "Corkscrew Creek", "Cranberry Creek", "Cripple Creek",
        "Croft Creek", "Cummins Creek", "Cutoff Creek", "Dahl Creek", "Dan Miner Creek",
        "Davidson Creek", "Decker Creek", "Dodd Creek", "Dog Creek", "Dorman Creek",
        "Dust Creek", "Eagle Creek", "East Erhorn Creek", "East Moxley Creek", "East Murray Creek",
        "East Negaard Creek", "East Side Creek", "Eastern Creek", "Ed Creek", "Eden Creek",
        "Engen Creek", "Engstrom Creek", "Erhorn Creek", "Esker Creek", "Evans Creek",
        "Fawnie Creek", "Fifteen Creek", "Finger Creek", "Fleming Creek", "Foster Creek",
        "Four Mile Creek", "Frypan Creek", "Fyfe Creek", "Garvin Creek", "Gauvin Creek",
        "Gerow Creek", "Gesul Buhn Creek", "Gilbert Creek", "Gloyazikut Creek", "Goldie Creek",
        "Goodwin Creek", "Graham Creek", "Gravel Creek", "Greer Creek", "Gregg Creek",
        "Grostete Creek", "Guyishton Creek", "Halsey Creek", "Hatdudatehl Creek", "Hautête Creek",
        "Hawley Creek", "Henkel Creek", "Hogsback Creek", "Hudson Bay Creek", "Hulatt Creek",
        "Hutchison Creek", "Hyman Creek", "Inzana Creek", "Isaac Creek", "Jack Weekes Creek",
        "Janzê Creek", "Kasalka Creek", "Kazchek Creek", "Kec Creek", "Kellogg Creek",
        "Khai Creek", "Kinowsa Creek", "Kivi Creek", "Kleedlee Creek", "Klinsake Creek",
        "Kloch Creek", "Kluk Creek", "Knapp Creek", "Knight Creek", "Lakes Creek",
        "Laventie Creek", "Lavoie Creek", "Leduc Creek", "Leigh Creek", "Leo Creek",
        "Leona Creek", "Little Bobtail Creek", "Lovell Creek", "Lucas Creek", "Macdougall Creek",
        "MacIvor Creek", "Maclaing Creek", "Maltby Creek", "Mandalay Creek", "Marie Creek",
        "Martens Creek", "Mathews Creek", "McCuish Creek", "McDonald Creek", "McIntosh Creek",
        "McKay Creek", "McKenzie Creek", "McMillan Creek", "Michel Creek", "Micks Creek",
        "Millard Creek", "Moss Creek", "Moxley Creek", "Mudhole Creek", "Murray Creek",
        "Nahounli Creek", "Nancut Creek", "Nankuz Creek", "Natazutlo Creek", "Negaard Creek",
        "Neuco Creek", "Nielsp Creek", "Nine Mile Creek", "Nizik Creek", "Norman Creek",
        "North Stony Creek", "Ohr Creek", "Olie Creek", "O'Ne-ell Creek", "Ormond Creek",
        "Parkland Creek", "Parrott Creek", "Paula Creek", "Peace Creek", "Perry Creek",
        "Peta Creek", "Peter Aleck Creek", "Phillips Creek", "Pinchi Creek", "Pitka Creek",
        "Poplar Creek", "Powder House Creek", "Prairie Meadow Creek", "Preston Creek", "Puttah Creek",
        "Ramsay Creek", "Redmond Creek", "Relief Creek", "Rentoul Creek", "Rhine Creek",
        "Robertson Creek", "Rubyrock Creek", "Sam Ross Creek", "Sandifer Creek", "Sauls Creek",
        "Saxton Creek", "Schjelderup Creek", "Shelford Creek", "Sheraton Creek", "Shillestead Brook",
        "Short Creek", "Shotgun Creek", "Shovel Creek", "Sibola Creek", "Sidney Creek",
        "Sinta Creek", "Sitlika Creek", "Small Trout Creek", "Smith Creek", "Snodgrass Creek",
        "Sob Creek", "South Creek", "South Goldie Creek", "Sowchea Creek", "Specularite Creek",
        "Spencha Creek", "St. George Creek", "Stearns Creek", "Stern Creek", "Stony Creek",
        "Swanson Creek", "Sweden Creek", "Sweetnam Creek", "Tachick Creek", "Tachintelachick Creek",
        "Tagetochlain Creek", "Taginchil Creek", "Tahultzu Creek", "Takatoot Creek", "Takysie Creek",
        "Targe Creek", "Tarnezell Creek", "Taslincheko Creek", "Tatalaska Creek", "Tatalrose Creek",
        "Tatin Creek", "Tatsutnai Creek", "Tatuk Creek", "Tchesinkut Creek", "Tesla Creek",
        "Tezzeron Creek", "Tibbets Creek", "Tildesley Creek", "Tintagel Creek", "Tliti Creek",
        "Tlutlias Creek", "Totem Pole Creek", "Trankle Creek", "Tritt Creek", "Troitsa Creek",
        "Tsah Creek", "Tsitsutl Creek", "Tultsau Creek", "Ucausley Creek", "Uncha Creek",
        "Upper Moss Creek", "Van Decar Creek", "Van Lear Creek", "Van Tine Creek", "Wardrop Creek",
        "Webber Creek", "Wells Creek", "West Engen Creek", "West Tarnezell Creek", "Whitefish Creek",
        "Whiting Creek", "Wilhelmsen Creek", "Willowy Creek", "Wynkes Creek", "Zelkwas Creek"
    ],
    
    # Lakes (including missing ones and accent variants)
    "lakes": [
        "Angly Lake", "Anzus Lake", "Barton Lake", "Bednesti Lake", "Bentzi Lake",
        "Bickle Lake", "Binta Lake", "Bird Lake", "Bittern Lake", "Blanchet Lake",
        "Blanket Lakes", "Bodley Lake", "Bone Lake", "Boomerang Lake", "Borel Lake",
        "Breadalbane Lake", "Brewster Lakes", "Bungalow Lake", "Bunghun Whucho Lake",
        "Burns Lake", "Butterfield Lake", "Cabin Lake", "Cam McEwen Lake", "Capoose Lake",
        "Captain Harry Lake", "Carrier Lake", "Centre Lake", "Chaoborus Lake", "Chelaslie Arm",
        "Cheslatta Lake", "Cheztainya Lake", "Chief Louis Lake", "Chowsunkut Lake", "Cicuta Lake",
        "Circle Lake", "Circum Lake", "Clatlatiently Lake", "Cluculz Lake", "Cobb Lake",
        "Coles Lake", "Copley Lake", "Cory Lake", "Cow Lake", "Crystal Lake",
        "Cunningham Lake", "Dahl Lake", "Dan Miner Lake", "Darby Lake", "Dargie Lake",
        "Davidson Lake", "Dawson Lake", "Decker Lake", "Dem Lake", "Deserter Lake",
        "Dolphin Lake", "Dorman Lake", "Drift Lake", "Drywilliam Lake", 
        "East Hautête Lake", "East HautÃªte Lake",  # Both accent variants
        "Elalie Lake", "Elliott Lake", "Emmett Lake", "Entiako Lake", "Enz Lake",
        "Euchu Reach", "Eulatazella Lake", "Eutsuk Lake", "Farbus Lake", "Fenton Lake",
        "Finger Lake", "Finnie Lake", "Fish Lake", "Flat Lake", "Fleming Lake",
        "Foster Lakes", "François Lake", "FranÃ§ois Lake",  # Both accent variants
        "Frank Lake", "Fraser Lake", "Friday Lake", "Fyfe Lake", "Gale Lake",
        "Gatcho Lake", "Getzuni Lake", "Ghitezli Lake", "Glatheli Lake", "Gluten Lake",
        "Goodrich Lake", "Goosefoot Lake", "Gordon Lake", "Guyishton Lake", "Hallett Lake",
        "Haney Lake", "Hanson Lake", "Harp Lake", "Hat Lake", "Hatdudatehl Lake",
        "Hautête Lake", "HautÃªte Lake",  # Both accent variants
        "Hay Lake", "Hewson Lake", "Hobson Lake", "Hogsback Lake", "Holy Cross Lake",
        "Home Lake", "Horseshoe Lake", "Hoult Lake", "Innes Lake", "Intata Reach",
        "Inzana Lake", "Isaac Lake", "Island Lake", "Jesson Lake", "Johnny Lake",
        "Johnson Lake", "Justine Lake", "Kalder Lake", "Karena Lake", "Kaykay Lake",
        "Kaza Lake", "Kazchek Lake", "Kenney Lake", "Kloch Lake", "Knapp Lake",
        "Knewstubb Lake", "Kuyakuz Lake", "Laidman Lake", "Laurie Lake", "Lavoie Lake",
        "Lena Lake", "Lindquist Lake", "Little Bobtail Lake", "Little Whitesail Lake",
        "Llgitiyuz Lake", "Long Lake", "Looncall Lake", "Lucas Lake", "Lumpy Lake",
        "Macdougall Lake", "Mackenzie Lake", "Majuba Lake", "Malaput Lake", "Margaret Lake",
        "Marie Lake", "McKelvey Lake", "McKnab Lake", "Michel Lake", "Milligan Lake",
        "Mink Lake", "Mollice Lake", "Moose Lake", "Morgan Lake", "Murdoch Lake",
        "Murray Lake", "Musclow Lake", "Nadina Lake", "Nadsilnich Lake", "Nahounli Lake",
        "Nakinilerak Lake", "Naltesby Lake", "Nanitsch Lake", "Nanna Lake", "Natalkuz Lake",
        "Natazutlo Lake", "Natowite Lake", "Needle Lake", "Nendatoo Lake", "Ness Lake",
        "Newcombe Lake", "Nizik Lake", "Norman Lake", "Nulki Lake", "Nutli Lake",
        "Ocock Lake", "Octopus Lake", "Olaf Lake", "Oona Lake", "Ootsa Lake",
        "Ootsanee Lake", "Ormond Lake", "Otterson Lake", "Owl Lake", "Paddle Lake",
        "Pam Lake", "Parrott Lakes", "Parrott Lake",  # Both singular and plural
        "Peta Lake", "Picket Lake", "Pinchi Lake", "Pondosy Lake", "Redfish Lake",
        "Reid Lake", "Richardson Lake", "Rubyrock Lake", "Sabina Lake", "Sandifer Lake",
        "Sather Lake", "Saxton Lake", "Seel Lake", "Shelford Lake", "Shesta Lake",
        "Short Portage Lake", "Sinkut Lake", "Skinny Lake", "Skins Lake", "Smith Lake",
        "Snowflake Lake", "Spad Lake", "Specularite Lake", "Square Lake", "St. Thomas Lake",
        "Starret Lake", "Stern Lake", "Stuart Lake", "Surel Lake", "Sweeney Lake",
        "Tachick Lake", "Tagai Lake", "Tagetochlain Lake", "Taginchil Lake", "Tahtsa Lake",
        "Tahtsa Reach", "Tahultzu Lake", "Tahuntesko Lake", "Takatoot Lake", "Takla Lake",
        "Takysie Lake", "Targe Lake", "Tarnezell Lake", "Tasa Lake", "Tatalaska Lake",
        "Tatalrose Lake", "Tatelkuz Lake", "Tatin Lake", "Tatsadah Lake", "Tatuk Lake",
        "Tchesinkut Lake", "Tercer Lake", "Tesla Lake", "Tetachuck Lake", "Tezzeron Lake",
        "Thletelban Lake", "Thompson Lake", "Tlutlias Lake", "Tochcha Lake", "Tomas Lake",
        "Top Lake", "Trembleur Lake", "Triangle Lake", "Troitsa Lake", "Tsayakwacha Lake",
        "Tschick Lake", "Tsetoyank'ut Lake", "Tsichgass Lake", "Turff Lake", "Twinkle Lake",
        "Uduk Lake", "Uncha Lake", "Wahla Lake", "Wapoose Lake", "Webber Lake",
        "White Eye Lake", "Whitefish Lake", "Whitesail Lake", "Williamson Lake",
        "Willington Lake", "Wutak Lake", "Yatzutzin Lake", "Yellow Moose Lake"
    ],
    
    # Physiographic features (previously missing category)
    "physiography": [
        "Nechako Plateau", "Quanchus Range", "Vital Range", "Interior Plateau",
        "Omineca Mountains", "Coast Mountains", "Takla Range", "Whitesail Range",
        "Cariboo Heart Range", "Chikamin Range", "Connelly Range", "Driftwood Range",
        "Fawnie Range", "Hazelton Mountains", "Henson Hills", "Hogem Ranges",
        "Holmes Ridge", "Interior System", "Kasalka Range", "Kitimat Ranges",
        "Mitchell Range", "Mosquito Hills", "Murray Ridge", "Naglico Hills",
        "Nechako Range", "Pattullo Range", "Sasklo Ridge", "Savory Ridge",
        "Shelford Hills", "Sibola Range", "Sitlika Range", "Skeena Mountains",
        "Tahtsa Ranges", "Tatuk Hills", "Tekaiziyis Ridge", "Telegraph Range",
        "Tochquonyalla Range", "Tsaytut Spur", "Western System", "Windfall Hills"
    ],
    
    # Cities, towns, and populated places (including missing ones)
    "populated_places": [
        "Vanderhoof", "Prince George", "Fort St. James", "Fraser Lake", "Burns Lake",
        "Bulkley House", "Cheslatta", "Clemretta", "Colleymount", "Danskin",
        "Decker Lake", "Dog Creek", "Endako", "Fort Fraser", "Francois Lake",
        "Grassy Plains", "Isle Pierre", "Leo Creek", "Mapes", "Marilla",
        "McDonalds Landing", "Middle River", "Miworth", "Mud River", "Nautley",
        "Noralee", "Nulki", "Ootsa Lake", "Pinchi", "Pinchi Lake",
        "Punchaw", "Reid Lake", "Shady Valley", "Sinkut River", "Skins Lake",
        "Southbank", "Sowchea 3", "Stellako", "Stony Creek", "Sunnyside",
        "Tachie", "Takla Landing", "Takysie Lake", "Tatalrose", "Tatla't East",
        "Tchesinkut Lake", "Telachick", "Tintagel", "Weneez", "Wet'suwet'en Village",
        "Wistaria", "Woyenne", "Yekooche"
    ],
    
    # First Nations communities and governments (enhanced)
    "first_nations": [
        "Stellat'en", "Nee-Tahi-Buhn", "Lake Babine", "Yekooche", "Burns Lake",
        "Cheslatta", "Nadleh Whuten", "Nak'azdli", "Saik'uz", "Skin Tyee",
        "Takla Lake", "Tl'azt'en", "Wet'suwet'en", "Carrier Sekani",
        "Wet'suwet'en Nation", "Carrier Nation"
    ],
    
    # Parks and protected areas
    "protected_areas": [
        "Tweedsmuir Provincial Park", "Entiako Provincial Park", "Finger-Tatuk Provincial Park",
        "Cheslatta Falls Provincial Park", "Beaumont Provincial Park", "Babine Mountains Provincial Park"
    ],
    
    # Sub-watersheds and reaches
    "sub_watersheds": [
        "Chelaslie Arm", "Tahtsa Reach", "Intata Reach", "Euchu Reach",
        "Upper Nechako", "Lower Nechako", "Middle Nechako"
    ],
    
    # Primary watershed terms
    "watershed_terms": [
        "Nechako", "Nechako Watershed", "Nechako Basin", "Nechako River System",
        "Fraser River", "British Columbia", "BC Interior", "Central Interior"
    ]
}

# Synonym mappings for watercourse types
WATERCOURSE_SYNONYMS = {
    "creek": ["creek", "river", "brook", "stream"],
    "river": ["river", "creek", "brook", "stream"], 
    "brook": ["brook", "creek", "river", "stream"],
    "stream": ["stream", "creek", "river", "brook"]
}

def normalize_text(text: str) -> str:
    """
    Normalize text by removing accents and converting to lowercase.
    Handles UTF-8 encoding issues.
    """
    if not text:
        return ""
    
    # Normalize Unicode characters
    text = unicodedata.normalize('NFD', text)
    
    # Remove accents by encoding to ASCII and ignoring errors
    text = text.encode('ascii', 'ignore').decode('ascii')
    
    # Convert to lowercase and clean up
    text = text.lower().strip()
    
    return text

def canonicalize(term: str) -> str:
    """Canonicalize term for deduplication across categories."""
    return normalize_text(term)

def build_category_index() -> Dict[str, Set[str]]:
    """
    Build index mapping canonical terms to categories.
    This helps identify terms that appear in multiple categories.
    """
    idx = defaultdict(set)
    for cat, terms in ENHANCED_NECHAKO_LOCATION_TERMS.items():
        for term in terms:
            canonical = canonicalize(term)
            idx[canonical].add(cat)
    return idx

def get_deduplicated_terms() -> Set[str]:
    """
    Get deduplicated set of all location terms.
    Returns unique canonical terms across all categories.
    """
    all_terms = set()
    for terms in ENHANCED_NECHAKO_LOCATION_TERMS.values():
        for term in terms:
            all_terms.add(canonicalize(term))
    return all_terms

def generate_watercourse_variants(name: str) -> List[str]:
    """
    Generate variants of watercourse names with different suffixes.
    e.g., "Nechako Creek" -> ["Nechako Creek", "Nechako River", "Nechako Brook", "Nechako Stream"]
    """
    variants = []
    
    # Extract base name and suffix
    name_parts = name.split()
    if len(name_parts) >= 2:
        suffix = name_parts[-1].lower()
        base_name = " ".join(name_parts[:-1])
        
        if suffix in WATERCOURSE_SYNONYMS:
            for synonym in WATERCOURSE_SYNONYMS[suffix]:
                variants.append(f"{base_name} {synonym.title()}")
        else:
            variants.append(name)
    else:
        variants.append(name)
    
    return variants

def generate_accent_variants(name: str) -> List[str]:
    """
    Generate both accented and non-accented variants of names.
    """
    variants = [name]
    
    # Add normalized (no accents) version
    normalized = normalize_text(name)
    if normalized != name.lower():
        variants.append(normalized)
        variants.append(normalized.title())
    
    return list(set(variants))

def build_comprehensive_location_query(use_priority_terms: bool = False) -> str:
    """
    Build a comprehensive location query with all terms and variants.
    Deduplicates across categories before building query.
    
    Args:
        use_priority_terms: If True, use only highest priority terms
        
    Returns:
        Query string for database searches
    """
    all_terms = set()
    
    if use_priority_terms:
        # Priority terms - most important and frequently cited
        priority_categories = ["watershed_terms", "rivers", "populated_places", "physiography"]
        categories_to_use = priority_categories
    else:
        # Use all categories
        categories_to_use = ENHANCED_NECHAKO_LOCATION_TERMS.keys()
    
    # Collect terms from specified categories
    base_terms = set()
    for category in categories_to_use:
        if category in ENHANCED_NECHAKO_LOCATION_TERMS:
            for term in ENHANCED_NECHAKO_LOCATION_TERMS[category]:
                base_terms.add(term)
    
    # Generate variants for all base terms (this deduplicates automatically)
    for term in base_terms:
        # Add original term
        all_terms.add(term)
        
        # Add accent variants
        for variant in generate_accent_variants(term):
            all_terms.add(variant)
        
        # Add watercourse variants if it looks like a watercourse
        if any(suffix in term.lower() for suffix in ["creek", "river", "brook", "stream"]):
            for variant in generate_watercourse_variants(term):
                all_terms.add(variant)
    
    # Build query string from deduplicated terms
    unique_terms = sorted(list(all_terms))
    quoted_terms = [f'"{term}"' for term in unique_terms]
    query = " OR ".join(quoted_terms)
    
    return query

def build_web_of_science_query(use_priority_terms: bool = False, 
                              date_start: str = "1930-01-01", 
                              date_end: str = "2023-12-31") -> str:
    """
    Build Web of Science query with enhanced location terms.
    """
    location_query = build_comprehensive_location_query(use_priority_terms)
    
    # Topic areas relevant to watershed research
    topic_terms = [
        "watershed", "hydrology", "water quality", "aquatic ecosystem", 
        "fisheries", "salmon", "environmental assessment", "water resources", 
        "river ecology", "biodiversity", "conservation", "climate change", 
        "forestry", "land use", "First Nations", "indigenous"
    ]
    
    topic_query = " OR ".join([f'"{term}"' for term in topic_terms])
    
    # Convert date format for WoS
    start_year = date_start.split('-')[0]
    end_year = date_end.split('-')[0]
    
    query = f'TS=({location_query}) AND TS=({topic_query}) AND PY=({start_year}-{end_year}) AND LA=(English)'
    
    return query

def build_scopus_query(use_priority_terms: bool = False,
                      date_start: str = "1930", 
                      date_end: str = "2023") -> str:
    """
    Build Scopus query with enhanced location terms.
    """
    location_query = build_comprehensive_location_query(use_priority_terms)
    
    # Convert to Scopus format (TITLE-ABS-KEY)
    location_terms = [term.strip('"') for term in location_query.split(' OR ')]
    scopus_location = " OR ".join([f'TITLE-ABS-KEY("{term}")' for term in location_terms])
    
    # Topic terms for Scopus
    topic_terms = [
        "watershed", "hydrology", "water quality", "aquatic ecosystem",
        "fisheries", "salmon", "environmental assessment", "water resources",
        "river ecology", "biodiversity", "conservation", "climate change",
        "forestry", "land use", "First Nations", "indigenous"
    ]
    
    scopus_topics = " OR ".join([f'TITLE-ABS-KEY("{term}")' for term in topic_terms])
    
    query = (f'({scopus_location}) AND ({scopus_topics}) '
             f'AND PUBYEAR > {int(date_start)-1} AND PUBYEAR < {int(date_end)+1} '
             f'AND LANGUAGE(english) AND DOCTYPE(ar OR re OR cp OR ch)')
    
    return query

def get_location_terms_stats() -> Dict[str, int]:
    """
    Get statistics about the enhanced location terms database.
    Now accounts for deduplication across categories.
    """
    stats = {}
    
    # Raw counts per category
    for category, terms in ENHANCED_NECHAKO_LOCATION_TERMS.items():
        stats[f"{category}_raw"] = len(terms)
    
    # Deduplicated counts
    category_index = build_category_index()
    deduplicated_terms = get_deduplicated_terms()
    
    stats['total_raw'] = sum(len(terms) for terms in ENHANCED_NECHAKO_LOCATION_TERMS.values())
    stats['total_unique'] = len(deduplicated_terms)
    stats['duplicates_across_categories'] = stats['total_raw'] - stats['total_unique']
    
    # Category overlap analysis
    multi_category_terms = {term: cats for term, cats in category_index.items() if len(cats) > 1}
    stats['multi_category_terms'] = len(multi_category_terms)
    
    return stats

def analyze_category_overlaps() -> Dict[str, List[str]]:
    """
    Analyze which terms appear in multiple categories.
    Useful for understanding data quality and potential issues.
    """
    category_index = build_category_index()
    overlaps = {}
    
    for term, categories in category_index.items():
        if len(categories) > 1:
            category_combo = " + ".join(sorted(categories))
            if category_combo not in overlaps:
                overlaps[category_combo] = []
            overlaps[category_combo].append(term)
    
    return overlaps

if __name__ == "__main__":
    # Display enhanced statistics
    stats = get_location_terms_stats()
    
    print("ENHANCED NECHAKO LOCATION TERMS DATABASE")
    print("=" * 50)
    
    print("Raw counts per category:")
    for category in ENHANCED_NECHAKO_LOCATION_TERMS.keys():
        raw_count = stats[f"{category}_raw"]
        print(f"  {category}: {raw_count} terms")
    
    print(f"\nDeduplication analysis:")
    print(f"  Total raw terms: {stats['total_raw']}")
    print(f"  Total unique terms: {stats['total_unique']}")
    print(f"  Duplicates across categories: {stats['duplicates_across_categories']}")
    print(f"  Multi-category terms: {stats['multi_category_terms']}")
    
    print(f"\nQuery lengths:")
    print(f"  Priority query: {len(build_comprehensive_location_query(True))} chars")
    print(f"  Comprehensive query: {len(build_comprehensive_location_query(False))} chars")
    
    # Show category overlaps
    overlaps = analyze_category_overlaps()
    if overlaps:
        print(f"\nCategory overlaps (showing first 5):")
        for i, (combo, terms) in enumerate(list(overlaps.items())[:5]):
            print(f"  {combo}: {len(terms)} terms (e.g., {terms[0]})")