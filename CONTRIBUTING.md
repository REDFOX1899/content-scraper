# Contributing to Multi-Source Content Scraper

First off, thank you for considering contributing to this project! 🎉

The following is a set of guidelines for contributing. These are mostly guidelines, not rules. Use your best judgment, and feel free to propose changes to this document in a pull request.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
  - [Reporting Bugs](#reporting-bugs)
  - [Suggesting Enhancements](#suggesting-enhancements)
  - [Adding New Authors](#adding-new-authors)
  - [Adding New Platforms](#adding-new-platforms)
  - [Pull Requests](#pull-requests)
- [Development Setup](#development-setup)
- [Style Guidelines](#style-guidelines)
- [Commit Messages](#commit-messages)

## Code of Conduct

This project and everyone participating in it is governed by our commitment to creating a welcoming and inclusive environment. By participating, you are expected to:

- Be respectful and inclusive
- Accept constructive criticism gracefully
- Focus on what is best for the community
- Show empathy towards others

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues to avoid duplicates. When you create a bug report, include as many details as possible:

**Bug Report Template:**

```markdown
## Description
A clear description of the bug.

## Steps to Reproduce
1. Step one
2. Step two
3. See error

## Expected Behavior
What you expected to happen.

## Actual Behavior
What actually happened.

## Environment
- OS: [e.g., macOS 14.0]
- Python Version: [e.g., 3.10.0]
- Scraper Version: [e.g., 1.0.0]

## Logs
```
Paste relevant log output here
```

## Additional Context
Any other context about the problem.
```

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, include:

- **Clear title** describing the enhancement
- **Detailed description** of the proposed functionality
- **Use cases** explaining why this would be useful
- **Possible implementation** if you have ideas

### Adding New Authors

We love expanding support to more public figures! To add a new author:

1. **Check if the author's content is publicly available**
2. **Identify their platforms** (Twitter, YouTube, blog, etc.)
3. **Find official domains** for authenticity validation

**Steps:**

1. Fork the repository
2. Add author configuration to `config/authors.json`:

```json
{
  "author_id": {
    "name": "Author Name",
    "twitter": {
      "handle": "username",
      "verified": true
    },
    "youtube_channels": [
      {
        "name": "Channel Name",
        "channel_id": "UCxxxxxxxxx",
        "url": "https://www.youtube.com/@username"
      }
    ],
    "blogs": [
      {
        "name": "Blog Name",
        "url": "https://blog.com",
        "type": "personal"
      }
    ],
    "podcasts": [
      {
        "name": "Podcast Name",
        "rss_url": "https://podcast.com/rss"
      }
    ],
    "books": [
      {
        "title": "Book Title",
        "url": "https://book-website.com",
        "publicly_available": true
      }
    ],
    "official_domains": [
      "blog.com",
      "official-site.com"
    ]
  }
}
```

3. Test thoroughly:
```bash
python main.py scrape --author author_id --platform blog --max-items 5
```

4. Submit a pull request

### Adding New Platforms

To add support for a new platform (e.g., LinkedIn, Medium, Substack):

1. **Create a new scraper** in `scrapers/`:

```python
"""
Platform scraper for [Platform Name].
"""
from typing import List, Dict, Any, Optional
from datetime import datetime

from scrapers.base_scraper import BaseScraper
from loguru import logger


class PlatformScraper(BaseScraper):
    """Scraper for [Platform Name]."""

    def __init__(self, author_id: str, author_config: Dict[str, Any]):
        """Initialize scraper."""
        super().__init__(author_id, author_config)
        # Platform-specific initialization

    def scrape(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Scrape content from platform.

        Returns:
            List of content objects
        """
        all_content = []

        # Your scraping logic here

        return all_content
```

2. **Add platform validation** in `validators/authenticity_validator.py`:

```python
def _verify_platform(self, author_id: str, platform: str, metadata: Dict[str, Any]) -> int:
    # ... existing code ...

    elif platform == 'your_platform':
        return self._verify_your_platform(author_config, metadata)
```

3. **Update main orchestrator** in `main.py`:

```python
def _scrape_platform(self, ...):
    # ... existing code ...

    elif platform == 'your_platform':
        scraper = YourPlatformScraper(author_id, author_config)
        content = scraper.scrape(...)
```

4. **Add tests** (when testing framework is set up)

5. **Update documentation**:
   - Add to README.md
   - Add usage examples
   - Update author configuration schema

### Pull Requests

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes**
4. **Test thoroughly**
5. **Commit with clear messages**: `git commit -m 'Add amazing feature'`
6. **Push to your fork**: `git push origin feature/amazing-feature`
7. **Open a Pull Request**

**PR Checklist:**
- [ ] Code follows the project's style guidelines
- [ ] Self-review of code completed
- [ ] Comments added for complex logic
- [ ] Documentation updated if needed
- [ ] No new warnings generated
- [ ] Tested locally
- [ ] Updated CHANGELOG.md (if applicable)

## Development Setup

### Prerequisites

- Python 3.8+
- pip
- Virtual environment tool

### Setup Steps

```bash
# Clone your fork
git clone https://github.com/your-username/content-scraper.git
cd content-scraper

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install black flake8 pytest pytest-mock

# Copy environment template
cp .env.example .env
# Edit .env with your API keys

# Run examples to test
python example_usage.py
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=scrapers --cov=validators --cov=storage --cov=processing

# Run specific test file
pytest tests/test_blog_scraper.py
```

## Style Guidelines

### Python Code Style

We follow [PEP 8](https://pep8.org/) with some modifications:

- **Line length**: 100 characters (not 79)
- **Indentation**: 4 spaces (no tabs)
- **Quotes**: Single quotes for strings, double for docstrings
- **Imports**: Grouped (standard library, third-party, local)

**Format code with Black:**

```bash
black scrapers/ validators/ storage/ processing/ utils/
```

**Check with flake8:**

```bash
flake8 scrapers/ validators/ storage/ processing/ utils/
```

### Docstring Style

Use Google-style docstrings:

```python
def function_name(param1: str, param2: int) -> bool:
    """
    Brief description of function.

    Longer description if needed. Can span multiple lines
    and include additional context.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Description of return value

    Raises:
        ValueError: When this happens
        TypeError: When that happens

    Examples:
        >>> function_name("test", 42)
        True
    """
    pass
```

### File Organization

```python
"""
Module docstring.
"""
# Standard library imports
import os
from datetime import datetime

# Third-party imports
import requests
from loguru import logger

# Local imports
from config.settings import SETTING_NAME
from scrapers.base_scraper import BaseScraper

# Constants
CONSTANT_NAME = "value"

# Classes
class ClassName:
    pass

# Functions
def function_name():
    pass
```

## Commit Messages

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation changes
- **style**: Code style changes (formatting, no logic change)
- **refactor**: Code refactoring
- **test**: Adding or updating tests
- **chore**: Maintenance tasks

### Examples

```
feat(twitter): Add support for Twitter Spaces

Implement scraper for Twitter Spaces audio content.
Includes metadata extraction and optional audio download.

Closes #123
```

```
fix(database): Fix duplicate key error on content insert

Handle case where same content ID already exists in database.
Now updates existing record instead of failing.

Fixes #456
```

```
docs(readme): Update installation instructions

Add troubleshooting section for common API key issues.
```

## Testing Guidelines

### Writing Tests

```python
import pytest
from scrapers.blog_scraper import BlogScraper


def test_blog_scraper_initialization():
    """Test BlogScraper initializes correctly."""
    author_config = {
        'name': 'Test Author',
        'blogs': [{'name': 'Test Blog', 'url': 'https://test.com'}]
    }

    scraper = BlogScraper('test_author', author_config)

    assert scraper.author_id == 'test_author'
    assert scraper.author_name == 'Test Author'


def test_blog_scraper_validates_content():
    """Test blog content validation."""
    # Test implementation
    pass
```

### Test Coverage

Aim for:
- **Core functionality**: 80%+ coverage
- **Critical paths**: 90%+ coverage
- **Edge cases**: Well documented

## Documentation

### Code Documentation

- **All public functions**: Must have docstrings
- **Classes**: Must have class docstrings
- **Modules**: Must have module docstrings
- **Complex logic**: Inline comments explaining why, not what

### README Updates

When adding features, update:
- Feature list
- Usage examples
- Configuration section
- Troubleshooting (if applicable)

## Community

### Getting Help

- **GitHub Discussions**: For questions and discussions
- **GitHub Issues**: For bugs and feature requests
- **Discord** (coming soon): For real-time chat

### Recognition

Contributors will be recognized in:
- README.md Contributors section
- CHANGELOG.md for significant contributions
- Release notes

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

**Thank you for contributing! 🙏**

Every contribution, no matter how small, is valuable and appreciated.
