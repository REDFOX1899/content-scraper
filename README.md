# 🚀 Multi-Source Content Scraper

<div align="center">

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](http://makeapullrequest.com)

**A powerful, extensible content scraping system for collecting authentic content from public figures across multiple platforms.**

[Features](#-features) • [Quick Start](#-quick-start) • [Installation](#-installation) • [Usage](#-usage) • [Documentation](#-documentation) • [Contributing](#-contributing)

</div>

---

## 🌟 Overview

Scrape, validate, and analyze content from your favorite thought leaders across **Twitter, YouTube, Blogs, Podcasts, and Books**. Built with authenticity validation, AI-powered processing, and vector embeddings for semantic search.

**Currently supports:**
- 🎯 **Balaji Srinivasan** (@balajis)
- 📚 **Tim Ferriss** (@tferriss)

**Easily extensible** to any public figure!

## ✨ Features

### 🔍 Multi-Platform Scraping
- **Twitter/X**: Full tweet history + automatic thread reconstruction
- **YouTube**: Video metadata + automatic transcript extraction
- **Blogs**: Full article text from personal blogs (tim.blog, balajis.com)
- **Podcasts**: RSS feed parsing + episode metadata
- **Books**: Online books & blog excerpts

### ✅ Authenticity Validation
- **Domain Verification**: Ensures content is from official sources
- **Platform-Specific Checks**: Twitter handles, YouTube channels, etc.
- **Authenticity Scoring**: 0-100 score for each piece of content
- **Configurable Filters**: Only save high-quality, authentic content

### 🧠 AI-Powered Processing
- **Text Cleaning**: Automatic normalization and cleaning
- **Keyword Extraction**: Identify main topics and themes
- **Content Chunking**: Smart chunking with configurable overlap
- **OpenAI Embeddings**: Generate vector embeddings for semantic search
- **Structured Data Extraction**: Extract goals, strategies, principles

### 💾 Flexible Storage
- **SQL Database**: SQLAlchemy with SQLite/PostgreSQL support
- **Vector Stores**: Pinecone, ChromaDB, or Weaviate integration
- **JSON Export**: Export data in standard formats
- **Incremental Updates**: Only scrape new content

### 🛡️ Production-Ready
- **Rate Limiting**: Respects API limits with token bucket algorithm
- **Robots.txt Compliance**: Ethical web scraping
- **Retry Logic**: Exponential backoff for failed requests
- **Comprehensive Logging**: Debug and monitor with loguru
- **Error Handling**: Graceful degradation and error recovery
- **Progress Tracking**: Real-time progress bars with tqdm

## 🚀 Quick Start

### 1️⃣ Installation

```bash
# Clone the repository
git clone https://github.com/REDFOX1899/content-scraper.git
cd content-scraper

# Run automated setup
./setup.sh
```

Or manually:

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
```

### 2️⃣ Configuration

Edit `.env` and add your API keys:

```bash
TWITTER_BEARER_TOKEN=your_token_here
YOUTUBE_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here  # Optional, for embeddings
```

### 3️⃣ Start Scraping!

```bash
# Scrape Tim Ferriss blog posts
python main.py scrape --author tim_ferriss --platform blog --max-items 20

# Scrape Balaji's tweets
python main.py scrape --author balaji_srinivasan --platform twitter --max-items 50

# Scrape with embeddings for AI applications
python main.py scrape --author tim_ferriss --platform blog --embed --max-items 100
```

## 📋 Usage

### Basic Commands

```bash
# Scrape specific platform
python main.py scrape --author tim_ferriss --platform blog --max-items 50

# Scrape multiple platforms
python main.py scrape --author balaji_srinivasan \
  --platform twitter \
  --platform youtube \
  --max-items 100

# Scrape with date filter
python main.py scrape --author tim_ferriss \
  --date-from 2023-01-01 \
  --date-to 2024-01-01

# Only save authentic content
python main.py scrape --author balaji_srinivasan --authentic-only

# Process existing data
python main.py process --limit 100 --embed

# View statistics
python main.py stats

# Export to JSON
python main.py export --author tim_ferriss --output data.json
```

### Python API

```python
from scrapers.blog_scraper import BlogScraper
from validators.authenticity_validator import AuthenticityValidator
from storage.database import ContentDatabase

# Initialize scraper
scraper = BlogScraper('tim_ferriss', author_config)

# Scrape content
content = scraper.scrape(max_pages=10)

# Validate authenticity
validator = AuthenticityValidator()
validated = validator.validate_batch(content)

# Store in database
db = ContentDatabase()
db.save_batch(validated)
```

See [example_usage.py](example_usage.py) for more examples.

## 🏗️ Architecture

```
┌─────────────────┐
│   User Input    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  CLI Interface  │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────┐
│      Orchestrator               │
│  ┌─────────────────────────┐   │
│  │  Platform Scrapers      │   │
│  │  • Blog                 │   │
│  │  • Twitter              │   │
│  │  • YouTube              │   │
│  │  • Podcast              │   │
│  │  • Book                 │   │
│  └─────────────────────────┘   │
└───────────┬─────────────────────┘
            │
            ▼
    ┌───────────────┐
    │  Validator    │
    │  (Score 0-100)│
    └───────┬───────┘
            │
            ▼
    ┌───────────────┐
    │   Processor   │
    │  • Clean      │
    │  • Extract    │
    │  • Chunk      │
    └───────┬───────┘
            │
            ▼
    ┌───────────────┐
    │   Embeddings  │
    │   (OpenAI)    │
    └───────┬───────┘
            │
            ▼
┌───────────────────────┐
│      Storage          │
│  ┌────────────────┐   │
│  │  SQL Database  │   │
│  │  Vector Store  │   │
│  │  JSON Export   │   │
│  └────────────────┘   │
└───────────────────────┘
```

## 📁 Project Structure

```
content-scraper/
├── config/                     # Configuration
│   ├── settings.py            # Main settings
│   └── authors.json           # Author profiles
├── scrapers/                   # Platform scrapers
│   ├── base_scraper.py        # Base class
│   ├── blog_scraper.py
│   ├── twitter_scraper.py
│   ├── youtube_scraper.py
│   ├── podcast_scraper.py
│   └── book_scraper.py
├── validators/                 # Content validation
│   └── authenticity_validator.py
├── storage/                    # Data storage
│   ├── database.py            # SQL database
│   └── vector_store.py        # Vector stores
├── processing/                 # Content processing
│   ├── text_processor.py
│   └── content_extractor.py
├── utils/                      # Utilities
│   └── rate_limiter.py
├── main.py                     # CLI interface
├── example_usage.py            # Examples
└── README.md                   # This file
```

## 🎯 Use Cases

### 1. **AI-Powered Knowledge Base**
Build a semantic search engine over your favorite thought leader's content:
```python
# Scrape with embeddings
python main.py scrape --author tim_ferriss --embed

# Use vector store for semantic search
from storage.vector_store import create_vector_store
store = create_vector_store("chroma")
results = store.query(question_embedding, top_k=5)
```

### 2. **Research & Analysis**
Analyze trends, topics, and insights:
```python
# Export data
python main.py export --output data.json

# Analyze with pandas
import pandas as pd
df = pd.read_json('data.json')
df['keywords'].value_counts()
```

### 3. **Content Curation**
Curate the best content automatically:
```bash
# Get only high-quality, authentic content
python main.py scrape --author balaji_srinivasan \
  --authentic-only \
  --date-from 2024-01-01
```

### 4. **Chatbot Training**
Train AI chatbots on authentic content:
- Scrape content with embeddings
- Store in vector database
- Build RAG (Retrieval-Augmented Generation) system

## 🔧 Configuration

### Adding New Authors

Edit `config/authors.json`:

```json
{
  "new_author": {
    "name": "Author Name",
    "twitter": {"handle": "username"},
    "youtube_channels": [{
      "name": "Channel Name",
      "channel_id": "UCxxxxx"
    }],
    "blogs": [{
      "name": "Blog Name",
      "url": "https://blog.com"
    }],
    "official_domains": ["blog.com", "website.com"]
  }
}
```

### Customizing Settings

Edit `config/settings.py`:

```python
# Rate limiting
RATE_LIMIT_CALLS = 10
RATE_LIMIT_PERIOD = 60  # seconds

# Content filtering
MIN_AUTHENTICITY_SCORE = 75
MIN_CONTENT_LENGTH = 100

# Text processing
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

# Embeddings
EMBEDDING_MODEL = "text-embedding-ada-002"
```

## 📊 Database Schema

```sql
CREATE TABLE content (
    id VARCHAR(64) PRIMARY KEY,
    author VARCHAR(100) NOT NULL,
    platform VARCHAR(50) NOT NULL,
    content_type VARCHAR(50),
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    url TEXT NOT NULL,
    date_published DATETIME,
    date_scraped DATETIME NOT NULL,
    authenticity_score INTEGER,
    processed BOOLEAN DEFAULT FALSE,
    embedded BOOLEAN DEFAULT FALSE,
    metadata JSON,
    word_count INTEGER
);
```

## 🔑 API Keys

### Twitter API
1. Go to [Twitter Developer Portal](https://developer.twitter.com/)
2. Create a new app
3. Copy the **Bearer Token**

### YouTube Data API
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create project → Enable YouTube Data API v3
3. Create credentials → Copy **API Key**

### OpenAI API (Optional)
1. Go to [OpenAI Platform](https://platform.openai.com/)
2. Create API key
3. Used for embeddings and content analysis

## 🚦 Rate Limits & Best Practices

- **Twitter**: ~300 requests per 15 minutes (managed automatically)
- **YouTube**: 10,000 quota units per day
- **Blogs**: Respectful 2-second delays between requests
- **Robots.txt**: Always respected

**Best Practices:**
- Start with `--max-items 10` to test
- Use `--date-from` for incremental updates
- Use `--authentic-only` for quality data
- Monitor `logs/scraper.log`
- Export data regularly

## 🤝 Contributing

We welcome contributions! Here's how you can help:

### Adding New Platforms

1. Create a new scraper inheriting from `BaseScraper`
2. Implement the `scrape()` method
3. Add platform validation
4. Submit a PR!

```python
from scrapers.base_scraper import BaseScraper

class NewPlatformScraper(BaseScraper):
    def scrape(self, **kwargs):
        # Your scraping logic
        return content_list
```

### Adding New Authors

1. Add configuration to `config/authors.json`
2. Add official domains for validation
3. Test thoroughly
4. Submit a PR!

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## 📖 Documentation

- [Quick Start Guide](QUICKSTART.md) - Get started in 5 minutes
- [Example Usage](example_usage.py) - Code examples
- [API Documentation](docs/) - Detailed API docs (coming soon)

## 🐛 Troubleshooting

### Common Issues

**"Twitter API key not found"**
```bash
# Add to .env
TWITTER_BEARER_TOKEN=your_token_here
```

**"Rate limit exceeded"**
```bash
# Wait and retry, or reduce max-items
python main.py scrape --author tim_ferriss --max-items 10
```

**"No module named 'tweepy'"**
```bash
pip install -r requirements.txt
```

**Database locked**
```bash
# Only one process can write at a time
# Wait for current operation to complete
```

See [QUICKSTART.md](QUICKSTART.md) for more troubleshooting tips.

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚖️ Legal & Ethics

- ✅ Only scrapes **publicly available** content
- ✅ Respects **robots.txt** files
- ✅ Implements **rate limiting**
- ✅ Does **NOT** scrape private or paywalled content
- ✅ For **personal use, research, and education**

**Important**: Always respect the terms of service of the platforms you're scraping. This tool is designed for ethical, legal use only.

## 🙏 Acknowledgments

Built for learning from:
- **Balaji Srinivasan** ([@balajis](https://twitter.com/balajis)) - Entrepreneur, investor, thought leader
- **Tim Ferriss** ([@tferriss](https://twitter.com/tferriss)) - Author, podcaster, entrepreneur

This tool helps fans and researchers analyze and learn from their public content.

## ⭐ Star History

If you find this project useful, please consider giving it a star! ⭐

## 🗺️ Roadmap

- [ ] Add more authors (Paul Graham, Naval Ravikant, etc.)
- [ ] Web dashboard for browsing scraped content
- [ ] REST API endpoints
- [ ] Docker support
- [ ] Incremental update scheduler
- [ ] Content deduplication
- [ ] Advanced ML-based topic modeling
- [ ] Notion/Obsidian export
- [ ] Browser extension

## 💬 Community

- **Issues**: [GitHub Issues](https://github.com/REDFOX1899/content-scraper/issues)
- **Discussions**: [GitHub Discussions](https://github.com/REDFOX1899/content-scraper/discussions)
- **Pull Requests**: [Contributing Guide](CONTRIBUTING.md)

---

<div align="center">

**Built with ❤️ for the learning community**

[⬆ back to top](#-multi-source-content-scraper)

</div>
