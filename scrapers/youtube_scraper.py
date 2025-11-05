"""
YouTube scraper for extracting video transcripts and metadata.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime

from loguru import logger
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from scrapers.base_scraper import BaseScraper
from config.settings import YOUTUBE_API_KEY, YOUTUBE_SETTINGS


class YouTubeScraper(BaseScraper):
    """Scraper for YouTube videos and transcripts."""

    def __init__(self, author_id: str, author_config: Dict[str, Any]):
        """Initialize YouTube scraper."""
        super().__init__(author_id, author_config)

        self.channels = author_config.get('youtube_channels', [])
        if not self.channels:
            raise ValueError(f"No YouTube channels found for {author_id}")

        # Initialize YouTube API client
        self.youtube = self._init_youtube_client()

    def _init_youtube_client(self):
        """Initialize YouTube Data API v3 client."""
        if not YOUTUBE_API_KEY:
            logger.warning("YouTube API key not found. Some features will be limited.")
            return None

        try:
            youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
            logger.info("Initialized YouTube API client")
            return youtube

        except Exception as e:
            logger.error(f"Failed to initialize YouTube client: {e}")
            return None

    def scrape(
        self,
        max_videos: int = 50,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        include_shorts: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Scrape YouTube videos.

        Args:
            max_videos: Maximum number of videos to fetch per channel
            date_from: Start date for filtering
            date_to: End date for filtering
            include_shorts: Include YouTube Shorts

        Returns:
            List of content objects
        """
        all_content = []

        for channel in self.channels:
            channel_id = channel.get('channel_id')
            channel_name = channel.get('name', 'Unknown')

            logger.info(f"Scraping YouTube channel: {channel_name} ({channel_id})")

            try:
                videos = self._scrape_channel(
                    channel_id=channel_id,
                    channel_name=channel_name,
                    max_videos=max_videos,
                    date_from=date_from,
                    date_to=date_to,
                    include_shorts=include_shorts
                )
                all_content.extend(videos)

            except Exception as e:
                logger.error(f"Failed to scrape channel {channel_name}: {e}", exc_info=True)

        logger.info(f"Scraped {len(all_content)} YouTube videos for {self.author_name}")
        self.stats['items_scraped'] = len(all_content)

        return all_content

    def _scrape_channel(
        self,
        channel_id: str,
        channel_name: str,
        max_videos: int,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        include_shorts: bool = False
    ) -> List[Dict[str, Any]]:
        """Scrape videos from a specific channel."""
        videos = []

        if not self.youtube:
            logger.error("YouTube API client not initialized")
            return videos

        try:
            # Get videos from channel
            video_ids = self._get_channel_video_ids(
                channel_id=channel_id,
                max_results=max_videos,
                published_after=date_from,
                published_before=date_to
            )

            logger.info(f"Found {len(video_ids)} videos from {channel_name}")

            # Process each video
            for video_id in video_ids:
                try:
                    video_content = self._scrape_video(video_id, channel_name)

                    if video_content:
                        # Filter shorts if needed
                        if not include_shorts and video_content['metadata'].get('is_short'):
                            self.stats['items_filtered'] += 1
                            continue

                        if self.validate_content(video_content):
                            videos.append(video_content)
                            self.stats['items_scraped'] += 1
                        else:
                            self.stats['items_filtered'] += 1

                except Exception as e:
                    logger.warning(f"Failed to scrape video {video_id}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Failed to get videos from channel {channel_id}: {e}")

        return videos

    def _get_channel_video_ids(
        self,
        channel_id: str,
        max_results: int,
        published_after: Optional[datetime] = None,
        published_before: Optional[datetime] = None
    ) -> List[str]:
        """Get video IDs from a channel."""
        video_ids = []

        try:
            # Build request parameters
            request_params = {
                'part': 'snippet',
                'channelId': channel_id,
                'maxResults': min(50, max_results),
                'order': YOUTUBE_SETTINGS['order'],
                'type': YOUTUBE_SETTINGS['type']
            }

            if published_after:
                request_params['publishedAfter'] = published_after.isoformat() + 'Z'
            if published_before:
                request_params['publishedBefore'] = published_before.isoformat() + 'Z'

            # Paginate through results
            next_page_token = None
            while len(video_ids) < max_results:
                if next_page_token:
                    request_params['pageToken'] = next_page_token

                response = self.youtube.search().list(**request_params).execute()

                for item in response.get('items', []):
                    if item['id']['kind'] == 'youtube#video':
                        video_ids.append(item['id']['videoId'])

                # Check for next page
                next_page_token = response.get('nextPageToken')
                if not next_page_token or len(video_ids) >= max_results:
                    break

        except HttpError as e:
            logger.error(f"YouTube API error: {e}")

        return video_ids[:max_results]

    def _scrape_video(self, video_id: str, channel_name: str) -> Optional[Dict[str, Any]]:
        """Scrape a single video."""
        try:
            # Get video metadata
            video_metadata = self._get_video_metadata(video_id)
            if not video_metadata:
                return None

            # Get transcript
            transcript = self._get_transcript(video_id)

            # Build content
            title = video_metadata['title']
            description = video_metadata['description']

            # Combine transcript and description for content
            content_parts = []
            if description:
                content_parts.append(f"Description: {description}")
            if transcript:
                content_parts.append(f"\n\nTranscript:\n{transcript}")

            content = '\n\n'.join(content_parts)

            if not content.strip():
                logger.warning(f"No content found for video {video_id}")
                return None

            # Build URL
            url = f"https://www.youtube.com/watch?v={video_id}"

            # Metadata
            metadata = {
                'video_id': video_id,
                'channel_name': channel_name,
                'duration_seconds': video_metadata.get('duration_seconds'),
                'view_count': video_metadata.get('view_count'),
                'like_count': video_metadata.get('like_count'),
                'comment_count': video_metadata.get('comment_count'),
                'tags': video_metadata.get('tags', []),
                'category': video_metadata.get('category'),
                'has_transcript': bool(transcript),
                'is_short': self._is_short_video(video_metadata)
            }

            # Create content object
            return self.create_content_object(
                title=title,
                content=content,
                url=url,
                date_published=video_metadata.get('published_at'),
                platform='youtube',
                content_type='video',
                metadata=metadata
            )

        except Exception as e:
            logger.error(f"Failed to scrape video {video_id}: {e}", exc_info=True)
            return None

    def _get_video_metadata(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Get video metadata from YouTube API."""
        try:
            response = self.youtube.videos().list(
                part='snippet,contentDetails,statistics',
                id=video_id
            ).execute()

            if not response.get('items'):
                return None

            item = response['items'][0]
            snippet = item['snippet']
            content_details = item['contentDetails']
            statistics = item['statistics']

            # Parse duration
            duration = content_details.get('duration', 'PT0S')
            duration_seconds = self._parse_duration(duration)

            return {
                'title': snippet['title'],
                'description': snippet.get('description', ''),
                'published_at': datetime.fromisoformat(snippet['publishedAt'].replace('Z', '+00:00')),
                'duration_seconds': duration_seconds,
                'view_count': int(statistics.get('viewCount', 0)),
                'like_count': int(statistics.get('likeCount', 0)),
                'comment_count': int(statistics.get('commentCount', 0)),
                'tags': snippet.get('tags', []),
                'category': snippet.get('categoryId')
            }

        except HttpError as e:
            logger.error(f"Failed to get metadata for video {video_id}: {e}")
            return None

    def _get_transcript(self, video_id: str) -> Optional[str]:
        """Get video transcript."""
        try:
            # Try to get transcript (prefer English)
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

            # Try to get English transcript first
            try:
                transcript = transcript_list.find_transcript(['en'])
            except NoTranscriptFound:
                # Fall back to any available transcript
                transcript = transcript_list.find_generated_transcript(['en'])

            # Fetch and format transcript
            transcript_data = transcript.fetch()
            formatted_transcript = ' '.join([item['text'] for item in transcript_data])

            return formatted_transcript

        except TranscriptsDisabled:
            logger.debug(f"Transcripts disabled for video {video_id}")
            return None

        except NoTranscriptFound:
            logger.debug(f"No transcript found for video {video_id}")
            return None

        except Exception as e:
            logger.warning(f"Failed to get transcript for video {video_id}: {e}")
            return None

    def _parse_duration(self, duration: str) -> int:
        """Parse ISO 8601 duration to seconds."""
        import re

        # Parse format like PT1H2M10S
        match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
        if not match:
            return 0

        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)

        return hours * 3600 + minutes * 60 + seconds

    def _is_short_video(self, metadata: Dict[str, Any]) -> bool:
        """Determine if video is a YouTube Short (< 60 seconds)."""
        duration = metadata.get('duration_seconds', 0)
        return duration > 0 and duration <= 60

    def get_video_by_id(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific video by ID."""
        try:
            return self._scrape_video(video_id, 'Direct')
        except Exception as e:
            logger.error(f"Failed to get video {video_id}: {e}")
            return None
