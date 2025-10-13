"""
Real scrapers for AI news sources
"""

from typing import List, Dict, Any
from datetime import datetime, timedelta
from loguru import logger
import httpx
from bs4 import BeautifulSoup

from app.core.config import settings


class AINewsScraper:
    """Scraper for various AI news sources"""
    
    def __init__(self):
        self.session = httpx.AsyncClient(
            headers={'User-Agent': settings.SCRAPER_USER_AGENT},
            timeout=settings.SCRAPER_TIMEOUT,
            follow_redirects=True
        )
    
    def _determine_category(self, title: str, company: str) -> str:
        """Determine news category based on title content"""
        title_lower = title.lower()
        
        # Technical updates
        if any(keyword in title_lower for keyword in [
            'api', 'technical', 'update', 'improvement', 'performance', 
            'optimization', 'infrastructure', 'system', 'backend'
        ]):
            return 'technical_update'
        
        # Product updates
        if any(keyword in title_lower for keyword in [
            'release', 'launch', 'new feature', 'product', 'version', 
            'update', 'announcement', 'introducing'
        ]):
            return 'product_update'
        
        # Strategic announcements
        if any(keyword in title_lower for keyword in [
            'strategy', 'partnership', 'collaboration', 'acquisition', 
            'investment', 'funding', 'business', 'market'
        ]):
            return 'strategic_announcement'
        
        # Research papers
        if any(keyword in title_lower for keyword in [
            'research', 'paper', 'study', 'analysis', 'findings', 
            'publication', 'journal'
        ]):
            return 'research_paper'
        
        # Security updates
        if any(keyword in title_lower for keyword in [
            'security', 'safety', 'privacy', 'protection', 'vulnerability'
        ]):
            return 'security_update'
        
        # Model releases
        if any(keyword in title_lower for keyword in [
            'model', 'gpt', 'claude', 'gemini', 'llama', 'training', 
            'dataset', 'weights'
        ]):
            return 'model_release'
        
        # Company-specific defaults
        company_defaults = {
            'OpenAI': 'product_update',
            'Anthropic': 'product_update', 
            'Google': 'technical_update',
            'Meta': 'product_update',
            'Hugging Face': 'technical_update',
            'Mistral AI': 'product_update',
            'Cohere': 'technical_update',
            'Stability AI': 'product_update',
            'Perplexity AI': 'product_update'
        }
        
        return company_defaults.get(company, 'product_update')
    
    async def scrape_openai_blog(self) -> List[Dict[str, Any]]:
        """Scrape OpenAI blog"""
        logger.info("Scraping OpenAI blog...")
        
        try:
            url = "https://openai.com/blog"
            response = await self.session.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            news_items = []
            # OpenAI blog structure - find article links
            articles = soup.select('a[href*="/blog/"]')[:10]
            
            for article in articles:
                href = article.get('href', '')
                if href and '/blog/' in href and href != '/blog/' and href != '/blog':
                    title = article.get_text(strip=True)
                    if title and len(title) > 10:
                        full_url = href if href.startswith('http') else f"https://openai.com{href}"
                        
                        # Determine category based on title content
                        category = self._determine_category(title, 'OpenAI')
                        
                        news_items.append({
                            'title': title[:500],
                            'content': f"Article from OpenAI blog: {title}",
                            'summary': title[:200],
                            'source_url': full_url,
                            'source_type': 'blog',
                            'company_name': 'OpenAI',
                            'category': category,
                            'published_at': datetime.now() - timedelta(days=len(news_items)),
                        })
            
            logger.info(f"Scraped {len(news_items)} items from OpenAI blog")
            return news_items[:10]  # Get more news  # Limit to 5 most recent
            
        except Exception as e:
            logger.error(f"Failed to scrape OpenAI blog: {e}")
            return []
    
    async def scrape_anthropic_news(self) -> List[Dict[str, Any]]:
        """Scrape Anthropic news"""
        logger.info("Scraping Anthropic news...")
        
        try:
            url = "https://www.anthropic.com/news"
            response = await self.session.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            news_items = []
            # Find news articles
            articles = soup.select('a[href*="/news/"]')[:10]
            
            for article in articles:
                href = article.get('href', '')
                if href and '/news/' in href and href != '/news/' and href != '/news':
                    title = article.get_text(strip=True)
                    if title and len(title) > 10:
                        full_url = href if href.startswith('http') else f"https://www.anthropic.com{href}"
                        
                        # Determine category based on title content
                        category = self._determine_category(title, 'Anthropic')
                        
                        news_items.append({
                            'title': title[:500],
                            'content': f"News from Anthropic: {title}",
                            'summary': title[:200],
                            'source_url': full_url,
                            'source_type': 'blog',
                            'company_name': 'Anthropic',
                            'category': category,
                            'published_at': datetime.now() - timedelta(days=len(news_items)),
                        })
            
            logger.info(f"Scraped {len(news_items)} items from Anthropic news")
            return news_items[:10]  # Get more news
            
        except Exception as e:
            logger.error(f"Failed to scrape Anthropic news: {e}")
            return []
    
    async def scrape_google_ai_blog(self) -> List[Dict[str, Any]]:
        """Scrape Google AI blog"""
        logger.info("Scraping Google AI blog...")
        
        try:
            url = "https://blog.google/technology/ai/"
            response = await self.session.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            news_items = []
            # Find blog posts
            articles = soup.select('article a, h3 a')[:10]
            
            for article in articles:
                href = article.get('href', '')
                title = article.get_text(strip=True)
                
                if href and title and len(title) > 10:
                    full_url = href if href.startswith('http') else f"https://blog.google{href}"
                    
                    # Determine category based on title content
                    category = self._determine_category(title, 'Google')
                    
                    news_items.append({
                        'title': title[:500],
                        'content': f"Article from Google AI Blog: {title}",
                        'summary': title[:200],
                        'source_url': full_url,
                        'source_type': 'blog',
                        'company_name': 'Google',
                        'category': category,
                        'published_at': datetime.now() - timedelta(days=len(news_items)),
                    })
            
            logger.info(f"Scraped {len(news_items)} items from Google AI blog")
            return news_items[:10]  # Get more news
            
        except Exception as e:
            logger.error(f"Failed to scrape Google AI blog: {e}")
            return []
    
    async def scrape_meta_ai_blog(self) -> List[Dict[str, Any]]:
        """Scrape Meta AI blog"""
        logger.info("Scraping Meta AI blog...")
        
        try:
            url = "https://ai.meta.com/blog/"
            response = await self.session.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            news_items = []
            # Find blog posts
            articles = soup.select('article a, h2 a, h3 a')[:15]
            
            for article in articles:
                href = article.get('href', '')
                title = article.get_text(strip=True)
                
                if href and title and len(title) > 10 and 'blog' in href:
                    full_url = href if href.startswith('http') else f"https://ai.meta.com{href}"
                    
                    # Determine category based on title content
                    category = self._determine_category(title, 'Meta')
                    
                    news_items.append({
                        'title': title[:500],
                        'content': f"Article from Meta AI Blog: {title}",
                        'summary': title[:200],
                        'source_url': full_url,
                        'source_type': 'blog',
                        'company_name': 'Meta',
                        'category': category,
                        'published_at': datetime.now() - timedelta(days=len(news_items)),
                    })
            
            logger.info(f"Scraped {len(news_items)} items from Meta AI blog")
            return news_items[:10]
            
        except Exception as e:
            logger.error(f"Failed to scrape Meta AI blog: {e}")
            return []
    
    async def scrape_huggingface_blog(self) -> List[Dict[str, Any]]:
        """Scrape Hugging Face blog"""
        logger.info("Scraping Hugging Face blog...")
        
        try:
            url = "https://huggingface.co/blog"
            response = await self.session.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            news_items = []
            # Find blog posts
            articles = soup.select('article a, h2 a')[:15]
            
            for article in articles:
                href = article.get('href', '')
                title = article.get_text(strip=True)
                
                if href and title and len(title) > 10:
                    full_url = href if href.startswith('http') else f"https://huggingface.co{href}"
                    
                    # Determine category based on title content
                    category = self._determine_category(title, 'Hugging Face')
                    
                    news_items.append({
                        'title': title[:500],
                        'content': f"Article from Hugging Face Blog: {title}",
                        'summary': title[:200],
                        'source_url': full_url,
                        'source_type': 'blog',
                        'company_name': 'Hugging Face',
                        'category': category,
                        'published_at': datetime.now() - timedelta(days=len(news_items)),
                    })
            
            logger.info(f"Scraped {len(news_items)} items from Hugging Face blog")
            return news_items[:10]
            
        except Exception as e:
            logger.error(f"Failed to scrape Hugging Face blog: {e}")
            return []
    
    async def scrape_mistral_ai_news(self) -> List[Dict[str, Any]]:
        """Scrape Mistral AI news"""
        logger.info("Scraping Mistral AI news...")
        
        try:
            url = "https://mistral.ai/news/"
            response = await self.session.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            news_items = []
            # Find news articles
            articles = soup.select('a[href*="/news/"]')[:15]
            
            for article in articles:
                href = article.get('href', '')
                title = article.get_text(strip=True)
                
                if href and title and len(title) > 10 and href != '/news/' and href != '/news':
                    full_url = href if href.startswith('http') else f"https://mistral.ai{href}"
                    
                    # Determine category based on title content
                    category = self._determine_category(title, 'Mistral AI')
                    
                    news_items.append({
                        'title': title[:500],
                        'content': f"News from Mistral AI: {title}",
                        'summary': title[:200],
                        'source_url': full_url,
                        'source_type': 'blog',
                        'company_name': 'Mistral AI',
                        'category': category,
                        'published_at': datetime.now() - timedelta(days=len(news_items)),
                    })
            
            logger.info(f"Scraped {len(news_items)} items from Mistral AI news")
            return news_items[:10]
            
        except Exception as e:
            logger.error(f"Failed to scrape Mistral AI news: {e}")
            return []
    
    async def scrape_cohere_blog(self) -> List[Dict[str, Any]]:
        """Scrape Cohere blog"""
        logger.info("Scraping Cohere blog...")
        
        try:
            url = "https://cohere.com/blog"
            response = await self.session.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            news_items = []
            # Find blog posts
            articles = soup.select('a[href*="/blog/"]')[:15]
            
            for article in articles:
                href = article.get('href', '')
                title = article.get_text(strip=True)
                
                if href and title and len(title) > 10 and href != '/blog/' and href != '/blog':
                    full_url = href if href.startswith('http') else f"https://cohere.com{href}"
                    
                    # Determine category based on title content
                    category = self._determine_category(title, 'Cohere')
                    
                    news_items.append({
                        'title': title[:500],
                        'content': f"Article from Cohere Blog: {title}",
                        'summary': title[:200],
                        'source_url': full_url,
                        'source_type': 'blog',
                        'company_name': 'Cohere',
                        'category': category,
                        'published_at': datetime.now() - timedelta(days=len(news_items)),
                    })
            
            logger.info(f"Scraped {len(news_items)} items from Cohere blog")
            return news_items[:10]
            
        except Exception as e:
            logger.error(f"Failed to scrape Cohere blog: {e}")
            return []
    
    async def scrape_stability_ai_news(self) -> List[Dict[str, Any]]:
        """Scrape Stability AI news"""
        logger.info("Scraping Stability AI news...")
        
        try:
            url = "https://stability.ai/news"
            response = await self.session.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            news_items = []
            # Find news articles
            articles = soup.select('article a, h2 a, h3 a')[:15]
            
            for article in articles:
                href = article.get('href', '')
                title = article.get_text(strip=True)
                
                if href and title and len(title) > 10:
                    full_url = href if href.startswith('http') else f"https://stability.ai{href}"
                    
                    if 'news' in full_url or 'blog' in full_url:
                        # Determine category based on title content
                        category = self._determine_category(title, 'Stability AI')
                        
                        news_items.append({
                            'title': title[:500],
                            'content': f"News from Stability AI: {title}",
                            'summary': title[:200],
                            'source_url': full_url,
                            'source_type': 'blog',
                            'company_name': 'Stability AI',
                            'category': category,
                            'published_at': datetime.now() - timedelta(days=len(news_items)),
                        })
            
            logger.info(f"Scraped {len(news_items)} items from Stability AI news")
            return news_items[:10]
            
        except Exception as e:
            logger.error(f"Failed to scrape Stability AI news: {e}")
            return []
    
    async def scrape_perplexity_blog(self) -> List[Dict[str, Any]]:
        """Scrape Perplexity AI blog"""
        logger.info("Scraping Perplexity AI blog...")
        
        try:
            url = "https://www.perplexity.ai/hub/blog"
            response = await self.session.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            news_items = []
            # Find blog posts
            articles = soup.select('article a, h2 a, h3 a')[:15]
            
            for article in articles:
                href = article.get('href', '')
                title = article.get_text(strip=True)
                
                if href and title and len(title) > 10:
                    full_url = href if href.startswith('http') else f"https://www.perplexity.ai{href}"
                    
                    if 'blog' in full_url or 'hub' in full_url:
                        # Determine category based on title content
                        category = self._determine_category(title, 'Perplexity AI')
                        
                        news_items.append({
                            'title': title[:500],
                            'content': f"Article from Perplexity AI Blog: {title}",
                            'summary': title[:200],
                            'source_url': full_url,
                            'source_type': 'blog',
                            'company_name': 'Perplexity AI',
                            'category': category,
                            'published_at': datetime.now() - timedelta(days=len(news_items)),
                        })
            
            logger.info(f"Scraped {len(news_items)} items from Perplexity AI blog")
            return news_items[:10]
            
        except Exception as e:
            logger.error(f"Failed to scrape Perplexity AI blog: {e}")
            return []
    
    async def scrape_all(self) -> List[Dict[str, Any]]:
        """Scrape all sources"""
        logger.info("Starting scraping all AI news sources...")
        
        all_news = []
        
        # Scrape each source
        openai_news = await self.scrape_openai_blog()
        all_news.extend(openai_news)
        
        anthropic_news = await self.scrape_anthropic_news()
        all_news.extend(anthropic_news)
        
        google_news = await self.scrape_google_ai_blog()
        all_news.extend(google_news)
        
        meta_news = await self.scrape_meta_ai_blog()
        all_news.extend(meta_news)
        
        hf_news = await self.scrape_huggingface_blog()
        all_news.extend(hf_news)
        
        # New sources
        mistral_news = await self.scrape_mistral_ai_news()
        all_news.extend(mistral_news)
        
        cohere_news = await self.scrape_cohere_blog()
        all_news.extend(cohere_news)
        
        stability_news = await self.scrape_stability_ai_news()
        all_news.extend(stability_news)
        
        perplexity_news = await self.scrape_perplexity_blog()
        all_news.extend(perplexity_news)
        
        logger.info(f"Total scraped: {len(all_news)} news items from 9 sources")
        return all_news
    
    async def close(self):
        """Close HTTP session"""
        await self.session.aclose()

