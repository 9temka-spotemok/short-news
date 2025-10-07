"""
OpenAI blog scraper
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import re
from loguru import logger

from .base import BaseScraper


class OpenAIScraper(BaseScraper):
    """Scraper for OpenAI blog"""
    
    def __init__(self):
        super().__init__(
            source_id="openai_blog",
            base_url="https://openai.com"
        )
        self.blog_url = "https://openai.com/blog"
    
    async def scrape(self) -> List[Dict[str, Any]]:
        """
        Scrape OpenAI blog for new posts
        """
        logger.info("Starting OpenAI blog scraping")
        
        try:
            # Fetch main blog page
            soup = await self.fetch_page(self.blog_url)
            if not soup:
                logger.error("Failed to fetch OpenAI blog page")
                return []
            
            # Extract blog post links
            post_links = await self.extract_blog_links(soup)
            logger.info(f"Found {len(post_links)} blog posts")
            
            # Scrape each post
            posts = []
            for link in post_links[:10]:  # Limit to 10 most recent posts
                try:
                    post_data = await self.scrape_post(link)
                    if post_data:
                        posts.append(post_data)
                except Exception as e:
                    logger.error(f"Failed to scrape post {link}: {e}")
                    continue
            
            logger.info(f"Successfully scraped {len(posts)} OpenAI blog posts")
            return posts
            
        except Exception as e:
            logger.error(f"OpenAI blog scraping failed: {e}")
            return []
    
    async def extract_blog_links(self, soup) -> List[str]:
        """
        Extract blog post links from the main blog page
        """
        links = []
        
        # Try different selectors for blog post links
        selectors = [
            'a[href*="/blog/"]',
            '.blog-post a',
            '.post-link',
            'article a',
            'h2 a',
            'h3 a'
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            for element in elements:
                href = element.get('href')
                if href and '/blog/' in href:
                    # Convert relative URLs to absolute
                    if href.startswith('/'):
                        href = self.base_url + href
                    elif not href.startswith('http'):
                        href = self.base_url + '/' + href
                    
                    if href not in links:
                        links.append(href)
        
        return links
    
    async def scrape_post(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Scrape individual blog post
        """
        try:
            soup = await self.fetch_page(url)
            if not soup:
                return None
            
            # Extract post data
            title = await self.extract_title(soup)
            content = await self.extract_content(soup)
            summary = await self.extract_summary(soup)
            published_date = await self.extract_published_date(soup)
            author = await self.extract_author(soup)
            
            if not title or not content:
                logger.warning(f"Missing required data for post: {url}")
                return None
            
            # Generate summary if not found
            if not summary:
                summary = self.summarize_text(content, max_length=200)
            
            post_data = {
                'title': self.normalize_text(title),
                'content': self.normalize_text(content),
                'summary': self.normalize_text(summary),
                'source_url': url,
                'source_type': 'blog',
                'company_id': 'openai',  # Will be resolved to actual UUID
                'published_at': published_date or datetime.now(),
                'author': author,
                'scraped_at': datetime.now(),
            }
            
            logger.info(f"Scraped post: {title[:50]}...")
            return post_data
            
        except Exception as e:
            logger.error(f"Failed to scrape post {url}: {e}")
            return None
    
    async def extract_title(self, soup) -> Optional[str]:
        """
        Extract post title
        """
        selectors = [
            'h1',
            '.post-title',
            '.blog-title',
            'title',
            'h2',
            '.entry-title'
        ]
        
        for selector in selectors:
            title = await self.extract_text(soup, selector)
            if title and len(title) > 10:  # Basic validation
                return title
        
        return None
    
    async def extract_content(self, soup) -> Optional[str]:
        """
        Extract post content
        """
        # Remove unwanted elements
        for element in soup.select('script, style, nav, footer, .advertisement, .sidebar'):
            element.decompose()
        
        selectors = [
            '.post-content',
            '.blog-content',
            '.entry-content',
            'article',
            '.content',
            'main'
        ]
        
        for selector in selectors:
            content_element = soup.select_one(selector)
            if content_element:
                # Extract text from all paragraphs
                paragraphs = content_element.select('p')
                content = ' '.join([p.get_text(strip=True) for p in paragraphs])
                
                if content and len(content) > 100:  # Basic validation
                    return content
        
        return None
    
    async def extract_summary(self, soup) -> Optional[str]:
        """
        Extract post summary
        """
        selectors = [
            '.post-summary',
            '.blog-summary',
            '.excerpt',
            'meta[name="description"]',
            '.intro'
        ]
        
        for selector in selectors:
            summary = await self.extract_text(soup, selector)
            if summary and len(summary) > 20:
                return summary
        
        return None
    
    async def extract_published_date(self, soup) -> Optional[datetime]:
        """
        Extract published date
        """
        selectors = [
            '.post-date',
            '.blog-date',
            '.published-date',
            'time',
            '.date'
        ]
        
        for selector in selectors:
            date_text = await self.extract_text(soup, selector)
            if date_text:
                # Try to parse date
                parsed_date = self.parse_date(date_text)
                if parsed_date:
                    return parsed_date
        
        # Try meta tags
        meta_date = soup.select_one('meta[property="article:published_time"]')
        if meta_date:
            date_str = meta_date.get('content')
            if date_str:
                parsed_date = self.parse_date(date_str)
                if parsed_date:
                    return parsed_date
        
        return None
    
    async def extract_author(self, soup) -> Optional[str]:
        """
        Extract post author
        """
        selectors = [
            '.post-author',
            '.blog-author',
            '.author',
            'meta[name="author"]'
        ]
        
        for selector in selectors:
            author = await self.extract_text(soup, selector)
            if author:
                return author
        
        return None
    
    def parse_date(self, date_str: str) -> Optional[datetime]:
        """
        Parse date string to datetime object
        """
        if not date_str:
            return None
        
        # Common date formats
        date_formats = [
            '%Y-%m-%d',
            '%Y-%m-%d %H:%M:%S',
            '%B %d, %Y',
            '%d %B %Y',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%SZ',
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue
        
        # Try regex patterns
        patterns = [
            r'(\d{4}-\d{2}-\d{2})',
            r'(\d{1,2}/\d{1,2}/\d{4})',
            r'(\w+ \d{1,2}, \d{4})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, date_str)
            if match:
                try:
                    return datetime.strptime(match.group(1), '%Y-%m-%d')
                except ValueError:
                    continue
        
        logger.warning(f"Could not parse date: {date_str}")
        return None
