"""
GPT Service for generating AI descriptions and industry signals
"""

from typing import List, Optional, Dict, Any
from loguru import logger

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None
    logger.warning("OpenAI library not installed. GPT features will use fallback mode.")

from app.core.config import settings


class GPTService:
    """Service for generating AI descriptions using OpenAI GPT"""
    
    def __init__(self):
        """Initialize GPT service with OpenAI client if API key is available"""
        self.model = settings.OPENAI_MODEL
        self.client = None
        
        if AsyncOpenAI and settings.OPENAI_API_KEY:
            try:
                self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
                logger.info(f"GPT Service initialized with model: {self.model}")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI client: {e}. Using fallback mode.")
                self.client = None
        else:
            if not AsyncOpenAI:
                logger.warning("OpenAI library not installed. Using fallback mode.")
            if not settings.OPENAI_API_KEY:
                logger.warning("OPENAI_API_KEY not configured. Using fallback mode.")
    
    async def generate_company_description(self, company_data: Dict[str, Any]) -> str:
        """
        Generate AI description for a company (2-3 sentences)
        
        Args:
            company_data: Dict with company information (name, website, category, meta_description, etc.)
            
        Returns:
            Generated description string
        """
        if self.client:
            try:
                company_name = company_data.get("name", "Company")
                website = company_data.get("website", "")
                category = company_data.get("category", "")
                meta_description = company_data.get("meta_description", "")
                
                # Build prompt
                prompt_parts = [f"Create a brief company description (2-3 sentences) based on the following data:"]
                prompt_parts.append(f"Name: {company_name}")
                if website:
                    prompt_parts.append(f"Website: {website}")
                if category:
                    prompt_parts.append(f"Category: {category}")
                if meta_description:
                    prompt_parts.append(f"Description: {meta_description}")
                
                prompt = "\n".join(prompt_parts)
                
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an assistant that creates brief and informative company descriptions in English. Always respond in English."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.7,
                    max_tokens=150
                )
                
                if response.choices and len(response.choices) > 0:
                    content = response.choices[0].message.content
                    if content and len(content.strip()) > 20:  # Minimum length check
                        return content.strip()
                
                # If response is too short, use fallback
                logger.warning("GPT response too short, using fallback")
                
            except Exception as e:
                logger.error(f"Failed to generate company description with GPT: {e}")
                # Fall through to fallback
        
        # Fallback: use meta_description or generate heuristic description
        return self._generate_company_description_fallback(company_data)
    
    async def generate_competitor_description(
        self, 
        competitor_data: Dict[str, Any], 
        parent_company: str
    ) -> str:
        """
        Generate AI description for a competitor company
        
        Args:
            competitor_data: Dict with competitor information (name, website, category, description, etc.)
            parent_company: Name of the parent company
            
        Returns:
            Generated description string
        """
        if self.client:
            try:
                competitor_name = competitor_data.get("name", "Competitor")
                website = competitor_data.get("website", "")
                category = competitor_data.get("category", "")
                description = competitor_data.get("description", "")
                
                # Build prompt
                prompt_parts = [
                    f"Describe {competitor_name} as a competitor for {parent_company}."
                ]
                prompt_parts.append("Briefly (1-2 sentences).")
                
                if website:
                    prompt_parts.append(f"Website: {website}")
                if category:
                    prompt_parts.append(f"Category: {category}")
                if description:
                    prompt_parts.append(f"Description: {description}")
                
                prompt = "\n".join(prompt_parts)
                
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an assistant that creates brief competitor company descriptions in English. Always respond in English."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.7,
                    max_tokens=100
                )
                
                if response.choices and len(response.choices) > 0:
                    content = response.choices[0].message.content
                    if content and len(content.strip()) > 10:
                        return content.strip()
                
                logger.warning("GPT response too short, using fallback")
                
            except Exception as e:
                logger.error(f"Failed to generate competitor description with GPT: {e}")
                # Fall through to fallback
        
        # Fallback: generate heuristic description
        return self._generate_competitor_description_fallback(competitor_data, parent_company)
    
    async def suggest_industry_signals(self, company_data: Dict[str, Any]) -> List[str]:
        """
        Suggest industry signals/characteristics for a company
        
        Args:
            company_data: Dict with company information (name, website, category, etc.)
            
        Returns:
            List of industry signals (3-5 keywords)
        """
        if self.client:
            try:
                company_name = company_data.get("name", "Company")
                website = company_data.get("website", "")
                category = company_data.get("category", "")
                
                # Build prompt
                prompt_parts = [
                    f"Identify the main characteristics of the company: {company_name}"
                ]
                if website:
                    prompt_parts.append(f"Website: {website}")
                if category:
                    prompt_parts.append(f"Category: {category}")
                
                prompt_parts.append("Return a list of 3-5 keywords, each on a new line, in English.")
                prompt = "\n".join(prompt_parts)
                
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an assistant that identifies key company characteristics. Return only a list of keywords in English, each on a new line, without additional comments."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.5,
                    max_tokens=100
                )
                
                if response.choices and len(response.choices) > 0:
                    content = response.choices[0].message.content
                    if content:
                        # Parse signals from response (newline-separated, filter out comments)
                        signals = [
                            line.strip()
                            for line in content.split("\n")
                            if line.strip() and not line.strip().startswith("#")
                        ]
                        # Limit to 5 signals
                        signals = signals[:5]
                        if len(signals) > 0:
                            return signals
                
                logger.warning("GPT response invalid, using fallback")
                
            except Exception as e:
                logger.error(f"Failed to suggest industry signals with GPT: {e}")
                # Fall through to fallback
        
        # Fallback: use heuristic detection
        return self._suggest_industry_signals_fallback(company_data)
    
    def _generate_company_description_fallback(self, company_data: Dict[str, Any]) -> str:
        """Generate fallback description using meta_description or company name"""
        meta_description = company_data.get("meta_description", "")
        company_name = company_data.get("name", "Компания")
        category = company_data.get("category", "")
        website = company_data.get("website", "")
        
        if meta_description and len(meta_description) > 20:
            return meta_description
        
        # Generate simple description
        parts = [company_name]
        if category:
            parts.append(f" — компания в категории {category}")
        if website:
            parts.append(f" ({website})")
        
        return "".join(parts) + "."
    
    def _generate_competitor_description_fallback(
        self, 
        competitor_data: Dict[str, Any], 
        parent_company: str
    ) -> str:
        """Generate fallback competitor description"""
        competitor_name = competitor_data.get("name", "Конкурент")
        description = competitor_data.get("description", "")
        category = competitor_data.get("category", "")
        
        if description:
            return f"{competitor_name} — {description}"
        
        parts = [competitor_name]
        if category:
            parts.append(f" — компания в категории {category}")
        parts.append(f", конкурент для {parent_company}")
        
        return "".join(parts) + "."
    
    def _suggest_industry_signals_fallback(self, company_data: Dict[str, Any]) -> List[str]:
        """Generate fallback industry signals using heuristics"""
        signals = []
        company_name = (company_data.get("name", "") or "").lower()
        category = (company_data.get("category", "") or "").lower()
        website = (company_data.get("website", "") or "").lower()
        
        # Add category if available
        if category:
            signals.append(category)
        
        # Heuristic detection based on name/website keywords
        name_website = f"{company_name} {website}"
        
        if any(keyword in name_website for keyword in ["saas", "software", "platform", "api", "cloud"]):
            if "saas" not in signals:
                signals.append("SaaS")
        
        if any(keyword in name_website for keyword in ["ecommerce", "shop", "store", "marketplace", "retail"]):
            if "ecommerce" not in signals:
                signals.append("ecommerce")
        
        if any(keyword in name_website for keyword in ["ai", "ml", "machine learning", "artificial intelligence"]):
            if "AI" not in signals:
                signals.append("AI")
        
        if any(keyword in name_website for keyword in ["fintech", "payment", "banking", "finance"]):
            if "fintech" not in signals:
                signals.append("fintech")
        
        if any(keyword in name_website for keyword in ["b2b", "enterprise", "business"]):
            if "B2B" not in signals:
                signals.append("B2B")
        
        if any(keyword in name_website for keyword in ["b2c", "consumer", "retail"]):
            if "B2C" not in signals:
                signals.append("B2C")
        
        # Limit to 5 signals
        return signals[:5] if signals else [category] if category else ["Technology"]
    
    async def suggest_competitors_list(
        self, 
        company_data: Dict[str, Any], 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Generate list of competitor companies using GPT
        
        Args:
            company_data: Dict with company information (name, website, description, industry_signals, etc.)
            limit: Maximum number of competitors to suggest
            
        Returns:
            List of competitor dictionaries with name, website, description, reason
        """
        if self.client:
            try:
                company_name = company_data.get("name", "Company")
                website = company_data.get("website", "")
                description = company_data.get("description", "") or company_data.get("ai_description", "")
                category = company_data.get("category", "")
                industry_signals = company_data.get("industry_signals", [])
                
                # Build prompt
                prompt_parts = [
                    f"Suggest a list of {limit} competitor companies for: {company_name}"
                ]
                
                if description:
                    prompt_parts.append(f"Company description: {description}")
                if website:
                    prompt_parts.append(f"Website: {website}")
                if category:
                    prompt_parts.append(f"Category: {category}")
                if industry_signals:
                    signals_str = ", ".join(industry_signals)
                    prompt_parts.append(f"Characteristics: {signals_str}")
                
                prompt_parts.append("\nReturn a list in JSON array format, each element should contain:")
                prompt_parts.append("- name: company name")
                prompt_parts.append("- website: company website (if known)")
                prompt_parts.append("- description: brief description in English (1 sentence)")
                prompt_parts.append("- reason: why this is a competitor (in English)")
                prompt_parts.append("\nExample format:")
                prompt_parts.append('[{"name": "Company 1", "website": "https://example.com", "description": "Description in English", "reason": "Reason in English"}]')
                
                prompt = "\n".join(prompt_parts)
                
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an assistant that suggests competitor companies. Return only a valid JSON array, without additional comments or formatting. All text must be in English. Format: [{\"name\": \"...\", \"website\": \"...\", \"description\": \"...\", \"reason\": \"...\"}]"
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.7,
                    max_tokens=2000
                )
                
                if response.choices and len(response.choices) > 0:
                    content = response.choices[0].message.content
                    if content:
                        import json
                        import re
                        try:
                            # Try to extract JSON array from response (might have markdown code blocks)
                            content_clean = content.strip()
                            # Remove markdown code blocks if present
                            if content_clean.startswith("```"):
                                content_clean = re.sub(r'^```(?:json)?\s*\n', '', content_clean)
                                content_clean = re.sub(r'\n```\s*$', '', content_clean)
                            
                            parsed = json.loads(content_clean)
                            
                            # Handle both {"competitors": [...]} and [...] formats
                            if isinstance(parsed, dict) and "competitors" in parsed:
                                competitors_list = parsed["competitors"]
                            elif isinstance(parsed, list):
                                competitors_list = parsed
                            else:
                                competitors_list = []
                            
                            # Validate and clean competitors
                            result = []
                            for comp in competitors_list[:limit]:
                                if isinstance(comp, dict) and comp.get("name"):
                                    result.append({
                                        "name": comp.get("name", "").strip(),
                                        "website": comp.get("website", "").strip(),
                                        "description": comp.get("description", "").strip(),
                                        "reason": comp.get("reason", "Конкурент").strip()
                                    })
                            
                            if len(result) > 0:
                                logger.info(f"GPT generated {len(result)} competitors for {company_name}")
                                return result
                        except json.JSONDecodeError as e:
                            logger.error(
                                f"Failed to parse GPT response as JSON for {company_name}: {e}. "
                                f"Response content (first 1000 chars): {content[:1000]}"
                            )
                            logger.debug(f"Full response content: {content}")
                        except ValueError as e:
                            logger.error(
                                f"Value error while parsing GPT response for {company_name}: {e}. "
                                f"Response content (first 1000 chars): {content[:1000]}"
                            )
                        except Exception as e:
                            logger.error(
                                f"Unexpected error while parsing GPT response for {company_name}: {e}. "
                                f"Response content (first 1000 chars): {content[:1000]}",
                                exc_info=True
                            )
                
                logger.warning(f"GPT response invalid for {company_name}, using fallback")
                
            except Exception as e:
                logger.error(f"Failed to suggest competitors with GPT: {e}", exc_info=True)
                # Fall through to fallback
        
        # Fallback: generate heuristic competitors
        return self._suggest_competitors_fallback(company_data, limit)
    
    def _suggest_competitors_fallback(
        self, 
        company_data: Dict[str, Any], 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Generate fallback competitor suggestions using heuristics"""
        company_name = company_data.get("name", "Company")
        category = company_data.get("category", "")
        industry_signals = company_data.get("industry_signals", [])
        
        # This is a fallback - in real scenario, we should use GPT
        # For now, return empty list to indicate that GPT is needed
        logger.warning(f"Fallback competitor suggestion called for {company_name} - GPT should be used")
        return []