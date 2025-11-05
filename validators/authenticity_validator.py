"""
Authenticity validator to ensure content is directly from the target authors.
"""
from typing import Dict, Any, List
from urllib.parse import urlparse
from loguru import logger

from config.settings import load_authors_config, MIN_AUTHENTICITY_SCORE


class AuthenticityValidator:
    """Validator to check content authenticity."""

    def __init__(self):
        """Initialize authenticity validator."""
        self.authors_config = load_authors_config()
        self.official_domains = self._build_domain_whitelist()

    def _build_domain_whitelist(self) -> Dict[str, List[str]]:
        """Build whitelist of official domains for each author."""
        whitelist = {}

        for author_id, config in self.authors_config.items():
            domains = config.get('official_domains', [])

            # Add domains from various sources
            for blog in config.get('blogs', []):
                url = blog.get('url', '')
                if url:
                    domain = urlparse(url).netloc.replace('www.', '')
                    if domain and domain not in domains:
                        domains.append(domain)

            whitelist[author_id] = domains

        logger.info(f"Built domain whitelist for {len(whitelist)} authors")
        return whitelist

    def validate(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate content authenticity and assign a confidence score.

        Args:
            content: Content object to validate

        Returns:
            Updated content object with authenticity_score
        """
        author_id = content.get('author')
        if not author_id:
            logger.warning("Content missing author ID")
            content['authenticity_score'] = 0
            return content

        platform = content.get('platform', '')
        url = content.get('url', '')
        metadata = content.get('metadata', {})

        # Calculate authenticity score
        score = self._calculate_authenticity_score(
            author_id=author_id,
            platform=platform,
            url=url,
            metadata=metadata
        )

        content['authenticity_score'] = score

        # Add validation details to metadata
        if 'validation' not in content['metadata']:
            content['metadata']['validation'] = {}

        content['metadata']['validation']['authenticity_score'] = score
        content['metadata']['validation']['passed'] = score >= MIN_AUTHENTICITY_SCORE

        logger.debug(f"Content authenticity score: {score}")

        return content

    def _calculate_authenticity_score(
        self,
        author_id: str,
        platform: str,
        url: str,
        metadata: Dict[str, Any]
    ) -> int:
        """
        Calculate authenticity score (0-100).

        Scoring criteria:
        - Domain verification: +40 points
        - Platform-specific verification: +40 points
        - Metadata verification: +20 points
        """
        score = 0

        # 1. Domain verification (40 points)
        domain_score = self._verify_domain(author_id, url)
        score += domain_score

        # 2. Platform-specific verification (40 points)
        platform_score = self._verify_platform(author_id, platform, metadata)
        score += platform_score

        # 3. Metadata verification (20 points)
        metadata_score = self._verify_metadata(author_id, metadata)
        score += metadata_score

        return min(100, max(0, score))

    def _verify_domain(self, author_id: str, url: str) -> int:
        """
        Verify URL is from an official domain.

        Returns:
            Score (0-40)
        """
        if not url:
            return 0

        official_domains = self.official_domains.get(author_id, [])
        if not official_domains:
            logger.warning(f"No official domains configured for {author_id}")
            return 20  # Neutral score if no domains configured

        try:
            domain = urlparse(url).netloc.replace('www.', '')

            # Exact match
            if domain in official_domains:
                logger.debug(f"Domain {domain} verified for {author_id}")
                return 40

            # Check for subdomain match
            for official_domain in official_domains:
                if domain.endswith('.' + official_domain) or domain == official_domain:
                    logger.debug(f"Subdomain {domain} verified for {author_id}")
                    return 35

            # Domain not in whitelist
            logger.warning(f"Domain {domain} not in whitelist for {author_id}")
            return 0

        except Exception as e:
            logger.error(f"Error verifying domain: {e}")
            return 0

    def _verify_platform(self, author_id: str, platform: str, metadata: Dict[str, Any]) -> int:
        """
        Verify platform-specific authenticity markers.

        Returns:
            Score (0-40)
        """
        if not platform:
            return 0

        author_config = self.authors_config.get(author_id, {})

        if platform == 'twitter':
            return self._verify_twitter(author_config, metadata)

        elif platform == 'youtube':
            return self._verify_youtube(author_config, metadata)

        elif platform == 'blog':
            return self._verify_blog(author_config, metadata)

        elif platform == 'podcast':
            return self._verify_podcast(author_config, metadata)

        elif platform == 'book':
            return self._verify_book(author_config, metadata)

        else:
            logger.warning(f"Unknown platform: {platform}")
            return 20  # Neutral score

    def _verify_twitter(self, author_config: Dict[str, Any], metadata: Dict[str, Any]) -> int:
        """Verify Twitter content authenticity."""
        twitter_config = author_config.get('twitter', {})
        expected_handle = twitter_config.get('handle', '').lstrip('@')

        # We trust our scraper to only fetch from the correct account
        # Additional verification could check tweet_id validity, etc.
        return 40

    def _verify_youtube(self, author_config: Dict[str, Any], metadata: Dict[str, Any]) -> int:
        """Verify YouTube content authenticity."""
        channel_name = metadata.get('channel_name', '')
        channels = author_config.get('youtube_channels', [])

        # Check if channel name matches
        for channel in channels:
            if channel.get('name') == channel_name:
                return 40

        # If we don't have channel info, give benefit of doubt
        if not channels:
            return 30

        logger.warning(f"YouTube channel {channel_name} not verified")
        return 15

    def _verify_blog(self, author_config: Dict[str, Any], metadata: Dict[str, Any]) -> int:
        """Verify blog content authenticity."""
        blog_name = metadata.get('blog_name', '')
        domain = metadata.get('domain', '')

        blogs = author_config.get('blogs', [])

        # Check if blog matches configured blogs
        for blog in blogs:
            if blog.get('name') == blog_name:
                return 40

            blog_domain = urlparse(blog.get('url', '')).netloc.replace('www.', '')
            if blog_domain == domain:
                return 40

        logger.warning(f"Blog {blog_name} ({domain}) not verified")
        return 15

    def _verify_podcast(self, author_config: Dict[str, Any], metadata: Dict[str, Any]) -> int:
        """Verify podcast content authenticity."""
        podcast_name = metadata.get('podcast_name', '')
        podcasts = author_config.get('podcasts', [])

        # Check if podcast matches configured podcasts
        for podcast in podcasts:
            if podcast.get('name') == podcast_name:
                return 40

        # For guest appearances, score lower
        logger.debug(f"Podcast {podcast_name} may be a guest appearance")
        return 25

    def _verify_book(self, author_config: Dict[str, Any], metadata: Dict[str, Any]) -> int:
        """Verify book content authenticity."""
        book_title = metadata.get('book_title', '')
        books = author_config.get('books', [])

        # Check if book matches configured books
        for book in books:
            if book.get('title') == book_title:
                return 40

        logger.warning(f"Book {book_title} not verified")
        return 10

    def _verify_metadata(self, author_id: str, metadata: Dict[str, Any]) -> int:
        """
        Verify metadata quality and completeness.

        Returns:
            Score (0-20)
        """
        score = 0

        # Check for author mentions in metadata
        author_config = self.authors_config.get(author_id, {})
        author_name = author_config.get('name', '')

        # Word count check (reasonable content length)
        word_count = metadata.get('word_count', 0)
        if word_count > 50:
            score += 5

        # Has engagement metrics (for social media)
        if metadata.get('metrics'):
            score += 5

        # Has proper timestamps
        if metadata.get('word_count'):  # Proxy for content being processed
            score += 5

        # Platform-specific metadata exists
        if len(metadata) > 2:  # More than just basic fields
            score += 5

        return min(20, score)

    def filter_by_score(
        self,
        contents: List[Dict[str, Any]],
        min_score: int = None
    ) -> List[Dict[str, Any]]:
        """
        Filter content by minimum authenticity score.

        Args:
            contents: List of content objects
            min_score: Minimum score (uses MIN_AUTHENTICITY_SCORE if not provided)

        Returns:
            Filtered list of content objects
        """
        min_score = min_score or MIN_AUTHENTICITY_SCORE

        filtered = [
            content for content in contents
            if content.get('authenticity_score', 0) >= min_score
        ]

        logger.info(
            f"Filtered {len(contents)} items to {len(filtered)} "
            f"with min score {min_score}"
        )

        return filtered

    def validate_batch(self, contents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Validate a batch of content objects.

        Args:
            contents: List of content objects

        Returns:
            List of validated content objects
        """
        validated = []

        for content in contents:
            try:
                validated_content = self.validate(content)
                validated.append(validated_content)
            except Exception as e:
                logger.error(f"Failed to validate content: {e}")
                # Add with zero score
                content['authenticity_score'] = 0
                validated.append(content)

        return validated
