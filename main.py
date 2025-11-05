#!/usr/bin/env python3
"""
Main orchestrator and CLI for the content scraper system.
"""
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import click
from loguru import logger
from tqdm import tqdm

from config.settings import (
    load_authors_config,
    get_author_config,
    LOG_LEVEL,
    LOG_FILE,
    LOGS_DIR
)
from scrapers.blog_scraper import BlogScraper
from scrapers.twitter_scraper import TwitterScraper
from scrapers.youtube_scraper import YouTubeScraper
from scrapers.podcast_scraper import PodcastScraper
from scrapers.book_scraper import BookScraper
from validators.authenticity_validator import AuthenticityValidator
from storage.database import ContentDatabase
from storage.vector_store import create_vector_store
from processing.text_processor import TextProcessor
from processing.content_extractor import ContentExtractor


# Configure logging
logger.remove()
logger.add(sys.stderr, level=LOG_LEVEL)
logger.add(LOGS_DIR / LOG_FILE, rotation="10 MB", level=LOG_LEVEL)


class ContentScraperOrchestrator:
    """Main orchestrator for scraping pipeline."""

    def __init__(self):
        """Initialize orchestrator."""
        self.authors_config = load_authors_config()
        self.validator = AuthenticityValidator()
        self.db = ContentDatabase()
        self.text_processor = TextProcessor()
        self.content_extractor = ContentExtractor()
        self.vector_store = None

    def scrape_author(
        self,
        author_id: str,
        platforms: Optional[list] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        max_items: int = 100
    ) -> list:
        """
        Scrape content for an author.

        Args:
            author_id: Author identifier
            platforms: List of platforms to scrape (None for all)
            date_from: Start date
            date_to: End date
            max_items: Max items per platform

        Returns:
            List of scraped content objects
        """
        logger.info(f"Starting scrape for author: {author_id}")

        try:
            author_config = get_author_config(author_id)
        except ValueError as e:
            logger.error(str(e))
            return []

        all_content = []

        # Determine which platforms to scrape
        if platforms is None:
            platforms = ['blog', 'twitter', 'youtube', 'podcast', 'book']

        # Scrape each platform
        with tqdm(total=len(platforms), desc=f"Scraping {author_id}") as pbar:
            for platform in platforms:
                pbar.set_description(f"Scraping {platform}")

                try:
                    content = self._scrape_platform(
                        author_id=author_id,
                        author_config=author_config,
                        platform=platform,
                        date_from=date_from,
                        date_to=date_to,
                        max_items=max_items
                    )

                    all_content.extend(content)
                    logger.info(f"Scraped {len(content)} items from {platform}")

                except Exception as e:
                    logger.error(f"Failed to scrape {platform}: {e}", exc_info=True)

                pbar.update(1)

        logger.info(f"Total items scraped for {author_id}: {len(all_content)}")
        return all_content

    def _scrape_platform(
        self,
        author_id: str,
        author_config: dict,
        platform: str,
        date_from: Optional[datetime],
        date_to: Optional[datetime],
        max_items: int
    ) -> list:
        """Scrape a specific platform."""
        content = []

        try:
            if platform == 'blog':
                scraper = BlogScraper(author_id, author_config)
                content = scraper.scrape(
                    max_pages=max_items // 10,
                    date_from=date_from,
                    date_to=date_to
                )

            elif platform == 'twitter':
                scraper = TwitterScraper(author_id, author_config)
                content = scraper.scrape(
                    max_tweets=max_items,
                    date_from=date_from,
                    date_to=date_to
                )

            elif platform == 'youtube':
                scraper = YouTubeScraper(author_id, author_config)
                content = scraper.scrape(
                    max_videos=max_items,
                    date_from=date_from,
                    date_to=date_to
                )

            elif platform == 'podcast':
                scraper = PodcastScraper(author_id, author_config)
                content = scraper.scrape(
                    max_episodes=max_items,
                    date_from=date_from,
                    date_to=date_to
                )

            elif platform == 'book':
                scraper = BookScraper(author_id, author_config)
                content = scraper.scrape(max_chapters=max_items)

        except Exception as e:
            logger.error(f"Error scraping {platform}: {e}", exc_info=True)

        return content

    def validate_content(self, contents: list) -> list:
        """Validate content authenticity."""
        logger.info(f"Validating {len(contents)} items")
        validated = self.validator.validate_batch(contents)
        return validated

    def process_content(self, contents: list) -> list:
        """Process and analyze content."""
        logger.info(f"Processing {len(contents)} items")

        processed = []
        for content in tqdm(contents, desc="Processing content"):
            try:
                processed_content = self.text_processor.process(content)
                processed.append(processed_content)
            except Exception as e:
                logger.error(f"Failed to process content {content.get('id')}: {e}")

        return processed

    def embed_content(self, contents: list) -> list:
        """Create embeddings for content."""
        logger.info(f"Creating embeddings for {len(contents)} items")

        embedded = []
        for content in tqdm(contents, desc="Creating embeddings"):
            try:
                embedded_content = self.content_extractor.embed_content(content)
                embedded.append(embedded_content)
            except Exception as e:
                logger.error(f"Failed to embed content {content.get('id')}: {e}")

        return embedded

    def store_content(self, contents: list, store_vectors: bool = False):
        """Store content in database and optionally vector store."""
        logger.info(f"Storing {len(contents)} items in database")

        # Store in database
        saved = self.db.save_batch(contents)
        logger.info(f"Saved {saved} items to database")

        # Store in vector store
        if store_vectors and self.vector_store:
            logger.info("Storing vectors in vector store")

            vectors = []
            for content in contents:
                if content.get('embeddings'):
                    vectors.append({
                        'id': content['id'],
                        'values': content['embeddings'],
                        'metadata': {
                            'author': content['author'],
                            'platform': content['platform'],
                            'title': content['title'],
                            'url': content['url']
                        }
                    })

            if vectors:
                try:
                    self.vector_store.upsert(vectors)
                    logger.info(f"Stored {len(vectors)} vectors")
                except Exception as e:
                    logger.error(f"Failed to store vectors: {e}")


# CLI Commands
@click.group()
@click.option('--verbose', is_flag=True, help='Enable verbose logging')
def cli(verbose):
    """Content Scraper for Balaji Srinivasan and Tim Ferriss."""
    if verbose:
        logger.remove()
        logger.add(sys.stderr, level="DEBUG")


@cli.command()
@click.option('--author', required=True, help='Author ID (balaji_srinivasan or tim_ferriss)')
@click.option('--platform', multiple=True, help='Platforms to scrape (blog, twitter, youtube, podcast, book)')
@click.option('--max-items', default=100, help='Maximum items per platform')
@click.option('--date-from', help='Start date (YYYY-MM-DD)')
@click.option('--date-to', help='End date (YYYY-MM-DD)')
@click.option('--authentic-only', is_flag=True, help='Only save authentic content')
@click.option('--process/--no-process', default=True, help='Process content')
@click.option('--embed/--no-embed', default=False, help='Create embeddings')
@click.option('--store/--no-store', default=True, help='Store in database')
def scrape(author, platform, max_items, date_from, date_to, authentic_only, process, embed, store):
    """Scrape content from specified platforms."""
    orchestrator = ContentScraperOrchestrator()

    # Parse dates
    date_from_dt = datetime.strptime(date_from, '%Y-%m-%d') if date_from else None
    date_to_dt = datetime.strptime(date_to, '%Y-%m-%d') if date_to else None

    # Convert platform tuple to list
    platforms = list(platform) if platform else None

    # Scrape
    contents = orchestrator.scrape_author(
        author_id=author,
        platforms=platforms,
        date_from=date_from_dt,
        date_to=date_to_dt,
        max_items=max_items
    )

    # Validate
    contents = orchestrator.validate_content(contents)

    # Filter by authenticity if requested
    if authentic_only:
        from config.settings import MIN_AUTHENTICITY_SCORE
        contents = [c for c in contents if c.get('authenticity_score', 0) >= MIN_AUTHENTICITY_SCORE]
        logger.info(f"Filtered to {len(contents)} authentic items")

    # Process
    if process:
        contents = orchestrator.process_content(contents)

    # Embed
    if embed:
        contents = orchestrator.embed_content(contents)

    # Store
    if store:
        orchestrator.store_content(contents, store_vectors=embed)

    click.echo(f"✓ Scraped and processed {len(contents)} items for {author}")


@cli.command()
@click.option('--limit', default=100, help='Number of items to process')
@click.option('--embed/--no-embed', default=True, help='Create embeddings')
def process(limit, embed):
    """Process unprocessed content from database."""
    orchestrator = ContentScraperOrchestrator()

    # Get unprocessed content
    contents = orchestrator.db.get_unprocessed_content(limit=limit)
    click.echo(f"Found {len(contents)} unprocessed items")

    if not contents:
        return

    # Process
    processed = orchestrator.process_content(contents)

    # Embed
    if embed:
        processed = orchestrator.embed_content(processed)

    # Update database
    orchestrator.store_content(processed, store_vectors=embed)

    click.echo(f"✓ Processed {len(processed)} items")


@cli.command()
def stats():
    """Show database statistics."""
    db = ContentDatabase()
    statistics = db.get_statistics()

    click.echo("\n=== Database Statistics ===\n")
    click.echo(f"Total content items: {statistics.get('total_content', 0)}")
    click.echo(f"Processed: {statistics.get('processed', 0)}")
    click.echo(f"Embedded: {statistics.get('embedded', 0)}")

    click.echo("\n--- By Author ---")
    for author, count in statistics.get('by_author', {}).items():
        click.echo(f"  {author}: {count}")

    click.echo("\n--- By Platform ---")
    for platform, count in statistics.get('by_platform', {}).items():
        click.echo(f"  {platform}: {count}")


@cli.command()
@click.option('--author', help='Filter by author')
@click.option('--output', required=True, help='Output file path')
def export(author, output):
    """Export content to JSON."""
    db = ContentDatabase()
    db.export_to_json(output, author=author)
    click.echo(f"✓ Exported content to {output}")


@cli.command()
@click.option('--all', 'scrape_all', is_flag=True, help='Scrape all authors')
@click.option('--authentic-only', is_flag=True, help='Only save authentic content')
def scrape_all_cmd(scrape_all, authentic_only):
    """Scrape all configured authors across all platforms."""
    if not scrape_all:
        click.echo("Use --all flag to confirm scraping all authors")
        return

    orchestrator = ContentScraperOrchestrator()

    for author_id in orchestrator.authors_config.keys():
        click.echo(f"\n=== Scraping {author_id} ===\n")

        # Scrape all platforms
        contents = orchestrator.scrape_author(author_id=author_id, max_items=100)

        # Validate
        contents = orchestrator.validate_content(contents)

        # Filter if needed
        if authentic_only:
            from config.settings import MIN_AUTHENTICITY_SCORE
            contents = [c for c in contents if c.get('authenticity_score', 0) >= MIN_AUTHENTICITY_SCORE]

        # Process
        contents = orchestrator.process_content(contents)

        # Store
        orchestrator.store_content(contents)

        click.echo(f"✓ Completed {author_id}: {len(contents)} items")


if __name__ == '__main__':
    cli()
