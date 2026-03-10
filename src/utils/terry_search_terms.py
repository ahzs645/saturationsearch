"""
Terry's exact WoS search terms — extracted from wos_search_parameters.json.

This is the authoritative reference for the Nechako Watershed saturation search
as built and maintained by Terry (Librarian/Search Specialist).

Search structure:
  #0: Key places (TS)           →   580 results
  #1: First Nations (TS)        →    78 results
  #2: Lakes (TS)                → 1,420 results
  #3: Physiography (TS)         → 1,238 results
  #4: Populated places (TS)     → 1,776 results
  #5: Creeks & rivers (TS)      → 1,264 results
  #6: #0 OR #1 OR ... OR #5     → 5,894 results
  #7: ALL=("British Columbia" OR "Canada") → 4,242,963 results
  #8: #6 AND #7                 → 1,790 results (final)

Options: lemmatize=On, database=WOSCC
"""

from typing import Dict, List, Set

# Search #0: Key places
KEY_PLACES = [
    "Fort St. James",
    "Fraser Lake",
    "Vanderhoof",
    "nechako",
    "prince george",
]

# Search #1: First Nations communities
FIRST_NATIONS = [
    "Burns Lake",
    "Cheslatta",
    "Lake Babine",
    "Nadleh Whuten",
    "Nak'azdli",
    "Nee-Tahi-Buhn",
    "Saik'uz",
    "Skin Tyee",
    "Stellat'en",
    "Takla Lake",
    "Tl'azt'en",
    "Wet'suwet'en",
    "Yekooche",
]

# Search #2: Lakes
LAKES = [
    "Angly Lake", "Anzus Lake", "Barton Lake", "Bednesti Lake", "Bentzi Lake",
    "Bickle Lake", "Binta Lake", "Bird Lake", "Bittern Lake", "Blanchet Lake",
    "Blanket Lakes", "Bodley Lake", "Bone Lake", "Boomerang Lake", "Borel Lake",
    "Breadalbane Lake", "Brewster Lakes", "Bungalow Lake", "Bunghun Whucho Lake",
    "Burns Lake", "Butterfield Lake", "Cabin Lake", "Cam McEwen Lake", "Capoose Lake",
    "Captain Harry Lake", "Carrier Lake", "Centre Lake", "Chaoborus Lake",
    "Chelaslie Arm", "Cheslatta Lake", "Cheztainya Lake", "Chief Louis Lake",
    "Chowsunkut Lake", "Cicuta Lake", "Circle Lake", "Circum Lake",
    "Clatlatiently Lake", "Cluculz Lake", "Cobb Lake", "Coles Lake", "Copley Lake",
    "Cory Lake", "Cow Lake", "Crystal Lake", "Cunningham Lake", "Dahl Lake",
    "Dan Miner Lake", "Darby Lake", "Dargie Lake", "Davidson Lake", "Dawson Lake",
    "Decker Lake", "Dem Lake", "Deserter Lake", "Dolphin Lake", "Dorman Lake",
    "Drift Lake", "Drywilliam Lake", "East Haut\u00eate Lake", "Elalie Lake",
    "Elliott Lake", "Emmett Lake", "Entiako Lake", "Enz Lake", "Euchu Reach",
    "Eulatazella Lake", "Eutsuk Lake", "Farbus Lake", "Fenton Lake", "Finger Lake",
    "Finnie Lake", "Fish Lake", "Flat Lake", "Fleming Lake", "Foster Lakes",
    "Fran\u00e7ois Lake", "Frank Lake", "Fraser Lake", "Friday Lake", "Fyfe Lake",
    "Gale Lake", "Gatcho Lake", "Getzuni Lake", "Ghitezli Lake", "Glatheli Lake",
    "Gluten Lake", "Goodrich Lake", "Goosefoot Lake", "Gordon Lake",
    "Guyishton Lake", "Hallett Lake", "Haney Lake", "Hanson Lake", "Harp Lake",
    "Hat Lake", "Hatdudatehl Lake", "Haut\u00eate Lake", "Hay Lake", "Hewson Lake",
    "Hobson Lake", "Hogsback Lake", "Holy Cross Lake", "Home Lake",
    "Horseshoe Lake", "Hoult Lake", "Innes Lake", "Intata Reach", "Inzana Lake",
    "Isaac Lake", "Island Lake", "Jesson Lake", "Johnny Lake", "Johnson Lake",
    "Justine Lake", "Kalder Lake", "Karena Lake", "Kaykay Lake", "Kaza Lake",
    "Kazchek Lake", "Kenney Lake", "Kloch Lake", "Knapp Lake", "Knewstubb Lake",
    "Kuyakuz Lake", "Laidman Lake", "Laurie Lake", "Lavoie Lake", "Lena Lake",
    "Lindquist Lake", "Little Bobtail Lake", "Little Whitesail Lake",
    "Llgitiyuz Lake", "Long Lake", "Looncall Lake", "Lucas Lake", "Lumpy Lake",
    "Macdougall Lake", "Mackenzie Lake", "Majuba Lake", "Malaput Lake",
    "Margaret Lake", "Marie Lake", "McKelvey Lake", "McKnab Lake", "Michel Lake",
    "Milligan Lake", "Mink Lake", "Mollice Lake", "Moose Lake", "Morgan Lake",
    "Murdoch Lake", "Murray Lake", "Musclow Lake", "Nadina Lake",
    "Nadsilnich Lake", "Nahounli Lake", "Nakinilerak Lake", "Naltesby Lake",
    "Nanitsch Lake", "Nanna Lake", "Natalkuz Lake", "Natazutlo Lake",
    "Natowite Lake", "Needle Lake", "Nendatoo Lake", "Ness Lake", "Newcombe Lake",
    "Nizik Lake", "Norman Lake", "Nulki Lake", "Nutli Lake", "Ocock Lake",
    "Octopus Lake", "Olaf Lake", "Oona Lake", "Ootsa Lake", "Ootsanee Lake",
    "Ormond Lake", "Otterson Lake", "Owl Lake", "Paddle Lake", "Pam Lake",
    "Parrott Lakes", "Peta Lake", "Picket Lake", "Pinchi Lake", "Pondosy Lake",
    "Redfish Lake", "Reid Lake", "Richardson Lake", "Rubyrock Lake", "Sabina Lake",
    "Sandifer Lake", "Sather Lake", "Saxton Lake", "Seel Lake", "Shelford Lake",
    "Shesta Lake", "Short Portage Lake", "Sinkut Lake", "Skinny Lake",
    "Skins Lake", "Smith Lake", "Snowflake Lake", "Spad Lake", "Specularite Lake",
    "Square Lake", "St. Thomas Lake", "Starret Lake", "Stern Lake", "Stuart Lake",
    "Surel Lake", "Sweeney Lake", "Tachick Lake", "Tagai Lake",
    "Tagetochlain Lake", "Taginchil Lake", "Tahtsa Lake", "Tahtsa Reach",
    "Tahultzu Lake", "Tahuntesko Lake", "Takatoot Lake", "Takla Lake",
    "Takysie Lake", "Targe Lake", "Tarnezell Lake", "Tasa Lake", "Tatalaska Lake",
    "Tatalrose Lake", "Tatelkuz Lake", "Tatin Lake", "Tatsadah Lake", "Tatuk Lake",
    "Tchesinkut Lake", "Tercer Lake", "Tesla Lake", "Tetachuck Lake",
    "Tezzeron Lake", "Thletelban Lake", "Thompson Lake", "Tlutlias Lake",
    "Tochcha Lake", "Tomas Lake", "Top Lake", "Trembleur Lake", "Triangle Lake",
    "Troitsa Lake", "Tsayakwacha Lake", "Tschick Lake", "Tsetoyank'ut Lake",
    "Tsichgass Lake", "Turff Lake", "Twinkle Lake", "Uduk Lake", "Uncha Lake",
    "Wahla Lake", "Wapoose Lake", "Webber Lake", "White Eye Lake",
    "Whitefish Lake", "Whitesail Lake", "Williamson Lake", "Willington Lake",
    "Wutak Lake", "Yatzutzin Lake", "Yellow Moose Lake",
]

# Search #3: Physiographic features
PHYSIOGRAPHY = [
    "Cariboo Heart Range", "Chikamin Range", "Coast Mountains", "Connelly Range",
    "Driftwood Range", "Fawnie Range", "Hazelton Mountains", "Henson Hills",
    "Hogem Ranges", "Holmes Ridge", "Interior Plateau", "Interior System",
    "Kasalka Range", "Kitimat Ranges", "Mitchell Range", "Mosquito Hills",
    "Murray Ridge", "Naglico Hills", "Nechako Plateau", "Nechako Range",
    "Omineca Mountains", "Pattullo Range", "Quanchus Range", "Sasklo Ridge",
    "Savory Ridge", "Shelford Hills", "Sibola Range", "Sitlika Range",
    "Skeena Mountains", "Tahtsa Ranges", "Takla Range", "Tatuk Hills",
    "Tekaiziyis Ridge", "Telegraph Range", "Tochquonyalla Range", "Tsaytut Spur",
    "Vital Range", "Western System", "Whitesail Range", "Windfall Hills",
]

# Search #4: Populated places
POPULATED_PLACES = [
    "Bulkley House", "Burns Lake", "Cheslatta", "Clemretta", "Colleymount",
    "Danskin", "Decker Lake", "Dog Creek", "Endako", "Fort Fraser",
    "Fort St. James", "Francois Lake", "Fraser Lake", "Grassy Plains",
    "Isle Pierre", "Leo Creek", "Mapes", "Marilla", "McDonalds Landing",
    "Middle River", "Miworth", "Mud River", "Nak'azdli", "Nautley", "Noralee",
    "Nulki", "Ootsa Lake", "Pinchi", "Pinchi Lake", "Punchaw", "Reid Lake",
    "Shady Valley", "Sinkut River", "Skins Lake", "Southbank", "Sowchea 3",
    "Stellako", "Stony Creek", "Sunnyside", "Tachie", "Takla Landing",
    "Takysie Lake", "Tatalrose", "Tatla't East", "Tchesinkut Lake", "Telachick",
    "Tintagel", "Vanderhoof", "Weneez", "Wet'suwet'en Village", "Wistaria",
    "Woyenne", "Yekooche",
]

# Search #5: Creeks and rivers
CREEKS_AND_RIVERS = [
    "Aird Creek", "Alf Creek", "Allen Creek", "Allin Creek", "Andrews Creek",
    "Angly Creek", "Ankwill Creek", "Arethusa Creek", "Aslin Creek",
    "Baker Creek", "Banguarel Creek", "Baptiste Creek", "Bates Creek",
    "Beach Creek", "Bearcub Creek", "Beaverdale Creek", "Beaverdam Creek",
    "Beaverley Creek", "Belisle Creek", "Belzile Creek", "Benoit Creek",
    "Big Bend Creek", "Bird Creek", "Bivouac Creek", "Blackburne Creek",
    "Blanchet River", "Bone Creek", "Breadalbane Creek", "Breeze Creek",
    "Brooks Creek", "Burnstead Creek", "Butcherflats Creek", "Butterfield Creek",
    "Cabin Creek", "Campbell Creek", "Camsell Creek", "Capoose Creek",
    "Chedakuz Creek", "Chehischic Creek", "Chelaslie River", "Cheskwa Creek",
    "Cheslatta River", "Chezko River", "Chikamin Creek", "Chilako River",
    "Chilco Creek", "Chillo Creek", "Chinohchey Creek", "Chowsunkut Creek",
    "Clarke Creek", "Clatlatiently Creek", "Clear Creek", "Cluculz Creek",
    "Coles Creek", "Colley Creek", "Comb Creek", "Cordella Creek",
    "Corkscrew Creek", "Cranberry Creek", "Cripple Creek", "Croft Creek",
    "Cummins Creek", "Cutoff Creek", "Dahl Creek", "Dan Miner Creek",
    "Davidson Creek", "Decker Creek", "Dodd Creek", "Dog Creek", "Dorman Creek",
    "Driftwood River", "Dust Creek", "Eagle Creek", "East Erhorn Creek",
    "East Moxley Creek", "East Murray Creek", "East Negaard Creek",
    "East Side Creek", "Eastern Creek", "Ed Creek", "Eden Creek", "Endako River",
    "Engen Creek", "Engstrom Creek", "Entiako River", "Erhorn Creek",
    "Esker Creek", "Evans Creek", "Fawnie Creek", "Fifteen Creek",
    "Finger Creek", "Fleming Creek", "Foster Creek", "Four Mile Creek",
    "Frypan Creek", "Fyfe Creek", "Garvin Creek", "Gauvin Creek", "Gerow Creek",
    "Gesul Buhn Creek", "Gilbert Creek", "Gloyazikut Creek", "Goldie Creek",
    "Goodwin Creek", "Graham Creek", "Gravel Creek", "Greer Creek",
    "Gregg Creek", "Grostete Creek", "Guyishton Creek", "Halsey Creek",
    "Hatdudatehl Creek", "Haut\u00eate Creek", "Hawley Creek", "Henkel Creek",
    "Hogsback Creek", "Hudson Bay Creek", "Hulatt Creek", "Hutchison Creek",
    "Hyman Creek", "Inzana Creek", "Isaac Creek", "Jack Weekes Creek",
    "Janz\u00ea Creek", "Kasalka Creek", "Kazchek Creek", "Kec Creek",
    "Kellogg Creek", "Khai Creek", "Kinowsa Creek", "Kivi Creek",
    "Kleedlee Creek", "Klinsake Creek", "Kloch Creek", "Kluk Creek",
    "Knapp Creek", "Knight Creek", "Kuzkwa River", "Lakes Creek",
    "Laventie Creek", "Lavoie Creek", "Leduc Creek", "Leigh Creek", "Leo Creek",
    "Leona Creek", "Little Bobtail Creek", "Lovell Creek", "Lucas Creek",
    "Macdougall Creek", "MacIvor Creek", "Maclaing Creek", "Maltby Creek",
    "Mandalay Creek", "Marie Creek", "Martens Creek", "Mathews Creek",
    "McCuish Creek", "McDonald Creek", "McIntosh Creek", "McKay Creek",
    "McKenzie Creek", "McMillan Creek", "Michel Creek", "Micks Creek",
    "Middle River", "Millard Creek", "Moss Creek", "Moxley Creek",
    "Mudhole Creek", "Murray Creek", "Nadina River", "Nahounli Creek",
    "Nancut Creek", "Nankuz Creek", "Natazutlo Creek", "Nechako River",
    "Necoslie River", "Negaard Creek", "Neuco Creek", "Nielsp Creek",
    "Nine Mile Creek", "Nithi River", "Nizik Creek", "Norman Creek",
    "North Stony Creek", "O'Ne-ell Creek", "Ocock River", "Ohr Creek",
    "Olie Creek", "Ormond Creek", "Parkland Creek", "Parrott Creek",
    "Paula Creek", "Peace Creek", "Perry Creek", "Peta Creek",
    "Peter Aleck Creek", "Phillips Creek", "Pinchi Creek", "Pitka Creek",
    "Poplar Creek", "Powder House Creek", "Prairie Meadow Creek",
    "Preston Creek", "Puttah Creek", "Ramsay Creek", "Redmond Creek",
    "Relief Creek", "Rentoul Creek", "Rhine Creek", "Robertson Creek",
    "Rubyrock Creek", "Sakeniche River", "Sam Ross Creek", "Sandifer Creek",
    "Sauls Creek", "Saxton Creek", "Schjelderup Creek", "Shelford Creek",
    "Sheraton Creek", "Shillestead Brook", "Short Creek", "Shotgun Creek",
    "Shovel Creek", "Sibola Creek", "Sidney Creek", "Sinkut River",
    "Sinta Creek", "Sitlika Creek", "Small Trout Creek", "Smith Creek",
    "Snodgrass Creek", "Sob Creek", "South Creek", "South Goldie Creek",
    "Sowchea Creek", "Specularite Creek", "Spencha Creek", "St. George Creek",
    "St. Thomas River", "Stearns Creek", "Stellako River", "Stern Creek",
    "Stony Creek", "Stuart River", "Swanson Creek", "Sweden Creek",
    "Sweetnam Creek", "Tachick Creek", "Tachie River", "Tachintelachick Creek",
    "Tagetochlain Creek", "Taginchil Creek", "Tahultzu Creek", "Takatoot Creek",
    "Takysie Creek", "Targe Creek", "Tarnezell Creek", "Taslincheko Creek",
    "Tatalaska Creek", "Tatalrose Creek", "Tatin Creek", "Tatsutnai Creek",
    "Tatuk Creek", "Tchesinkut Creek", "Tesla Creek", "Tetachuck River",
    "Tezzeron Creek", "Tibbets Creek", "Tildesley Creek", "Tintagel Creek",
    "Tliti Creek", "Tlutlias Creek", "Totem Pole Creek", "Trankle Creek",
    "Tritt Creek", "Troitsa Creek", "Tsah Creek", "Tsilcoh River",
    "Tsitsutl Creek", "Tultsau Creek", "Ucausley Creek", "Uncha Creek",
    "Upper Moss Creek", "Van Decar Creek", "Van Lear Creek", "Van Tine Creek",
    "Wardrop Creek", "Webber Creek", "Wells Creek", "West Engen Creek",
    "West Tarnezell Creek", "Whitefish Creek", "Whiting Creek",
    "Wilhelmsen Creek", "Willowy Creek", "Wynkes Creek", "Zelkwas Creek",
]

# Line 8: Regional filter (ALL fields, not Topic Search)
REGIONAL_FILTER = ["British Columbia", "Canada"]

# All categories combined (for building the full search)
TERRY_SEARCH_TERMS: Dict[str, List[str]] = {
    "key_places": KEY_PLACES,
    "first_nations": FIRST_NATIONS,
    "lakes": LAKES,
    "physiography": PHYSIOGRAPHY,
    "populated_places": POPULATED_PLACES,
    "creeks_and_rivers": CREEKS_AND_RIVERS,
}

# Known false positive terms from the screening protocol (Table 2)
# These terms match locations outside the Nechako Watershed
KNOWN_FALSE_POSITIVE_TERMS = {
    "Allen Creek": "Florida/New Brunswick",
    "Baker Creek": "Northwest Territories",
    "Bear Lake": "Utah / Northwest Territories",
    "Clear Creek": "California",
    "Cripple Creek": "Colorado",
    "Crystal Lake": "Connecticut, Wisconsin, Illinois",
    "Fish Lake": "Minnesota, Oregon, Utah, Wisconsin",
    "Four Mile Creek": "Alaska",
    "Goodwin Creek": "Mississippi",
    "Gordon Lake": "Ontario",
    "Hanson Lake": "Saskatchewan",
    "Harp Lake": "Ontario",
    "Horseshoe Lake": "Illinois",
    "Island Lake": "Manitoba, Ontario, Saskatchewan, Taiwan, Texas",
    "Long Lake": "Multiple states and provinces",
    "Mapes": "Author name / MAPES acronym",
    "Moose Lake": "New York",
    "Murray Ridge": "Mars",
    "Poplar Creek": "Tennessee",
    "Prince George": "Maryland",
    "Redfish Lake": "Idaho",
    "Sunnyside": "Various",
    "Western System": "Generic phrase (e.g., western system of medicine)",
}


def get_all_terry_terms() -> Set[str]:
    """Get all unique terms from Terry's search (deduplicated across categories)."""
    all_terms = set()
    for terms in TERRY_SEARCH_TERMS.values():
        all_terms.update(terms)
    return all_terms


def get_terry_term_count() -> int:
    """Get the count of unique terms in Terry's search."""
    return len(get_all_terry_terms())


def build_terry_wos_query_parts() -> List[str]:
    """
    Build the individual TS= query parts matching Terry's exact search.
    Returns a list of TS=(...) strings, one per category.
    """
    parts = []
    for category, terms in TERRY_SEARCH_TERMS.items():
        quoted = " OR ".join([f'"{t}"' for t in terms])
        parts.append(f'TS=({quoted})')
    return parts


if __name__ == "__main__":
    print("TERRY'S EXACT WOS SEARCH TERMS")
    print("=" * 50)
    for cat, terms in TERRY_SEARCH_TERMS.items():
        print(f"  {cat}: {len(terms)} terms")
    total = get_terry_term_count()
    print(f"  Total unique: {total}")
    print(f"\n  Regional filter: ALL=({' OR '.join(REGIONAL_FILTER)})")
    print(f"  Known false positives: {len(KNOWN_FALSE_POSITIVE_TERMS)} terms")
