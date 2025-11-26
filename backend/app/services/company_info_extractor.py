"""
Service for extracting company information from website
"""

from typing import Dict, Optional
from urllib.parse import urlparse, urljoin
import httpx
from bs4 import BeautifulSoup
from loguru import logger

from app.core.config import settings


async def extract_company_info(website_url: str) -> Dict[str, Optional[str]]:
    """
    Extract company information from website homepage
    
    Args:
        website_url: URL of the company website
        
    Returns:
        Dict with name, description, logo_url, category
    """
    try:
        async with httpx.AsyncClient(
            headers={'User-Agent': settings.SCRAPER_USER_AGENT},
            timeout=settings.SCRAPER_TIMEOUT,
            follow_redirects=True
        ) as client:
            response = await client.get(website_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract company name from title or meta tags
            name = None
            if soup.title:
                title_text = soup.title.string
                if title_text:
                    # Try to extract company name from title (remove common suffixes)
                    name = title_text.split('|')[0].split('-')[0].strip()
                    name = name.replace('Home', '').replace('Welcome', '').strip()
            
            # Try meta tags
            if not name:
                og_title = soup.find('meta', property='og:title')
                if og_title and og_title.get('content'):
                    name = og_title['content'].split('|')[0].split('-')[0].strip()
            
            # Extract description
            description = None
            meta_description = soup.find('meta', attrs={'name': 'description'})
            if meta_description and meta_description.get('content'):
                description = meta_description['content'].strip()
            
            if not description:
                og_description = soup.find('meta', property='og:description')
                if og_description and og_description.get('content'):
                    description = og_description['content'].strip()
            
            # Extract logo URL
            logo_url = None
            # Try favicon first
            favicon = soup.find('link', rel='icon') or soup.find('link', rel='shortcut icon')
            if favicon and favicon.get('href'):
                favicon_href = favicon['href']
                if favicon_href.startswith('http'):
                    logo_url = favicon_href
                else:
                    logo_url = urljoin(website_url, favicon_href)
            
            # Try og:image
            if not logo_url:
                og_image = soup.find('meta', property='og:image')
                if og_image and og_image.get('content'):
                    og_image_url = og_image['content']
                    if og_image_url.startswith('http'):
                        logo_url = og_image_url
                    else:
                        logo_url = urljoin(website_url, og_image_url)
            
            # Try common logo selectors
            if not logo_url:
                logo_selectors = [
                    'img[alt*="logo" i]',
                    'img[class*="logo" i]',
                    'img[id*="logo" i]',
                    '.logo img',
                    '#logo img'
                ]
                for selector in logo_selectors:
                    logo_img = soup.select_one(selector)
                    if logo_img and logo_img.get('src'):
                        logo_src = logo_img['src']
                        if logo_src.startswith('http'):
                            logo_url = logo_src
                        else:
                            logo_url = urljoin(website_url, logo_src)
                        break
            
            # Infer category from domain/name (basic heuristic)
            category = None
            parsed_url = urlparse(website_url)
            domain = (parsed_url.netloc or '').lower()
            name_lower = (name or '').lower()
            
            if any(kw in domain or kw in name_lower for kw in ['ai', 'ml', 'machine-learning', 'artificial-intelligence']):
                category = 'llm_provider'
            elif any(kw in domain or kw in name_lower for kw in ['search', 'engine', 'seo']):
                category = 'search_engine'
            elif any(kw in domain or kw in name_lower for kw in ['tool', 'platform', 'saas', 'software']):
                category = 'toolkit'
            
            # If name is still None, try to extract from domain
            if not name:
                parsed_url = urlparse(website_url)
                domain = parsed_url.netloc or ''
                # Remove www. and extract main domain name
                domain = domain.replace('www.', '').split('.')[0]
                if domain:
                    # Capitalize properly (handle camelCase domains like "openAI" -> "OpenAI")
                    if domain.lower() in ['openai', 'anthropic', 'cohere', 'meta', 'microsoft']:
                        # Known company name mappings
                        name_mapping = {
                            'openai': 'OpenAI',
                            'anthropic': 'Anthropic',
                            'cohere': 'Cohere',
                            'meta': 'Meta',
                            'microsoft': 'Microsoft'
                        }
                        name = name_mapping.get(domain.lower(), domain.capitalize())
                    else:
                        # Capitalize first letter
                        name = domain.capitalize()
            
            return {
                'name': name,
                'description': description,
                'logo_url': logo_url,
                'category': category
            }
            
    except httpx.HTTPError as e:
        logger.warning(f"HTTP error extracting company info from {website_url}: {e}")
        # Fallback: extract name from domain
        parsed_url = urlparse(website_url)
        domain = parsed_url.netloc or ''
        domain = domain.replace('www.', '').split('.')[0]
        if domain:
            # Known company name mappings
            name_mapping = {
                'openai': 'OpenAI',
                'anthropic': 'Anthropic',
                'cohere': 'Cohere',
                'meta': 'Meta',
                'microsoft': 'Microsoft',
                'google': 'Google',
                'amazon': 'Amazon',
                'apple': 'Apple'
            }
            name = name_mapping.get(domain.lower(), domain.capitalize())
        else:
            name = None
        
        # Infer category from domain
        category = None
        domain_lower = domain.lower() if domain else ''
        if any(kw in domain_lower for kw in ['ai', 'ml', 'machine-learning', 'artificial-intelligence']):
            category = 'llm_provider'
        elif any(kw in domain_lower for kw in ['search', 'engine', 'seo']):
            category = 'search_engine'
        elif any(kw in domain_lower for kw in ['tool', 'platform', 'saas', 'software']):
            category = 'toolkit'
        
        return {
            'name': name,
            'description': None,
            'logo_url': None,
            'category': category
        }
    except Exception as e:
        logger.error(f"Failed to extract company info from {website_url}: {e}")
        # Fallback: extract name from domain
        parsed_url = urlparse(website_url)
        domain = parsed_url.netloc or ''
        domain = domain.replace('www.', '').split('.')[0]
        if domain:
            # Known company name mappings
            name_mapping = {
                'openai': 'OpenAI',
                'anthropic': 'Anthropic',
                'cohere': 'Cohere',
                'meta': 'Meta',
                'microsoft': 'Microsoft',
                'google': 'Google',
                'amazon': 'Amazon',
                'apple': 'Apple'
            }
            name = name_mapping.get(domain.lower(), domain.capitalize())
        else:
            name = None
        
        # Infer category from domain
        category = None
        domain_lower = domain.lower() if domain else ''
        if any(kw in domain_lower for kw in ['ai', 'ml', 'machine-learning', 'artificial-intelligence']):
            category = 'llm_provider'
        elif any(kw in domain_lower for kw in ['search', 'engine', 'seo']):
            category = 'search_engine'
        elif any(kw in domain_lower for kw in ['tool', 'platform', 'saas', 'software']):
            category = 'toolkit'
        
        return {
            'name': name,
            'description': None,
            'logo_url': None,
            'category': category
        }

