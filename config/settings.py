"""
Configuration settings for the content scraper system.
"""
import os
import json
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# API Keys
TWITTER_API_KEY = os.getenv('TWITTER_API_KEY')
TWITTER_API_SECRET = os.getenv('TWITTER_API_SECRET')
TWITTER_ACCESS_TOKEN = os.getenv('TWITTER_ACCESS_TOKEN')
TWITTER_ACCESS_TOKEN_SECRET = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
TWITTER_BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN')

YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

PINECONE_API_KEY = os.getenv('PINECONE_API_KEY')
PINECONE_ENVIRONMENT = os.getenv('PINECONE_ENVIRONMENT')
WEAVIATE_URL = os.getenv('WEAVIATE_URL')
WEAVIATE_API_KEY = os.getenv('WEAVIATE_API_KEY')

# Database
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///data/content_scraper.db')

# Scraping Configuration
USER_AGENT = os.getenv('USER_AGENT', 'ContentScraperBot/1.0')
REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '30'))
MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
RATE_LIMIT_CALLS = int(os.getenv('RATE_LIMIT_CALLS', '10'))
RATE_LIMIT_PERIOD = int(os.getenv('RATE_LIMIT_PERIOD', '60'))

# Logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.getenv('LOG_FILE', 'logs/scraper.log')

# Processing
CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', '1000'))
CHUNK_OVERLAP = int(os.getenv('CHUNK_OVERLAP', '200'))
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'text-embedding-ada-002')
MAX_WORKERS = int(os.getenv('MAX_WORKERS', '5'))

# Content Filtering
MIN_AUTHENTICITY_SCORE = int(os.getenv('MIN_AUTHENTICITY_SCORE', '75'))
MIN_CONTENT_LENGTH = int(os.getenv('MIN_CONTENT_LENGTH', '100'))

# Data directories
DATA_DIR = BASE_DIR / 'data'
RAW_DATA_DIR = DATA_DIR / 'raw'
PROCESSED_DATA_DIR = DATA_DIR / 'processed'
LOGS_DIR = BASE_DIR / 'logs'

# Create directories if they don't exist
for directory in [DATA_DIR, RAW_DATA_DIR, PROCESSED_DATA_DIR, LOGS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Authors configuration
AUTHORS_CONFIG_PATH = BASE_DIR / 'config' / 'authors.json'


def load_authors_config() -> Dict[str, Any]:
    """Load authors configuration from JSON file."""
    with open(AUTHORS_CONFIG_PATH, 'r') as f:
        return json.load(f)


def get_author_config(author_id: str) -> Dict[str, Any]:
    """Get configuration for a specific author."""
    authors = load_authors_config()
    if author_id not in authors:
        raise ValueError(f"Author '{author_id}' not found in configuration")
    return authors[author_id]


# HTTP Headers
DEFAULT_HEADERS = {
    'User-Agent': USER_AGENT,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}

# Platform-specific settings
YOUTUBE_SETTINGS = {
    'max_results': 50,
    'order': 'date',
    'type': 'video'
}

TWITTER_SETTINGS = {
    'max_results': 100,
    'tweet_fields': ['created_at', 'public_metrics', 'conversation_id', 'referenced_tweets'],
    'expansions': ['author_id', 'referenced_tweets.id']
}

BLOG_SETTINGS = {
    'timeout': REQUEST_TIMEOUT,
    'max_pages': 100,
    'delay_between_requests': 2
}

PODCAST_SETTINGS = {
    'download_audio': False,  # Set to True to download audio files
    'transcribe': False  # Set to True to transcribe audio without transcripts
}

# Content extraction selectors (CSS/XPath)
BLOG_SELECTORS = {
    'tim.blog': {
        'article': 'article.post',
        'title': 'h1.entry-title',
        'content': 'div.entry-content',
        'date': 'time.entry-date',
        'author': 'span.author'
    },
    'balajis.com': {
        'article': 'article',
        'title': 'h1',
        'content': 'div.content',
        'date': 'time',
        'author': 'meta[name="author"]'
    }
}

# Embedding configuration
EMBEDDING_CONFIG = {
    'model': EMBEDDING_MODEL,
    'batch_size': 100,
    'max_tokens': 8191
}

# Vector store configuration
VECTOR_STORE_CONFIG = {
    'index_name': 'content-scraper',
    'dimension': 1536,  # for text-embedding-ada-002
    'metric': 'cosine',
    'namespace': 'default'
}
