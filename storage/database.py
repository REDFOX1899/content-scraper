"""
Database layer for storing scraped content using SQLAlchemy.
"""
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from contextlib import contextmanager

from sqlalchemy import (
    create_engine, Column, String, Text, Integer,
    DateTime, Float, Boolean, JSON, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from loguru import logger

from config.settings import DATABASE_URL

Base = declarative_base()


class Content(Base):
    """Content model for storing scraped data."""

    __tablename__ = 'content'

    # Primary key
    id = Column(String(64), primary_key=True)

    # Author information
    author = Column(String(100), nullable=False, index=True)
    author_name = Column(String(200))

    # Platform and content type
    platform = Column(String(50), nullable=False, index=True)
    content_type = Column(String(50), index=True)

    # Content fields
    title = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    url = Column(Text, nullable=False)

    # Dates
    date_published = Column(DateTime, index=True)
    date_scraped = Column(DateTime, nullable=False, default=datetime.now)

    # Validation
    authenticity_score = Column(Integer, index=True)

    # Processing status
    processed = Column(Boolean, default=False, index=True)
    embedded = Column(Boolean, default=False, index=True)

    # Metadata (JSON field)
    metadata = Column(JSON)

    # Word count (denormalized for quick access)
    word_count = Column(Integer)

    # Timestamps
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    # Indexes
    __table_args__ = (
        Index('idx_author_platform', 'author', 'platform'),
        Index('idx_author_date', 'author', 'date_published'),
        Index('idx_platform_date', 'platform', 'date_published'),
        Index('idx_processed_embedded', 'processed', 'embedded'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            'id': self.id,
            'author': self.author,
            'author_name': self.author_name,
            'platform': self.platform,
            'content_type': self.content_type,
            'title': self.title,
            'content': self.content,
            'url': self.url,
            'date_published': self.date_published.isoformat() if self.date_published else None,
            'date_scraped': self.date_scraped.isoformat() if self.date_scraped else None,
            'authenticity_score': self.authenticity_score,
            'processed': self.processed,
            'embedded': self.embedded,
            'metadata': self.metadata,
            'word_count': self.word_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class ContentDatabase:
    """Database manager for content storage."""

    def __init__(self, database_url: str = None):
        """
        Initialize database connection.

        Args:
            database_url: Database connection URL
        """
        self.database_url = database_url or DATABASE_URL
        self.engine = create_engine(self.database_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)

        # Create tables
        self.create_tables()

        logger.info(f"Initialized database: {self.database_url}")

    def create_tables(self):
        """Create all tables if they don't exist."""
        Base.metadata.create_all(self.engine)
        logger.info("Database tables created/verified")

    @contextmanager
    def get_session(self) -> Session:
        """
        Get a database session with automatic cleanup.

        Yields:
            Database session
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            session.close()

    def save_content(self, content_obj: Dict[str, Any]) -> bool:
        """
        Save or update content in database.

        Args:
            content_obj: Content dictionary

        Returns:
            True if successful
        """
        try:
            with self.get_session() as session:
                # Check if content already exists
                existing = session.query(Content).filter_by(id=content_obj['id']).first()

                if existing:
                    # Update existing
                    for key, value in content_obj.items():
                        if key == 'date_published' and isinstance(value, str):
                            value = datetime.fromisoformat(value)
                        elif key == 'date_scraped' and isinstance(value, str):
                            value = datetime.fromisoformat(value)
                        setattr(existing, key, value)

                    logger.debug(f"Updated existing content: {content_obj['id']}")
                else:
                    # Create new
                    # Convert date strings to datetime
                    if 'date_published' in content_obj and isinstance(content_obj['date_published'], str):
                        content_obj['date_published'] = datetime.fromisoformat(content_obj['date_published'])

                    if 'date_scraped' in content_obj and isinstance(content_obj['date_scraped'], str):
                        content_obj['date_scraped'] = datetime.fromisoformat(content_obj['date_scraped'])

                    # Extract word count from metadata if not present
                    if 'word_count' not in content_obj and 'metadata' in content_obj:
                        content_obj['word_count'] = content_obj['metadata'].get('word_count', 0)

                    content = Content(**content_obj)
                    session.add(content)
                    logger.debug(f"Saved new content: {content_obj['id']}")

                return True

        except Exception as e:
            logger.error(f"Failed to save content: {e}", exc_info=True)
            return False

    def save_batch(self, contents: List[Dict[str, Any]]) -> int:
        """
        Save multiple content objects.

        Args:
            contents: List of content dictionaries

        Returns:
            Number of successfully saved items
        """
        saved = 0

        for content in contents:
            if self.save_content(content):
                saved += 1

        logger.info(f"Saved {saved}/{len(contents)} content items")
        return saved

    def get_content_by_id(self, content_id: str) -> Optional[Dict[str, Any]]:
        """Get content by ID."""
        try:
            with self.get_session() as session:
                content = session.query(Content).filter_by(id=content_id).first()
                return content.to_dict() if content else None
        except Exception as e:
            logger.error(f"Failed to get content {content_id}: {e}")
            return None

    def get_content_by_author(
        self,
        author: str,
        limit: int = 100,
        offset: int = 0,
        platform: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get content by author."""
        try:
            with self.get_session() as session:
                query = session.query(Content).filter_by(author=author)

                if platform:
                    query = query.filter_by(platform=platform)

                query = query.order_by(Content.date_published.desc())
                query = query.limit(limit).offset(offset)

                return [c.to_dict() for c in query.all()]

        except Exception as e:
            logger.error(f"Failed to get content for {author}: {e}")
            return []

    def get_unprocessed_content(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get content that hasn't been processed yet."""
        try:
            with self.get_session() as session:
                contents = session.query(Content).filter_by(processed=False).limit(limit).all()
                return [c.to_dict() for c in contents]
        except Exception as e:
            logger.error(f"Failed to get unprocessed content: {e}")
            return []

    def get_unembedded_content(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get content that hasn't been embedded yet."""
        try:
            with self.get_session() as session:
                contents = session.query(Content).filter_by(
                    processed=True,
                    embedded=False
                ).limit(limit).all()
                return [c.to_dict() for c in contents]
        except Exception as e:
            logger.error(f"Failed to get unembedded content: {e}")
            return []

    def mark_processed(self, content_id: str) -> bool:
        """Mark content as processed."""
        try:
            with self.get_session() as session:
                content = session.query(Content).filter_by(id=content_id).first()
                if content:
                    content.processed = True
                    return True
                return False
        except Exception as e:
            logger.error(f"Failed to mark content as processed: {e}")
            return False

    def mark_embedded(self, content_id: str) -> bool:
        """Mark content as embedded."""
        try:
            with self.get_session() as session:
                content = session.query(Content).filter_by(id=content_id).first()
                if content:
                    content.embedded = True
                    return True
                return False
        except Exception as e:
            logger.error(f"Failed to mark content as embedded: {e}")
            return False

    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics."""
        try:
            with self.get_session() as session:
                total = session.query(Content).count()
                processed = session.query(Content).filter_by(processed=True).count()
                embedded = session.query(Content).filter_by(embedded=True).count()

                by_author = {}
                authors = session.query(Content.author).distinct().all()
                for (author,) in authors:
                    count = session.query(Content).filter_by(author=author).count()
                    by_author[author] = count

                by_platform = {}
                platforms = session.query(Content.platform).distinct().all()
                for (platform,) in platforms:
                    count = session.query(Content).filter_by(platform=platform).count()
                    by_platform[platform] = count

                return {
                    'total_content': total,
                    'processed': processed,
                    'embedded': embedded,
                    'by_author': by_author,
                    'by_platform': by_platform
                }

        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {}

    def delete_content(self, content_id: str) -> bool:
        """Delete content by ID."""
        try:
            with self.get_session() as session:
                content = session.query(Content).filter_by(id=content_id).first()
                if content:
                    session.delete(content)
                    logger.info(f"Deleted content: {content_id}")
                    return True
                return False
        except Exception as e:
            logger.error(f"Failed to delete content: {e}")
            return False

    def export_to_json(self, filepath: str, author: Optional[str] = None):
        """Export content to JSON file."""
        try:
            with self.get_session() as session:
                query = session.query(Content)

                if author:
                    query = query.filter_by(author=author)

                contents = [c.to_dict() for c in query.all()]

                with open(filepath, 'w') as f:
                    json.dump(contents, f, indent=2, default=str)

                logger.info(f"Exported {len(contents)} items to {filepath}")

        except Exception as e:
            logger.error(f"Failed to export to JSON: {e}")
