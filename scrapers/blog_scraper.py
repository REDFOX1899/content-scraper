"""
Blog scraper for extracting articles from tim.blog and balajis.com.
"""
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from loguru import logger
from dateutil import parser as date_parser

from scrapers.base_scraper import BaseScraper
from config.settings import BLOG_SETTINGS, BLOG_SELECTORS
from utils.rate_limiter import delay


class BlogScraper(BaseScraper):
    """Scraper for blog posts from various blogs."""

    def __init__(self, author_id: str, author_config: Dict[str, Any]):
        """Initialize blog scraper."""
        super().__init__(author_id, author_config)
        self.blogs = author_config.get('blogs', [])

    def scrape(
        self,
        max_pages: Optional[int] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Scrape blog posts.

        Args:
            max_pages: Maximum number of pages to scrape
            date_from: Start date for filtering
            date_to: End date for filtering

        Returns:
            List of content objects
        """
        all_content = []

        for blog in self.blogs:
            blog_url = blog.get('url')
            blog_name = blog.get('name')

            logger.info(f"Scraping blog: {blog_name} ({blog_url})")

            try:
                content = self._scrape_blog(
                    blog_url,
                    blog_name,
                    max_pages=max_pages or BLOG_SETTINGS['max_pages'],
                    date_from=date_from,
                    date_to=date_to
                )
                all_content.extend(content)

            except Exception as e:
                logger.error(f"Failed to scrape {blog_name}: {e}", exc_info=True)

        logger.info(f"Scraped {len(all_content)} blog posts for {self.author_name}")
        self.stats['items_scraped'] = len(all_content)

        return all_content

    def _scrape_blog(
        self,
        blog_url: str,
        blog_name: str,
        max_pages: int,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Scrape a specific blog."""
        articles = []

        # Get domain for selector lookup
        domain = urlparse(blog_url).netloc.replace('www.', '')

        # Get article URLs from archive/index pages
        article_urls = self._get_article_urls(blog_url, domain, max_pages)

        logger.info(f"Found {len(article_urls)} article URLs from {blog_name}")

        # Scrape each article
        for url in article_urls:
            try:
                article = self._scrape_article(url, domain, blog_name)

                if article:
                    # Filter by date if specified
                    if date_from or date_to:
                        article_date = article.get('date_published')
                        if article_date:
                            article_dt = date_parser.parse(article_date)
                            if date_from and article_dt < date_from:
                                continue
                            if date_to and article_dt > date_to:
                                continue

                    if self.validate_content(article):
                        articles.append(article)
                        self.stats['items_scraped'] += 1
                    else:
                        self.stats['items_filtered'] += 1

                # Be respectful with delays
                delay(BLOG_SETTINGS['delay_between_requests'])

            except Exception as e:
                logger.warning(f"Failed to scrape article {url}: {e}")
                continue

        return articles

    def _get_article_urls(self, base_url: str, domain: str, max_pages: int) -> List[str]:
        """Get article URLs from blog index/archive pages."""
        article_urls = set()

        # Try different strategies based on the blog
        if 'tim.blog' in domain:
            article_urls = self._get_tim_blog_urls(base_url, max_pages)
        elif 'balajis.com' in domain:
            article_urls = self._get_balajis_blog_urls(base_url, max_pages)
        else:
            # Generic approach
            article_urls = self._get_generic_blog_urls(base_url, max_pages)

        return list(article_urls)

    def _get_tim_blog_urls(self, base_url: str, max_pages: int) -> set:
        """Get article URLs from tim.blog."""
        urls = set()

        # Tim Ferriss blog uses WordPress pagination
        for page_num in range(1, max_pages + 1):
            page_url = f"{base_url}/page/{page_num}/" if page_num > 1 else base_url

            try:
                response = self.fetch_url(page_url)
                soup = BeautifulSoup(response.content, 'html.parser')

                # Find article links
                articles = soup.find_all('article', class_=re.compile('post-'))
                if not articles:
                    logger.info(f"No more articles found at page {page_num}")
                    break

                for article in articles:
                    # Get the permalink
                    title_link = article.find('h2', class_='entry-title')
                    if title_link:
                        link = title_link.find('a')
                        if link and link.get('href'):
                            urls.add(link['href'])

                logger.debug(f"Found {len(articles)} articles on page {page_num}")

            except Exception as e:
                logger.warning(f"Failed to fetch page {page_num}: {e}")
                break

        return urls

    def _get_balajis_blog_urls(self, base_url: str, max_pages: int) -> set:
        """Get article URLs from balajis.com."""
        urls = set()

        try:
            response = self.fetch_url(base_url)
            soup = BeautifulSoup(response.content, 'html.parser')

            # Find all article links
            links = soup.find_all('a', href=True)
            for link in links:
                href = link['href']
                # Filter for article URLs
                if href.startswith('/') or base_url in href:
                    full_url = urljoin(base_url, href)
                    # Exclude non-article pages
                    if not any(x in full_url for x in ['#', 'tag', 'category', 'page']):
                        urls.add(full_url)

        except Exception as e:
            logger.error(f"Failed to get Balaji's blog URLs: {e}")

        return urls

    def _get_generic_blog_urls(self, base_url: str, max_pages: int) -> set:
        """Generic method to get article URLs."""
        urls = set()

        try:
            response = self.fetch_url(base_url)
            soup = BeautifulSoup(response.content, 'html.parser')

            # Look for common article link patterns
            for link in soup.find_all('a', href=True):
                href = link['href']
                full_url = urljoin(base_url, href)

                # Basic heuristics for article URLs
                if (full_url.startswith(base_url) and
                    not any(x in full_url for x in ['#', 'tag', 'category', 'author', 'page'])):
                    urls.add(full_url)

        except Exception as e:
            logger.error(f"Failed to get generic blog URLs: {e}")

        return urls

    def _scrape_article(self, url: str, domain: str, blog_name: str) -> Optional[Dict[str, Any]]:
        """Scrape a single article."""
        try:
            response = self.fetch_url(url)
            soup = BeautifulSoup(response.content, 'html.parser')

            # Get selectors for this domain
            selectors = BLOG_SELECTORS.get(domain, {})

            # Extract title
            title = self._extract_title(soup, selectors)

            # Extract content
            content = self._extract_content(soup, selectors)

            # Extract date
            date_published = self._extract_date(soup, selectors)

            # Extract metadata
            metadata = {
                'blog_name': blog_name,
                'domain': domain,
                'tags': self._extract_tags(soup),
                'categories': self._extract_categories(soup)
            }

            if not title or not content:
                logger.warning(f"Missing title or content for {url}")
                return None

            # Create content object
            return self.create_content_object(
                title=title,
                content=content,
                url=url,
                date_published=date_published,
                platform='blog',
                content_type='article',
                metadata=metadata
            )

        except Exception as e:
            logger.error(f"Failed to scrape article {url}: {e}", exc_info=True)
            return None

    def _extract_title(self, soup: BeautifulSoup, selectors: Dict) -> str:
        """Extract article title."""
        # Try selector
        if 'title' in selectors:
            title_elem = soup.select_one(selectors['title'])
            if title_elem:
                return title_elem.get_text(strip=True)

        # Fallback: try common patterns
        for selector in ['h1.entry-title', 'h1.post-title', 'h1', 'title']:
            elem = soup.select_one(selector)
            if elem:
                return elem.get_text(strip=True)

        return ""

    def _extract_content(self, soup: BeautifulSoup, selectors: Dict) -> str:
        """Extract article content."""
        # Try selector
        if 'content' in selectors:
            content_elem = soup.select_one(selectors['content'])
            if content_elem:
                return self._clean_content(content_elem)

        # Fallback: try common patterns
        for selector in ['div.entry-content', 'div.post-content', 'article', 'main']:
            elem = soup.select_one(selector)
            if elem:
                return self._clean_content(elem)

        return ""

    def _clean_content(self, element) -> str:
        """Clean and extract text from content element."""
        # Remove script and style elements
        for script in element(['script', 'style', 'nav', 'footer', 'aside']):
            script.decompose()

        # Get text with some structure preserved
        text = element.get_text(separator='\n', strip=True)

        # Clean up extra whitespace
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r' +', ' ', text)

        return text.strip()

    def _extract_date(self, soup: BeautifulSoup, selectors: Dict) -> Optional[datetime]:
        """Extract publication date."""
        # Try selector
        if 'date' in selectors:
            date_elem = soup.select_one(selectors['date'])
            if date_elem:
                date_str = date_elem.get('datetime') or date_elem.get_text(strip=True)
                try:
                    return date_parser.parse(date_str)
                except:
                    pass

        # Try common patterns
        for selector in ['time', 'meta[property="article:published_time"]', '.entry-date']:
            elem = soup.select_one(selector)
            if elem:
                date_str = elem.get('datetime') or elem.get('content') or elem.get_text(strip=True)
                try:
                    return date_parser.parse(date_str)
                except:
                    pass

        return None

    def _extract_tags(self, soup: BeautifulSoup) -> List[str]:
        """Extract article tags."""
        tags = []

        # Try common tag patterns
        tag_elems = soup.select('.tag, .tags a, [rel="tag"]')
        for elem in tag_elems:
            tag = elem.get_text(strip=True)
            if tag:
                tags.append(tag)

        return tags

    def _extract_categories(self, soup: BeautifulSoup) -> List[str]:
        """Extract article categories."""
        categories = []

        # Try common category patterns
        cat_elems = soup.select('.category, .categories a, [rel="category"]')
        for elem in cat_elems:
            cat = elem.get_text(strip=True)
            if cat:
                categories.append(cat)

        return categories
