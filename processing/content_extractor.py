"""
Content extraction utilities for creating embeddings and structured data.
"""
import os
from typing import List, Dict, Any, Optional

from loguru import logger

from config.settings import OPENAI_API_KEY, EMBEDDING_CONFIG


class ContentExtractor:
    """Extract structured information and embeddings from content."""

    def __init__(self, embedding_model: str = None):
        """
        Initialize content extractor.

        Args:
            embedding_model: Name of embedding model to use
        """
        self.embedding_model = embedding_model or EMBEDDING_CONFIG['model']
        self.openai_client = None

        # Initialize OpenAI client if API key is available
        if OPENAI_API_KEY:
            self._init_openai()

    def _init_openai(self):
        """Initialize OpenAI client."""
        try:
            import openai
            openai.api_key = OPENAI_API_KEY
            self.openai_client = openai
            logger.info("Initialized OpenAI client for embeddings")
        except ImportError:
            logger.warning("OpenAI package not installed. Install with: pip install openai")

    def create_embedding(self, text: str) -> Optional[List[float]]:
        """
        Create embedding for text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector or None if failed
        """
        if not self.openai_client:
            logger.warning("OpenAI client not initialized. Cannot create embeddings.")
            return None

        try:
            # Truncate text if too long
            max_tokens = EMBEDDING_CONFIG['max_tokens']
            if len(text) > max_tokens * 4:  # Approximate, 1 token ≈ 4 chars
                text = text[:max_tokens * 4]

            # Create embedding
            response = self.openai_client.embeddings.create(
                input=text,
                model=self.embedding_model
            )

            embedding = response.data[0].embedding
            logger.debug(f"Created embedding with dimension {len(embedding)}")

            return embedding

        except Exception as e:
            logger.error(f"Failed to create embedding: {e}")
            return None

    def create_embeddings_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        Create embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        if not self.openai_client:
            logger.warning("OpenAI client not initialized. Cannot create embeddings.")
            return [None] * len(texts)

        embeddings = []
        batch_size = EMBEDDING_CONFIG['batch_size']

        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]

            try:
                # Truncate texts if too long
                max_tokens = EMBEDDING_CONFIG['max_tokens']
                truncated_batch = [
                    text[:max_tokens * 4] if len(text) > max_tokens * 4 else text
                    for text in batch
                ]

                # Create embeddings
                response = self.openai_client.embeddings.create(
                    input=truncated_batch,
                    model=self.embedding_model
                )

                batch_embeddings = [item.embedding for item in response.data]
                embeddings.extend(batch_embeddings)

                logger.debug(f"Created {len(batch_embeddings)} embeddings")

            except Exception as e:
                logger.error(f"Failed to create batch embeddings: {e}")
                embeddings.extend([None] * len(batch))

        return embeddings

    def embed_content(self, content_obj: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add embeddings to content object.

        Args:
            content_obj: Content dictionary

        Returns:
            Updated content dictionary with embeddings
        """
        text = content_obj.get('content', '')

        if not text:
            logger.warning(f"No content to embed for {content_obj.get('id')}")
            return content_obj

        # Create embedding
        embedding = self.create_embedding(text)

        if embedding:
            content_obj['embeddings'] = embedding
            content_obj['embedded'] = True
        else:
            content_obj['embeddings'] = []
            content_obj['embedded'] = False

        return content_obj

    def embed_chunks(self, chunk_objs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Add embeddings to chunk objects.

        Args:
            chunk_objs: List of chunk dictionaries

        Returns:
            List of chunks with embeddings
        """
        texts = [chunk['text'] for chunk in chunk_objs]
        embeddings = self.create_embeddings_batch(texts)

        for chunk, embedding in zip(chunk_objs, embeddings):
            if embedding:
                chunk['embedding'] = embedding
            else:
                chunk['embedding'] = []

        return chunk_objs

    def extract_insights(self, text: str) -> Dict[str, Any]:
        """
        Extract insights from text using AI (if available).

        Args:
            text: Text to analyze

        Returns:
            Dictionary of insights
        """
        if not self.openai_client:
            return {}

        try:
            # Use GPT to extract key insights
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "Extract key insights, main topics, and actionable takeaways from the text. Return as JSON with keys: main_topics, key_insights, actionable_items."
                    },
                    {
                        "role": "user",
                        "content": text[:4000]  # Limit length
                    }
                ],
                temperature=0.3
            )

            import json
            insights = json.loads(response.choices[0].message.content)
            return insights

        except Exception as e:
            logger.error(f"Failed to extract insights: {e}")
            return {}

    def create_summary(self, text: str, max_length: int = 200) -> str:
        """
        Create a summary of text.

        Args:
            text: Text to summarize
            max_length: Maximum summary length

        Returns:
            Summary text
        """
        if not self.openai_client:
            # Simple extractive summary - first few sentences
            sentences = text.split('.')
            summary = '. '.join(sentences[:3]) + '.'
            return summary[:max_length]

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": f"Create a concise summary of the following text in no more than {max_length} characters."
                    },
                    {
                        "role": "user",
                        "content": text[:4000]
                    }
                ],
                temperature=0.3,
                max_tokens=max_length // 4
            )

            summary = response.choices[0].message.content
            return summary

        except Exception as e:
            logger.error(f"Failed to create summary: {e}")
            # Fallback to simple summary
            sentences = text.split('.')
            summary = '. '.join(sentences[:3]) + '.'
            return summary[:max_length]

    def extract_structured_data(self, content_obj: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract structured data from content.

        Args:
            content_obj: Content dictionary

        Returns:
            Dictionary of structured data
        """
        text = content_obj.get('content', '')
        platform = content_obj.get('platform', '')

        structured = {
            'goals': [],
            'strategies': [],
            'principles': [],
            'resources': [],
            'quotes': []
        }

        # Extract based on patterns
        # Goals
        goal_patterns = [
            r'goal[s]?\s+(?:is|are|was|were)\s+to\s+([^.!?]+)',
            r'aim[s]?\s+(?:is|are|was|were)\s+to\s+([^.!?]+)',
            r'objective[s]?\s+(?:is|are|was|were)\s+to\s+([^.!?]+)'
        ]

        # Strategies
        strategy_patterns = [
            r'strategy\s+(?:is|are|was|were)\s+to\s+([^.!?]+)',
            r'approach\s+(?:is|are|was|were)\s+to\s+([^.!?]+)',
            r'method\s+(?:is|are|was|were)\s+to\s+([^.!?]+)'
        ]

        # Principles
        principle_patterns = [
            r'principle[s]?\s+(?:is|are|was|were)\s+([^.!?]+)',
            r'rule[s]?\s+(?:is|are|was|were)\s+([^.!?]+)',
            r'always\s+([^.!?]+)',
            r'never\s+([^.!?]+)'
        ]

        import re

        for pattern in goal_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                structured['goals'].append(match.group(1).strip())

        for pattern in strategy_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                structured['strategies'].append(match.group(1).strip())

        for pattern in principle_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                structured['principles'].append(match.group(1).strip())

        # Extract quotes (text in quotation marks)
        quote_pattern = r'"([^"]{20,200})"'
        quotes = re.findall(quote_pattern, text)
        structured['quotes'] = quotes[:5]  # Limit to 5 quotes

        return structured
