"""
Base scraper class with common functionality for all platform scrapers.
"""
import hashlib
import requests
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from config.settings import (
    DEFAULT_HEADERS,
    REQUEST_TIMEOUT,
    MAX_RETRIES,
    RATE_LIMIT_CALLS,
    RATE_LIMIT_PERIOD
)
from utils.rate_limiter import RateLimiter


class BaseScraper(ABC):
    """Abstract base class for all content scrapers."""

    def __init__(self, author_id: str, author_config: Dict[str, Any]):
        """
        Initialize base scraper.

        Args:
            author_id: Unique identifier for the author
            author_config: Configuration dictionary for the author
        """
        self.author_id = author_id
        self.author_config = author_config
        self.author_name = author_config.get('name', author_id)

        # Set up session with retry logic
        self.session = self._create_session()

        # Rate limiter
        self.rate_limiter = RateLimiter(RATE_LIMIT_CALLS, RATE_LIMIT_PERIOD)

        # Robot parser cache
        self.robot_parsers: Dict[str, RobotFileParser] = {}

        # Statistics
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'items_scraped': 0,
            'items_filtered': 0
        }

        logger.info(f"Initialized {self.__class__.__name__} for {self.author_name}")

    def _create_session(self) -> requests.Session:
        """Create a requests session with retry logic."""
        session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=MAX_RETRIES,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Set default headers
        session.headers.update(DEFAULT_HEADERS)

        return session

    def _get_robot_parser(self, url: str) -> Optional[RobotFileParser]:
        """
        Get robot parser for a domain.

        Args:
            url: URL to get robot parser for

        Returns:
            RobotFileParser instance or None if unavailable
        """
        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

        if base_url not in self.robot_parsers:
            robots_url = f"{base_url}/robots.txt"
            try:
                rp = RobotFileParser()
                rp.set_url(robots_url)
                rp.read()
                self.robot_parsers[base_url] = rp
                logger.debug(f"Loaded robots.txt from {robots_url}")
            except Exception as e:
                logger.warning(f"Could not load robots.txt from {robots_url}: {e}")
                self.robot_parsers[base_url] = None

        return self.robot_parsers[base_url]

    def can_fetch(self, url: str) -> bool:
        """
        Check if URL can be fetched according to robots.txt.

        Args:
            url: URL to check

        Returns:
            True if URL can be fetched, False otherwise
        """
        rp = self._get_robot_parser(url)
        if rp is None:
            return True  # Allow if robots.txt unavailable
        return rp.can_fetch(DEFAULT_HEADERS['User-Agent'], url)

    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((requests.RequestException, ConnectionError))
    )
    def fetch_url(self, url: str, method: str = 'GET', **kwargs) -> requests.Response:
        """
        Fetch a URL with retry logic and rate limiting.

        Args:
            url: URL to fetch
            method: HTTP method (GET, POST, etc.)
            **kwargs: Additional arguments to pass to requests

        Returns:
            Response object

        Raises:
            requests.RequestException: If request fails after retries
        """
        # Check robots.txt
        if not self.can_fetch(url):
            logger.warning(f"URL blocked by robots.txt: {url}")
            raise ValueError(f"URL blocked by robots.txt: {url}")

        # Apply rate limiting
        self.rate_limiter.wait_if_needed()

        # Set timeout if not provided
        if 'timeout' not in kwargs:
            kwargs['timeout'] = REQUEST_TIMEOUT

        # Make request
        try:
            self.stats['total_requests'] += 1
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            self.stats['successful_requests'] += 1
            logger.debug(f"Successfully fetched {url}")
            return response

        except requests.RequestException as e:
            self.stats['failed_requests'] += 1
            logger.error(f"Failed to fetch {url}: {e}")
            raise

    def generate_content_id(self, content: str, url: str = "") -> str:
        """
        Generate a unique ID for content.

        Args:
            content: Content text
            url: URL of the content

        Returns:
            Unique content ID
        """
        combined = f"{url}:{content[:1000]}"
        return hashlib.sha256(combined.encode()).hexdigest()

    def create_content_object(
        self,
        title: str,
        content: str,
        url: str,
        date_published: Optional[datetime] = None,
        platform: str = "",
        content_type: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a standardized content object.

        Args:
            title: Content title
            content: Main content text
            url: Source URL
            date_published: Publication date
            platform: Platform name (twitter, youtube, blog, etc.)
            content_type: Type of content (post, video, article, etc.)
            metadata: Additional metadata

        Returns:
            Standardized content dictionary
        """
        content_id = self.generate_content_id(content, url)

        content_obj = {
            'id': content_id,
            'author': self.author_id,
            'author_name': self.author_name,
            'platform': platform,
            'content_type': content_type,
            'title': title,
            'content': content,
            'url': url,
            'date_published': date_published.isoformat() if date_published else None,
            'date_scraped': datetime.now().isoformat(),
            'authenticity_score': None,  # To be filled by validator
            'metadata': metadata or {},
            'embeddings': [],
            'processed': False
        }

        # Add word count
        content_obj['metadata']['word_count'] = len(content.split())

        return content_obj

    def validate_content(self, content_obj: Dict[str, Any]) -> bool:
        """
        Perform basic validation on scraped content.

        Args:
            content_obj: Content object to validate

        Returns:
            True if content is valid, False otherwise
        """
        # Check required fields
        required_fields = ['title', 'content', 'url']
        for field in required_fields:
            if not content_obj.get(field):
                logger.warning(f"Content missing required field: {field}")
                return False

        # Check minimum content length
        from config.settings import MIN_CONTENT_LENGTH
        if len(content_obj['content']) < MIN_CONTENT_LENGTH:
            logger.debug(f"Content too short: {len(content_obj['content'])} chars")
            return False

        return True

    def get_stats(self) -> Dict[str, int]:
        """Get scraper statistics."""
        return self.stats.copy()

    def reset_stats(self):
        """Reset scraper statistics."""
        for key in self.stats:
            self.stats[key] = 0

    @abstractmethod
    def scrape(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Scrape content from the platform.

        This method must be implemented by each platform-specific scraper.

        Returns:
            List of content objects
        """
        pass

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close session."""
        self.session.close()
        if exc_type:
            logger.error(f"Scraper exited with error: {exc_val}")
        return False
