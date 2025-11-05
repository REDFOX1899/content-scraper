"""
Twitter/X scraper for extracting tweets and threads.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import tweepy
from loguru import logger

from scrapers.base_scraper import BaseScraper
from config.settings import (
    TWITTER_API_KEY,
    TWITTER_API_SECRET,
    TWITTER_ACCESS_TOKEN,
    TWITTER_ACCESS_TOKEN_SECRET,
    TWITTER_BEARER_TOKEN,
    TWITTER_SETTINGS
)


class TwitterScraper(BaseScraper):
    """Scraper for Twitter/X posts."""

    def __init__(self, author_id: str, author_config: Dict[str, Any]):
        """Initialize Twitter scraper."""
        super().__init__(author_id, author_config)

        self.twitter_handle = author_config.get('twitter', {}).get('handle')
        if not self.twitter_handle:
            raise ValueError(f"No Twitter handle found for {author_id}")

        # Remove @ if present
        self.twitter_handle = self.twitter_handle.lstrip('@')

        # Initialize Twitter API client
        self.client = self._init_twitter_client()
        self.user_id = None

    def _init_twitter_client(self) -> Optional[tweepy.Client]:
        """Initialize Twitter API v2 client."""
        if not TWITTER_BEARER_TOKEN:
            logger.warning("Twitter Bearer Token not found. Twitter scraping will be limited.")
            return None

        try:
            client = tweepy.Client(
                bearer_token=TWITTER_BEARER_TOKEN,
                consumer_key=TWITTER_API_KEY,
                consumer_secret=TWITTER_API_SECRET,
                access_token=TWITTER_ACCESS_TOKEN,
                access_token_secret=TWITTER_ACCESS_TOKEN_SECRET,
                wait_on_rate_limit=True
            )
            logger.info(f"Initialized Twitter API client for @{self.twitter_handle}")
            return client

        except Exception as e:
            logger.error(f"Failed to initialize Twitter client: {e}")
            return None

    def _get_user_id(self) -> Optional[str]:
        """Get Twitter user ID from handle."""
        if self.user_id:
            return self.user_id

        if not self.client:
            return None

        try:
            user = self.client.get_user(username=self.twitter_handle)
            if user and user.data:
                self.user_id = user.data.id
                logger.info(f"Found user ID for @{self.twitter_handle}: {self.user_id}")
                return self.user_id

        except Exception as e:
            logger.error(f"Failed to get user ID for @{self.twitter_handle}: {e}")

        return None

    def scrape(
        self,
        max_tweets: int = 100,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        include_replies: bool = False,
        include_retweets: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Scrape tweets from the user.

        Args:
            max_tweets: Maximum number of tweets to fetch
            date_from: Start date for filtering
            date_to: End date for filtering
            include_replies: Include reply tweets
            include_retweets: Include retweets

        Returns:
            List of content objects
        """
        if not self.client:
            logger.error("Twitter client not initialized. Cannot scrape tweets.")
            return []

        user_id = self._get_user_id()
        if not user_id:
            logger.error(f"Could not find user ID for @{self.twitter_handle}")
            return []

        all_content = []

        try:
            # Build query parameters
            exclude = []
            if not include_replies:
                exclude.append('replies')
            if not include_retweets:
                exclude.append('retweets')

            # Fetch tweets
            tweets = self._fetch_tweets(
                user_id=user_id,
                max_results=min(max_tweets, TWITTER_SETTINGS['max_results']),
                start_time=date_from,
                end_time=date_to,
                exclude=exclude
            )

            # Process tweets
            for tweet in tweets:
                content_obj = self._process_tweet(tweet)
                if content_obj and self.validate_content(content_obj):
                    all_content.append(content_obj)
                    self.stats['items_scraped'] += 1
                else:
                    self.stats['items_filtered'] += 1

            # Detect and reconstruct threads
            threads = self._reconstruct_threads(all_content)
            all_content.extend(threads)

            logger.info(f"Scraped {len(all_content)} tweets/threads for @{self.twitter_handle}")

        except Exception as e:
            logger.error(f"Failed to scrape Twitter for @{self.twitter_handle}: {e}", exc_info=True)

        return all_content

    def _fetch_tweets(
        self,
        user_id: str,
        max_results: int,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        exclude: Optional[List[str]] = None
    ) -> List[tweepy.Tweet]:
        """Fetch tweets using Twitter API v2."""
        tweets = []
        pagination_token = None

        while len(tweets) < max_results:
            try:
                response = self.client.get_users_tweets(
                    id=user_id,
                    max_results=min(100, max_results - len(tweets)),
                    tweet_fields=TWITTER_SETTINGS['tweet_fields'],
                    expansions=TWITTER_SETTINGS['expansions'],
                    start_time=start_time,
                    end_time=end_time,
                    exclude=exclude,
                    pagination_token=pagination_token
                )

                if not response.data:
                    break

                tweets.extend(response.data)

                # Check for more pages
                if hasattr(response, 'meta') and 'next_token' in response.meta:
                    pagination_token = response.meta['next_token']
                else:
                    break

            except Exception as e:
                logger.error(f"Error fetching tweets: {e}")
                break

        return tweets

    def _process_tweet(self, tweet: tweepy.Tweet) -> Optional[Dict[str, Any]]:
        """Process a single tweet into content object."""
        try:
            # Extract tweet data
            tweet_id = tweet.id
            text = tweet.text
            created_at = tweet.created_at
            conversation_id = getattr(tweet, 'conversation_id', None)

            # Get metrics
            metrics = {}
            if hasattr(tweet, 'public_metrics'):
                metrics = {
                    'retweet_count': tweet.public_metrics.get('retweet_count', 0),
                    'reply_count': tweet.public_metrics.get('reply_count', 0),
                    'like_count': tweet.public_metrics.get('like_count', 0),
                    'quote_count': tweet.public_metrics.get('quote_count', 0)
                }

            # Check if part of thread
            referenced_tweets = getattr(tweet, 'referenced_tweets', [])
            is_reply = any(ref.type == 'replied_to' for ref in referenced_tweets) if referenced_tweets else False

            # Build URL
            url = f"https://twitter.com/{self.twitter_handle}/status/{tweet_id}"

            # Metadata
            metadata = {
                'tweet_id': str(tweet_id),
                'conversation_id': str(conversation_id) if conversation_id else None,
                'is_reply': is_reply,
                'is_thread': False,  # Will be updated if part of thread
                'metrics': metrics,
                'referenced_tweets': [
                    {'id': str(ref.id), 'type': ref.type}
                    for ref in referenced_tweets
                ] if referenced_tweets else []
            }

            # Create content object
            return self.create_content_object(
                title=f"Tweet by @{self.twitter_handle}",
                content=text,
                url=url,
                date_published=created_at,
                platform='twitter',
                content_type='tweet',
                metadata=metadata
            )

        except Exception as e:
            logger.error(f"Failed to process tweet: {e}")
            return None

    def _reconstruct_threads(self, tweets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Reconstruct tweet threads from individual tweets."""
        threads = []

        # Group tweets by conversation_id
        conversations = {}
        for tweet in tweets:
            conv_id = tweet['metadata'].get('conversation_id')
            if conv_id:
                if conv_id not in conversations:
                    conversations[conv_id] = []
                conversations[conv_id].append(tweet)

        # Reconstruct threads (conversations with multiple tweets)
        for conv_id, conv_tweets in conversations.items():
            if len(conv_tweets) > 1:
                # Sort by date
                conv_tweets.sort(key=lambda x: x['date_published'])

                # Combine into thread
                thread_text = '\n\n'.join([t['content'] for t in conv_tweets])
                first_tweet = conv_tweets[0]

                # Mark individual tweets as part of thread
                for tweet in conv_tweets:
                    tweet['metadata']['is_thread'] = True

                # Create thread object
                thread_obj = self.create_content_object(
                    title=f"Thread by @{self.twitter_handle}",
                    content=thread_text,
                    url=first_tweet['url'],
                    date_published=datetime.fromisoformat(first_tweet['date_published']),
                    platform='twitter',
                    content_type='thread',
                    metadata={
                        'conversation_id': conv_id,
                        'tweet_count': len(conv_tweets),
                        'tweet_ids': [t['metadata']['tweet_id'] for t in conv_tweets],
                        'combined_metrics': self._combine_metrics(conv_tweets)
                    }
                )

                threads.append(thread_obj)

        logger.info(f"Reconstructed {len(threads)} threads")
        return threads

    def _combine_metrics(self, tweets: List[Dict[str, Any]]) -> Dict[str, int]:
        """Combine metrics from multiple tweets in a thread."""
        combined = {
            'retweet_count': 0,
            'reply_count': 0,
            'like_count': 0,
            'quote_count': 0
        }

        for tweet in tweets:
            metrics = tweet['metadata'].get('metrics', {})
            for key in combined:
                combined[key] += metrics.get(key, 0)

        return combined

    def get_tweet_by_id(self, tweet_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a specific tweet by ID."""
        if not self.client:
            return None

        try:
            tweet = self.client.get_tweet(
                id=tweet_id,
                tweet_fields=TWITTER_SETTINGS['tweet_fields']
            )

            if tweet and tweet.data:
                return self._process_tweet(tweet.data)

        except Exception as e:
            logger.error(f"Failed to fetch tweet {tweet_id}: {e}")

        return None
