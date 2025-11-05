"""
Podcast scraper for extracting podcast episodes from RSS feeds.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime

import feedparser
from loguru import logger
from dateutil import parser as date_parser

from scrapers.base_scraper import BaseScraper
from config.settings import PODCAST_SETTINGS


class PodcastScraper(BaseScraper):
    """Scraper for podcast episodes from RSS feeds."""

    def __init__(self, author_id: str, author_config: Dict[str, Any]):
        """Initialize podcast scraper."""
        super().__init__(author_id, author_config)

        self.podcasts = author_config.get('podcasts', [])
        if not self.podcasts:
            logger.warning(f"No podcast feeds found for {author_id}")

    def scrape(
        self,
        max_episodes: int = 100,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        download_audio: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Scrape podcast episodes.

        Args:
            max_episodes: Maximum number of episodes to fetch per podcast
            date_from: Start date for filtering
            date_to: End date for filtering
            download_audio: Whether to download audio files

        Returns:
            List of content objects
        """
        all_content = []

        for podcast in self.podcasts:
            podcast_name = podcast.get('name', 'Unknown')
            rss_url = podcast.get('rss_url')

            if not rss_url:
                # Try to search for podcast appearances
                search_keywords = podcast.get('search_keywords', [])
                if search_keywords:
                    logger.info(f"Searching for podcast appearances with keywords: {search_keywords}")
                    # This would require additional implementation for podcast search
                    continue
                else:
                    logger.warning(f"No RSS URL or search keywords for podcast: {podcast_name}")
                    continue

            logger.info(f"Scraping podcast: {podcast_name} ({rss_url})")

            try:
                episodes = self._scrape_podcast(
                    rss_url=rss_url,
                    podcast_name=podcast_name,
                    max_episodes=max_episodes,
                    date_from=date_from,
                    date_to=date_to,
                    download_audio=download_audio or PODCAST_SETTINGS['download_audio']
                )
                all_content.extend(episodes)

            except Exception as e:
                logger.error(f"Failed to scrape podcast {podcast_name}: {e}", exc_info=True)

        logger.info(f"Scraped {len(all_content)} podcast episodes for {self.author_name}")
        self.stats['items_scraped'] = len(all_content)

        return all_content

    def _scrape_podcast(
        self,
        rss_url: str,
        podcast_name: str,
        max_episodes: int,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        download_audio: bool = False
    ) -> List[Dict[str, Any]]:
        """Scrape episodes from a specific podcast feed."""
        episodes = []

        try:
            # Parse RSS feed
            feed = feedparser.parse(rss_url)

            if feed.bozo:
                logger.warning(f"RSS feed may be malformed: {rss_url}")

            # Get feed metadata
            feed_title = feed.feed.get('title', podcast_name)
            feed_description = feed.feed.get('description', '')

            logger.info(f"Found {len(feed.entries)} episodes in {feed_title}")

            # Process episodes
            for entry in feed.entries[:max_episodes]:
                try:
                    episode = self._process_episode(
                        entry=entry,
                        podcast_name=feed_title,
                        feed_description=feed_description,
                        download_audio=download_audio
                    )

                    if episode:
                        # Filter by date
                        if date_from or date_to:
                            episode_date = episode.get('date_published')
                            if episode_date:
                                episode_dt = datetime.fromisoformat(episode_date)
                                if date_from and episode_dt < date_from:
                                    continue
                                if date_to and episode_dt > date_to:
                                    continue

                        if self.validate_content(episode):
                            episodes.append(episode)
                            self.stats['items_scraped'] += 1
                        else:
                            self.stats['items_filtered'] += 1

                except Exception as e:
                    logger.warning(f"Failed to process episode: {e}")
                    continue

        except Exception as e:
            logger.error(f"Failed to parse RSS feed {rss_url}: {e}", exc_info=True)

        return episodes

    def _process_episode(
        self,
        entry,
        podcast_name: str,
        feed_description: str,
        download_audio: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Process a single podcast episode."""
        try:
            # Extract basic info
            title = entry.get('title', 'Untitled Episode')
            summary = entry.get('summary', entry.get('description', ''))

            # Clean HTML from summary if present
            from bs4 import BeautifulSoup
            summary = BeautifulSoup(summary, 'html.parser').get_text(separator='\n', strip=True)

            # Get episode URL
            url = entry.get('link', '')

            # Get audio URL
            audio_url = None
            for link in entry.get('links', []):
                if link.get('type', '').startswith('audio/'):
                    audio_url = link.get('href')
                    break

            # If no audio link found, try enclosures
            if not audio_url and hasattr(entry, 'enclosures') and entry.enclosures:
                for enclosure in entry.enclosures:
                    if enclosure.get('type', '').startswith('audio/'):
                        audio_url = enclosure.get('href')
                        break

            # Get publication date
            published_date = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                published_date = datetime(*entry.published_parsed[:6])
            elif hasattr(entry, 'published'):
                try:
                    published_date = date_parser.parse(entry.published)
                except:
                    pass

            # Get duration
            duration = None
            if hasattr(entry, 'itunes_duration'):
                duration = self._parse_duration(entry.itunes_duration)

            # Build content
            content_parts = [summary]

            # Note about transcript
            transcript_note = "\n\n[Note: Full transcript not available from RSS feed. "
            transcript_note += "Audio transcription would be required for complete content.]"
            content_parts.append(transcript_note)

            content = '\n\n'.join(content_parts)

            # Metadata
            metadata = {
                'podcast_name': podcast_name,
                'episode_url': url,
                'audio_url': audio_url,
                'duration': duration,
                'author': entry.get('author', ''),
                'episode_number': entry.get('itunes_episode'),
                'season': entry.get('itunes_season'),
                'has_transcript': False,
                'audio_downloaded': False
            }

            # Optionally download audio
            if download_audio and audio_url:
                audio_file = self._download_audio(audio_url, title)
                if audio_file:
                    metadata['audio_file'] = audio_file
                    metadata['audio_downloaded'] = True

            # Create content object
            return self.create_content_object(
                title=f"{podcast_name}: {title}",
                content=content,
                url=url or audio_url or '',
                date_published=published_date,
                platform='podcast',
                content_type='episode',
                metadata=metadata
            )

        except Exception as e:
            logger.error(f"Failed to process episode: {e}", exc_info=True)
            return None

    def _parse_duration(self, duration_str: str) -> Optional[int]:
        """Parse duration string to seconds."""
        try:
            # Handle formats like "1:23:45" or "45:30" or "125"
            parts = str(duration_str).split(':')
            if len(parts) == 3:
                hours, minutes, seconds = parts
                return int(hours) * 3600 + int(minutes) * 60 + int(seconds)
            elif len(parts) == 2:
                minutes, seconds = parts
                return int(minutes) * 60 + int(seconds)
            else:
                return int(duration_str)
        except:
            return None

    def _download_audio(self, audio_url: str, title: str) -> Optional[str]:
        """Download podcast audio file."""
        try:
            import os
            from config.settings import RAW_DATA_DIR

            # Create audio directory
            audio_dir = RAW_DATA_DIR / 'audio' / 'podcasts'
            audio_dir.mkdir(parents=True, exist_ok=True)

            # Generate filename
            safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_title = safe_title[:100]  # Limit length
            extension = audio_url.split('.')[-1].split('?')[0]
            if extension not in ['mp3', 'wav', 'm4a', 'ogg']:
                extension = 'mp3'

            filename = f"{safe_title}.{extension}"
            filepath = audio_dir / filename

            # Download file
            logger.info(f"Downloading audio: {title}")
            response = self.fetch_url(audio_url, stream=True)

            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            logger.info(f"Downloaded audio to {filepath}")
            return str(filepath)

        except Exception as e:
            logger.error(f"Failed to download audio {audio_url}: {e}")
            return None

    def get_episode_by_url(self, rss_url: str, episode_title: str) -> Optional[Dict[str, Any]]:
        """Get a specific episode by RSS URL and title."""
        try:
            feed = feedparser.parse(rss_url)

            for entry in feed.entries:
                if entry.get('title') == episode_title:
                    return self._process_episode(
                        entry=entry,
                        podcast_name=feed.feed.get('title', 'Unknown'),
                        feed_description=feed.feed.get('description', ''),
                        download_audio=False
                    )

        except Exception as e:
            logger.error(f"Failed to get episode: {e}")

        return None
