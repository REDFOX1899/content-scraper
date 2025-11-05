#!/usr/bin/env python3
"""
Example usage of the content scraper system.
Demonstrates how to use the scraper programmatically.
"""
from datetime import datetime, timedelta
from loguru import logger

from config.settings import get_author_config
from scrapers.blog_scraper import BlogScraper
from scrapers.twitter_scraper import TwitterScraper
from validators.authenticity_validator import AuthenticityValidator
from storage.database import ContentDatabase
from processing.text_processor import TextProcessor


def example_blog_scrape():
    """Example: Scrape Tim Ferriss blog posts."""
    print("\n=== Example 1: Blog Scraping ===\n")

    # Get author configuration
    author_config = get_author_config('tim_ferriss')

    # Initialize scraper
    scraper = BlogScraper('tim_ferriss', author_config)

    # Scrape recent posts
    date_from = datetime.now() - timedelta(days=365)  # Last year
    content = scraper.scrape(max_pages=5, date_from=date_from)

    print(f"Scraped {len(content)} blog posts")

    # Show first item
    if content:
        first_post = content[0]
        print(f"\nFirst post: {first_post['title']}")
        print(f"URL: {first_post['url']}")
        print(f"Published: {first_post['date_published']}")
        print(f"Word count: {first_post['metadata']['word_count']}")


def example_validation():
    """Example: Validate content authenticity."""
    print("\n=== Example 2: Content Validation ===\n")

    # Create a sample content object
    sample_content = {
        'id': 'test123',
        'author': 'tim_ferriss',
        'platform': 'blog',
        'title': 'Test Post',
        'content': 'This is a test post about productivity and life optimization.',
        'url': 'https://tim.blog/test-post/',
        'metadata': {}
    }

    # Validate
    validator = AuthenticityValidator()
    validated = validator.validate(sample_content)

    print(f"Authenticity score: {validated['authenticity_score']}")
    print(f"Passed validation: {validated['metadata']['validation']['passed']}")


def example_database():
    """Example: Store and retrieve from database."""
    print("\n=== Example 3: Database Operations ===\n")

    # Initialize database
    db = ContentDatabase()

    # Get statistics
    stats = db.get_statistics()
    print(f"Total items in database: {stats.get('total_content', 0)}")

    # Get content for specific author
    tim_content = db.get_content_by_author('tim_ferriss', limit=5)
    print(f"\nFound {len(tim_content)} items for Tim Ferriss")

    if tim_content:
        print(f"\nLatest item: {tim_content[0]['title']}")


def example_text_processing():
    """Example: Process text content."""
    print("\n=== Example 4: Text Processing ===\n")

    # Sample text
    text = """
    The 4-Hour Workweek is about lifestyle design and automation.
    Tim Ferriss discusses productivity, outsourcing, and mini-retirements.
    The book covers topics like elimination, automation, and liberation.
    """

    # Initialize processor
    processor = TextProcessor()

    # Extract keywords
    keywords = processor.extract_keywords(text)
    print(f"Keywords: {', '.join(keywords)}")

    # Chunk text
    chunks = processor.chunk_text(text, chunk_size=100, overlap=20)
    print(f"\nText split into {len(chunks)} chunks")

    # Calculate readability
    readability = processor.calculate_readability(text)
    print(f"Readability score: {readability:.1f}/100")


def example_full_pipeline():
    """Example: Full scraping pipeline."""
    print("\n=== Example 5: Full Pipeline ===\n")

    # 1. Scrape content
    author_config = get_author_config('balaji_srinivasan')
    scraper = BlogScraper('balaji_srinivasan', author_config)

    print("Step 1: Scraping...")
    content = scraper.scrape(max_pages=2)
    print(f"✓ Scraped {len(content)} items")

    if not content:
        print("No content scraped. Exiting.")
        return

    # 2. Validate
    print("\nStep 2: Validating...")
    validator = AuthenticityValidator()
    validated = validator.validate_batch(content)
    authentic = [c for c in validated if c['authenticity_score'] >= 75]
    print(f"✓ {len(authentic)} items passed validation")

    # 3. Process
    print("\nStep 3: Processing...")
    processor = TextProcessor()
    processed = [processor.process(c) for c in authentic]
    print(f"✓ Processed {len(processed)} items")

    # 4. Store
    print("\nStep 4: Storing...")
    db = ContentDatabase()
    saved = db.save_batch(processed)
    print(f"✓ Saved {saved} items to database")

    # 5. Retrieve and display
    print("\nStep 5: Retrieving...")
    stored_content = db.get_content_by_author('balaji_srinivasan', limit=1)

    if stored_content:
        item = stored_content[0]
        print(f"\nSample stored item:")
        print(f"  Title: {item['title']}")
        print(f"  Platform: {item['platform']}")
        print(f"  Authenticity: {item['authenticity_score']}")
        print(f"  Processed: {item['processed']}")
        print(f"  Keywords: {', '.join(item['metadata'].get('keywords', [])[:5])}")


def main():
    """Run all examples."""
    print("=" * 60)
    print("Content Scraper - Example Usage")
    print("=" * 60)

    try:
        # Run examples
        example_blog_scrape()
        example_validation()
        example_database()
        example_text_processing()
        example_full_pipeline()

    except Exception as e:
        logger.error(f"Error in examples: {e}", exc_info=True)

    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)


if __name__ == '__main__':
    main()
