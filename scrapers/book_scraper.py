"""
Book scraper for extracting content from publicly available books and excerpts.
"""
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from loguru import logger

from scrapers.base_scraper import BaseScraper


class BookScraper(BaseScraper):
    """Scraper for book content from web sources."""

    def __init__(self, author_id: str, author_config: Dict[str, Any]):
        """Initialize book scraper."""
        super().__init__(author_id, author_config)

        self.books = author_config.get('books', [])
        if not self.books:
            logger.warning(f"No books found for {author_id}")

    def scrape(
        self,
        book_title: Optional[str] = None,
        max_chapters: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Scrape book content.

        Args:
            book_title: Specific book to scrape (None for all)
            max_chapters: Maximum chapters to scrape per book

        Returns:
            List of content objects
        """
        all_content = []

        for book in self.books:
            title = book.get('title')

            # Filter by specific book if requested
            if book_title and title != book_title:
                continue

            logger.info(f"Scraping book: {title}")

            try:
                # Check if publicly available
                if not book.get('publicly_available', True):
                    logger.warning(f"Book '{title}' not marked as publicly available. Skipping.")
                    continue

                # Scrape based on book type
                book_type = book.get('type', 'excerpts')

                if book_type == 'online':
                    # Full online book (like The Network State)
                    content = self._scrape_online_book(book, max_chapters)
                elif book_type == 'excerpts':
                    # Blog excerpts
                    content = self._scrape_excerpts(book, max_chapters)
                else:
                    logger.warning(f"Unknown book type: {book_type}")
                    continue

                all_content.extend(content)

            except Exception as e:
                logger.error(f"Failed to scrape book {title}: {e}", exc_info=True)

        logger.info(f"Scraped {len(all_content)} book sections for {self.author_name}")
        self.stats['items_scraped'] = len(all_content)

        return all_content

    def _scrape_online_book(
        self,
        book: Dict[str, Any],
        max_chapters: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Scrape a full online book (like The Network State)."""
        content = []
        book_title = book.get('title')
        book_url = book.get('url')

        try:
            # Fetch the main page
            response = self.fetch_url(book_url)
            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract table of contents or chapter links
            chapter_links = self._find_chapter_links(soup, book_url)

            logger.info(f"Found {len(chapter_links)} chapters in {book_title}")

            # Limit chapters if specified
            if max_chapters:
                chapter_links = chapter_links[:max_chapters]

            # Scrape each chapter
            for idx, (chapter_title, chapter_url) in enumerate(chapter_links, 1):
                try:
                    chapter_content = self._scrape_chapter(
                        chapter_url,
                        chapter_title,
                        book_title,
                        idx
                    )

                    if chapter_content and self.validate_content(chapter_content):
                        content.append(chapter_content)
                        self.stats['items_scraped'] += 1
                    else:
                        self.stats['items_filtered'] += 1

                except Exception as e:
                    logger.warning(f"Failed to scrape chapter {chapter_title}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Failed to scrape online book {book_title}: {e}", exc_info=True)

        return content

    def _find_chapter_links(self, soup: BeautifulSoup, base_url: str) -> List[tuple]:
        """Find chapter links in a book's table of contents."""
        chapter_links = []

        # Look for common TOC patterns
        toc_selectors = [
            'nav#TableOfContents',
            'div.toc',
            'ul.chapters',
            'nav[role="navigation"]',
            'div#toc'
        ]

        toc = None
        for selector in toc_selectors:
            toc = soup.select_one(selector)
            if toc:
                break

        if not toc:
            # Try to find all links that look like chapters
            logger.debug("No TOC found, searching for chapter links")
            all_links = soup.find_all('a', href=True)
            for link in all_links:
                href = link['href']
                text = link.get_text(strip=True)
                # Heuristic: chapter links often contain numbers or "chapter"
                if text and (re.search(r'\d+', text) or 'chapter' in text.lower()):
                    full_url = urljoin(base_url, href)
                    chapter_links.append((text, full_url))
        else:
            # Extract links from TOC
            for link in toc.find_all('a', href=True):
                title = link.get_text(strip=True)
                url = urljoin(base_url, link['href'])
                if title:
                    chapter_links.append((title, url))

        return chapter_links

    def _scrape_chapter(
        self,
        url: str,
        title: str,
        book_title: str,
        chapter_num: int
    ) -> Optional[Dict[str, Any]]:
        """Scrape a single chapter."""
        try:
            response = self.fetch_url(url)
            soup = BeautifulSoup(response.content, 'html.parser')

            # Remove navigation, headers, footers
            for elem in soup(['nav', 'header', 'footer', 'script', 'style']):
                elem.decompose()

            # Find main content
            content = None
            content_selectors = [
                'article',
                'main',
                'div.content',
                'div.chapter',
                'div.post-content'
            ]

            for selector in content_selectors:
                elem = soup.select_one(selector)
                if elem:
                    content = self._clean_text(elem)
                    break

            if not content:
                # Fall back to body
                body = soup.find('body')
                if body:
                    content = self._clean_text(body)

            if not content:
                logger.warning(f"No content found for chapter: {title}")
                return None

            # Metadata
            metadata = {
                'book_title': book_title,
                'chapter_number': chapter_num,
                'chapter_title': title,
                'source': 'online_book'
            }

            # Create content object
            return self.create_content_object(
                title=f"{book_title} - Chapter {chapter_num}: {title}",
                content=content,
                url=url,
                date_published=None,  # Books don't have precise publish dates per chapter
                platform='book',
                content_type='chapter',
                metadata=metadata
            )

        except Exception as e:
            logger.error(f"Failed to scrape chapter {title}: {e}", exc_info=True)
            return None

    def _scrape_excerpts(
        self,
        book: Dict[str, Any],
        max_excerpts: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Scrape book excerpts from blog posts."""
        content = []
        book_title = book.get('title')
        excerpts_url = book.get('excerpts_url')

        if not excerpts_url:
            logger.warning(f"No excerpts URL for {book_title}")
            return content

        try:
            # This is typically a blog category/tag page
            response = self.fetch_url(excerpts_url)
            soup = BeautifulSoup(response.content, 'html.parser')

            # Find article links
            articles = soup.find_all('article', limit=max_excerpts)

            for article in articles:
                # Get article link
                title_elem = article.find(['h2', 'h3'], class_=re.compile('title'))
                if not title_elem:
                    continue

                link = title_elem.find('a')
                if not link or not link.get('href'):
                    continue

                article_url = link['href']
                article_title = link.get_text(strip=True)

                # Scrape the excerpt article
                try:
                    excerpt = self._scrape_excerpt_article(
                        article_url,
                        article_title,
                        book_title
                    )

                    if excerpt and self.validate_content(excerpt):
                        content.append(excerpt)
                        self.stats['items_scraped'] += 1
                    else:
                        self.stats['items_filtered'] += 1

                except Exception as e:
                    logger.warning(f"Failed to scrape excerpt {article_title}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Failed to scrape excerpts for {book_title}: {e}", exc_info=True)

        return content

    def _scrape_excerpt_article(
        self,
        url: str,
        title: str,
        book_title: str
    ) -> Optional[Dict[str, Any]]:
        """Scrape a blog post containing a book excerpt."""
        try:
            response = self.fetch_url(url)
            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract content
            content_elem = soup.select_one('div.entry-content, div.post-content, article')
            if not content_elem:
                return None

            content = self._clean_text(content_elem)

            # Extract date
            date_elem = soup.select_one('time, .entry-date')
            published_date = None
            if date_elem:
                date_str = date_elem.get('datetime') or date_elem.get_text(strip=True)
                try:
                    from dateutil import parser as date_parser
                    published_date = date_parser.parse(date_str)
                except:
                    pass

            # Metadata
            metadata = {
                'book_title': book_title,
                'excerpt_title': title,
                'source': 'blog_excerpt'
            }

            # Create content object
            return self.create_content_object(
                title=f"{book_title} - {title}",
                content=content,
                url=url,
                date_published=published_date,
                platform='book',
                content_type='excerpt',
                metadata=metadata
            )

        except Exception as e:
            logger.error(f"Failed to scrape excerpt article {url}: {e}", exc_info=True)
            return None

    def _clean_text(self, element) -> str:
        """Clean and extract text from HTML element."""
        # Remove unwanted elements
        for unwanted in element(['script', 'style', 'nav', 'footer', 'aside', 'iframe']):
            unwanted.decompose()

        # Get text
        text = element.get_text(separator='\n', strip=True)

        # Clean up whitespace
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r' +', ' ', text)

        return text.strip()
