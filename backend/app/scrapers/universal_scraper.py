"""
Universal scraper for company blogs and news pages
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from loguru import logger
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re

from app.core.config import settings


class UniversalBlogScraper:
    """Universal scraper that can scrape blogs from any company"""
    
    def __init__(self):
        self.session = httpx.AsyncClient(
            headers={'User-Agent': settings.SCRAPER_USER_AGENT},
            timeout=settings.SCRAPER_TIMEOUT,
            follow_redirects=True
        )
    
    def _detect_blog_url(self, website: str) -> List[str]:
        """Detect possible blog/news URLs from company website"""
        base_url = website.rstrip('/')
        
        # Common blog/news URL patterns
        patterns = [
            f"{base_url}/blog",
            f"{base_url}/news",
            f"{base_url}/blog/",
            f"{base_url}/news/",
            f"{base_url}/insights",
            f"{base_url}/updates",
            f"{base_url}/press",
            f"{base_url}/newsroom",
            f"{base_url}/press-releases",
            f"{base_url}/company/blog",
            f"{base_url}/company/news",
            f"{base_url}/resources/blog",
            f"{base_url}/hub/blog",
        ]
        
        return patterns
    
    def _extract_articles(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, Any]]:
        """Extract article links from page"""
        articles = []
        
        # Common article selectors
        selectors = [
            'article a',
            'div.post a',
            'div.blog-post a',
            'div.news-item a',
            'h2 a',
            'h3 a',
            'a[href*="/blog/"]',
            'a[href*="/news/"]',
            'a[href*="/post/"]',
            'a[href*="/article/"]',
            '.article-link',
            '.post-link',
            '.news-link',
        ]
        
        found_links = set()
        
        for selector in selectors:
            elements = soup.select(selector)
            
            for element in elements:
                href = element.get('href', '')
                title = element.get_text(strip=True)
                
                # Skip if no href or title
                if not href or not title or len(title) < 10:
                    continue
                
                # Build full URL
                full_url = urljoin(base_url, href)
                
                # Skip duplicates
                if full_url in found_links:
                    continue
                
                # Skip non-article URLs (images, PDFs, etc.)
                if any(ext in full_url.lower() for ext in ['.jpg', '.png', '.pdf', '.zip', '.mp4']):
                    continue
                
                # Skip social media and external links
                base_domain = urlparse(base_url).netloc
                link_domain = urlparse(full_url).netloc
                if link_domain and base_domain not in link_domain:
                    continue
                
                # Check if looks like an article URL
                article_patterns = ['/blog/', '/news/', '/post/', '/article/', '/update/', '/insight/', '/press/']
                if any(pattern in full_url.lower() for pattern in article_patterns):
                    found_links.add(full_url)
                    articles.append({
                        'url': full_url,
                        'title': title[:500]
                    })
        
        return articles
    
    async def scrape_company_blog(
        self, 
        company_name: str, 
        website: str, 
        max_articles: int = 10
    ) -> List[Dict[str, Any]]:
        """Scrape blog/news from a company website"""
        logger.info(f"Scraping blog for: {company_name}")
        
        news_items = []
        
        try:
            # Try different blog URL patterns
            blog_urls = self._detect_blog_url(website)
            
            for blog_url in blog_urls:
                try:
                    logger.info(f"Trying URL: {blog_url}")
                    response = await self.session.get(blog_url)
                    
                    # Skip if not found
                    if response.status_code == 404:
                        continue
                    
                    if response.status_code != 200:
                        continue
                    
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Extract articles
                    articles = self._extract_articles(soup, blog_url)
                    
                    if not articles:
                        continue
                    
                    logger.info(f"Found {len(articles)} articles at {blog_url}")
                    
                    # Process articles
                    for idx, article in enumerate(articles[:max_articles]):
                        # Detect source type from URL
                        source_type = 'blog'
                        if '/news/' in article['url'].lower():
                            source_type = 'news_site'
                        elif '/press/' in article['url'].lower():
                            source_type = 'press_release'
                        
                        news_items.append({
                            'title': article['title'],
                            'content': f"Article from {company_name}: {article['title']}",
                            'summary': article['title'][:200],
                            'source_url': article['url'],
                            'source_type': source_type,
                            'company_name': company_name,
                            'category': 'product_update',
                            'published_at': datetime.now() - timedelta(days=idx),
                        })
                    
                    # If we found articles, stop trying other URLs
                    if news_items:
                        break
                        
                except httpx.HTTPError as e:
                    logger.debug(f"HTTP error for {blog_url}: {e}")
                    continue
                except Exception as e:
                    logger.debug(f"Error scraping {blog_url}: {e}")
                    continue
            
            if news_items:
                logger.info(f"Successfully scraped {len(news_items)} items from {company_name}")
            else:
                logger.warning(f"No articles found for {company_name}")
            
            return news_items
            
        except Exception as e:
            logger.error(f"Failed to scrape {company_name}: {e}")
            return []
    
    async def scrape_multiple_companies(
        self, 
        companies: List[Dict[str, str]], 
        max_articles_per_company: int = 5
    ) -> List[Dict[str, Any]]:
        """Scrape blogs from multiple companies"""
        logger.info(f"Scraping blogs from {len(companies)} companies...")
        
        all_news = []
        
        for company in companies:
            company_name = company.get('name')
            website = company.get('website')
            
            if not company_name or not website:
                continue
            
            news = await self.scrape_company_blog(
                company_name, 
                website, 
                max_articles=max_articles_per_company
            )
            all_news.extend(news)
        
        logger.info(f"Total scraped: {len(all_news)} news items from {len(companies)} companies")
        return all_news
    
    async def close(self):
        """Close HTTP session"""
        await self.session.aclose()




