"""
Text processing pipeline for content extraction, chunking, and analysis.
"""
import re
from typing import List, Dict, Any, Optional
from loguru import logger

from config.settings import CHUNK_SIZE, CHUNK_OVERLAP


class TextProcessor:
    """Process and analyze text content."""

    def __init__(self):
        """Initialize text processor."""
        self.chunk_size = CHUNK_SIZE
        self.chunk_overlap = CHUNK_OVERLAP

    def process(self, content_obj: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process content object.

        Args:
            content_obj: Content dictionary

        Returns:
            Updated content dictionary with processing metadata
        """
        text = content_obj.get('content', '')

        if not text:
            logger.warning(f"No content to process for {content_obj.get('id')}")
            return content_obj

        # Clean text
        cleaned_text = self.clean_text(text)
        content_obj['content'] = cleaned_text

        # Extract key information
        metadata = content_obj.get('metadata', {})

        # Update word count
        word_count = self.count_words(cleaned_text)
        metadata['word_count'] = word_count
        content_obj['word_count'] = word_count

        # Extract topics/keywords
        keywords = self.extract_keywords(cleaned_text)
        metadata['keywords'] = keywords

        # Detect language (simple heuristic)
        metadata['language'] = 'en'  # Default to English

        # Update metadata
        content_obj['metadata'] = metadata
        content_obj['processed'] = True

        return content_obj

    def clean_text(self, text: str) -> str:
        """
        Clean and normalize text.

        Args:
            text: Raw text

        Returns:
            Cleaned text
        """
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)

        # Remove multiple newlines
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)

        # Remove URLs (optional - might want to keep for context)
        # text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)

        # Remove special characters but keep punctuation
        # text = re.sub(r'[^\w\s\.\,\!\?\-\;\:\'\"]', '', text)

        # Normalize quotes
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(''', "'").replace(''', "'")

        # Remove zero-width characters
        text = re.sub(r'[\u200b\u200c\u200d\ufeff]', '', text)

        return text.strip()

    def count_words(self, text: str) -> int:
        """Count words in text."""
        return len(text.split())

    def extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """
        Extract keywords from text using simple frequency analysis.

        Args:
            text: Text to analyze
            max_keywords: Maximum number of keywords to return

        Returns:
            List of keywords
        """
        # Convert to lowercase
        text_lower = text.lower()

        # Remove punctuation
        text_clean = re.sub(r'[^\w\s]', ' ', text_lower)

        # Split into words
        words = text_clean.split()

        # Common stop words to filter out
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
            'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these',
            'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'what', 'which',
            'who', 'when', 'where', 'why', 'how', 'not', 'no', 'yes'
        }

        # Filter and count
        word_freq = {}
        for word in words:
            if word and len(word) > 3 and word not in stop_words:
                word_freq[word] = word_freq.get(word, 0) + 1

        # Sort by frequency
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)

        # Return top keywords
        return [word for word, freq in sorted_words[:max_keywords]]

    def chunk_text(self, text: str, chunk_size: int = None, overlap: int = None) -> List[str]:
        """
        Split text into chunks with overlap.

        Args:
            text: Text to chunk
            chunk_size: Size of each chunk in characters
            overlap: Overlap between chunks in characters

        Returns:
            List of text chunks
        """
        chunk_size = chunk_size or self.chunk_size
        overlap = overlap or self.chunk_overlap

        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            # Get chunk
            end = start + chunk_size
            chunk = text[start:end]

            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence ending
                last_period = chunk.rfind('.')
                last_newline = chunk.rfind('\n')
                break_point = max(last_period, last_newline)

                if break_point > chunk_size // 2:  # Only break if in latter half
                    chunk = chunk[:break_point + 1]
                    end = start + break_point + 1

            chunks.append(chunk.strip())

            # Move to next chunk with overlap
            start = end - overlap

        return chunks

    def chunk_content(self, content_obj: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Create chunks from content object.

        Args:
            content_obj: Content dictionary

        Returns:
            List of chunk dictionaries
        """
        text = content_obj.get('content', '')
        chunks = self.chunk_text(text)

        chunk_objs = []
        for idx, chunk in enumerate(chunks):
            chunk_obj = {
                'content_id': content_obj['id'],
                'chunk_index': idx,
                'total_chunks': len(chunks),
                'text': chunk,
                'metadata': {
                    **content_obj.get('metadata', {}),
                    'chunk_info': {
                        'index': idx,
                        'total': len(chunks)
                    }
                }
            }
            chunk_objs.append(chunk_obj)

        return chunk_objs

    def extract_topics(self, text: str) -> List[str]:
        """
        Extract topics from text using keyword patterns.

        Args:
            text: Text to analyze

        Returns:
            List of topics
        """
        topics = []

        # Define topic patterns
        topic_patterns = {
            'blockchain': r'\b(blockchain|crypto|bitcoin|ethereum|web3|defi)\b',
            'productivity': r'\b(productivity|efficiency|time management|habits|goals)\b',
            'business': r'\b(business|startup|entrepreneur|company|revenue)\b',
            'technology': r'\b(technology|tech|software|ai|machine learning)\b',
            'health': r'\b(health|fitness|wellness|nutrition|exercise)\b',
            'finance': r'\b(finance|investment|money|wealth|portfolio)\b',
            'learning': r'\b(learning|education|knowledge|study|skill)\b',
            'network': r'\b(network|community|social|connection)\b',
        }

        text_lower = text.lower()

        for topic, pattern in topic_patterns.items():
            if re.search(pattern, text_lower):
                topics.append(topic)

        return topics

    def extract_mentions(self, text: str) -> List[str]:
        """
        Extract @mentions from text.

        Args:
            text: Text to analyze

        Returns:
            List of mentions
        """
        mention_pattern = r'@(\w+)'
        mentions = re.findall(mention_pattern, text)
        return list(set(mentions))  # Remove duplicates

    def extract_urls(self, text: str) -> List[str]:
        """
        Extract URLs from text.

        Args:
            text: Text to analyze

        Returns:
            List of URLs
        """
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        urls = re.findall(url_pattern, text)
        return urls

    def calculate_readability(self, text: str) -> float:
        """
        Calculate simple readability score (Flesch Reading Ease approximation).

        Args:
            text: Text to analyze

        Returns:
            Readability score (0-100, higher is easier to read)
        """
        # Count sentences
        sentences = re.split(r'[.!?]+', text)
        num_sentences = len([s for s in sentences if s.strip()])

        # Count words
        words = text.split()
        num_words = len(words)

        # Count syllables (simple approximation)
        num_syllables = sum(self._count_syllables(word) for word in words)

        if num_sentences == 0 or num_words == 0:
            return 0

        # Flesch Reading Ease formula (simplified)
        avg_sentence_length = num_words / num_sentences
        avg_syllables_per_word = num_syllables / num_words

        score = 206.835 - 1.015 * avg_sentence_length - 84.6 * avg_syllables_per_word

        return max(0, min(100, score))

    def _count_syllables(self, word: str) -> int:
        """Count syllables in a word (simple approximation)."""
        word = word.lower()
        vowels = 'aeiouy'
        syllable_count = 0
        previous_was_vowel = False

        for char in word:
            is_vowel = char in vowels
            if is_vowel and not previous_was_vowel:
                syllable_count += 1
            previous_was_vowel = is_vowel

        # Adjust for silent e
        if word.endswith('e'):
            syllable_count -= 1

        # Minimum 1 syllable
        return max(1, syllable_count)
