# Quick Start Guide

## Installation (5 minutes)

### Option 1: Automated Setup

```bash
./setup.sh
```

### Option 2: Manual Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
```

## Configuration (2 minutes)

Edit `.env` and add your API keys:

```bash
# Minimum required for basic scraping
TWITTER_BEARER_TOKEN=your_token_here      # For Twitter
YOUTUBE_API_KEY=your_key_here             # For YouTube
OPENAI_API_KEY=your_key_here              # For embeddings (optional)
```

### Where to Get API Keys

**Twitter API:**
1. Go to https://developer.twitter.com/
2. Create a developer account
3. Create a new app
4. Copy the Bearer Token

**YouTube API:**
1. Go to https://console.cloud.google.com/
2. Create a new project
3. Enable YouTube Data API v3
4. Create credentials (API Key)

**OpenAI API:**
1. Go to https://platform.openai.com/
2. Sign up/login
3. Go to API Keys section
4. Create new key

## First Scrape (1 minute)

### Scrape Tim Ferriss Blog (No API Keys Required)

```bash
python main.py scrape --author tim_ferriss --platform blog --max-items 10
```

### Scrape Twitter (Requires Twitter API)

```bash
python main.py scrape --author balajis --platform twitter --max-items 20
```

### Scrape YouTube (Requires YouTube API)

```bash
python main.py scrape --author tim_ferriss --platform youtube --max-items 5
```

## View Results

```bash
# Check database statistics
python main.py stats

# Export to JSON
python main.py export --output my_data.json

# Export specific author
python main.py export --author tim_ferriss --output tim_data.json
```

## Common Commands

### Scrape Multiple Platforms

```bash
python main.py scrape --author tim_ferriss \
  --platform blog \
  --platform twitter \
  --platform youtube \
  --max-items 50
```

### Scrape with Date Filter

```bash
python main.py scrape --author balaji_srinivasan \
  --platform blog \
  --date-from 2023-01-01 \
  --date-to 2024-01-01
```

### Scrape with Embeddings

```bash
python main.py scrape --author tim_ferriss \
  --platform blog \
  --embed \
  --max-items 20
```

### Process Existing Data

```bash
# Process unprocessed items
python main.py process --limit 100

# Process and create embeddings
python main.py process --limit 100 --embed
```

## Running Examples

```bash
python example_usage.py
```

This will demonstrate:
- Blog scraping
- Content validation
- Database operations
- Text processing
- Full pipeline

## Troubleshooting

### Error: "Twitter API key not found"

**Solution:** Add `TWITTER_BEARER_TOKEN` to your `.env` file

### Error: "YouTube API key not found"

**Solution:** Add `YOUTUBE_API_KEY` to your `.env` file

### Error: "No module named 'tweepy'"

**Solution:** Install dependencies:
```bash
pip install -r requirements.txt
```

### Database locked error

**Solution:** Only one process can write to SQLite at a time. Wait for current operation to complete.

### Rate limit errors

**Solution:** The scrapers have built-in rate limiting. If you hit API limits, wait and try again later or reduce `--max-items`.

## Next Steps

1. **Scrape More Content:**
   ```bash
   python main.py scrape --author balaji_srinivasan --platform blog --max-items 100
   python main.py scrape --author tim_ferriss --platform podcast --max-items 50
   ```

2. **Process Content:**
   ```bash
   python main.py process --limit 200 --embed
   ```

3. **Explore the Data:**
   - Check `data/content_scraper.db` with SQLite browser
   - Export JSON and analyze with pandas
   - View logs in `logs/scraper.log`

4. **Customize:**
   - Edit `config/authors.json` to add more authors
   - Modify `config/settings.py` for custom settings
   - Create custom scrapers in `scrapers/`

## Tips

1. **Start Small:** Test with `--max-items 10` first
2. **Use Filters:** `--authentic-only` ensures quality
3. **Check Logs:** Always review `logs/scraper.log` for errors
4. **Incremental Scraping:** Use date filters to scrape new content only
5. **Backup Data:** Export regularly with `python main.py export`

## Architecture Overview

```
User Request → CLI (main.py)
    ↓
Orchestrator
    ↓
Platform Scrapers → Raw Content
    ↓
Validator → Authenticity Score
    ↓
Text Processor → Cleaned + Keywords
    ↓
Embeddings (optional) → Vector Embeddings
    ↓
Storage → Database + Vector Store
```

## Support

- **Documentation:** See `README.md`
- **Examples:** Run `python example_usage.py`
- **Logs:** Check `logs/scraper.log`
- **Configuration:** Review `config/settings.py`

## What's Next?

Once you have scraped content, you can:

1. **Build a Search Engine:** Use embeddings for semantic search
2. **Create a Chatbot:** Feed content to an LLM
3. **Analyze Trends:** Process keywords and topics over time
4. **Generate Insights:** Extract principles and strategies
5. **Build a Goal Tracker:** Use structured data extraction

Happy Scraping! 🚀
