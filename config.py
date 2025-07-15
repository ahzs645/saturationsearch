"""
Configuration settings for the Nechako Saturation Search automation system.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# API Configuration
WOS_API_KEY = os.getenv('WOS_API_KEY')
SCOPUS_API_KEY = os.getenv('SCOPUS_API_KEY')
ZOTERO_API_KEY = os.getenv('ZOTERO_API_KEY')
ZOTERO_LIBRARY_ID = os.getenv('ZOTERO_LIBRARY_ID')
ZOTERO_LIBRARY_TYPE = os.getenv('ZOTERO_LIBRARY_TYPE', 'group')

# Search Configuration
DEFAULT_DATE_START = "1930-01-01"
DEFAULT_LANGUAGE = "English"
GEOGRAPHIC_FILTER = '("Canada" OR "British Columbia")'

# Quality Thresholds
TITLE_SIMILARITY_THRESHOLD = 0.95
ABSTRACT_SIMILARITY_THRESHOLD = 0.85
CONFIDENCE_THRESHOLD = 0.8
MANUAL_REVIEW_THRESHOLD = 0.8

# Processing Configuration
MAX_RESULTS_PER_SEARCH = 1000
BATCH_SIZE = 100
API_RATE_LIMIT_DELAY = 1.0  # seconds

# File Paths
LOCATION_TERMS_FILE = "data/location_terms.json"
BASELINE_ARTICLES_FILE = "data/baseline_748_articles.json"
SEARCH_RESULTS_DIR = "results/"
LOGS_DIR = "logs/"

# Theme Classification
THEMES = ["Environment", "Community", "Health"]

# Exclusion Criteria Keywords
UNBC_EXCLUSION_KEYWORDS = [
    "timber engineering",
    "forestry engineering", 
    "astronomy",
    "astrophysics",
    "software engineering",
    "computer science"
]

# Logging Configuration
LOG_LEVEL = "INFO"
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'