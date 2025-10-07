"""
Seed database with AI companies
"""

import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.core.database import AsyncSessionLocal
from app.models.company import Company


AI_COMPANIES = [
    {
        "name": "OpenAI",
        "website": "https://openai.com",
        "description": "AI research and deployment company. Creators of ChatGPT, GPT-4, DALL-E, and more.",
        "logo_url": "https://openai.com/favicon.ico",
        "category": "llm_provider",
        "twitter_handle": "OpenAI",
        "github_org": "openai"
    },
    {
        "name": "Anthropic",
        "website": "https://anthropic.com",
        "description": "AI safety company. Creators of Claude, a helpful, harmless, and honest AI assistant.",
        "logo_url": "https://anthropic.com/favicon.ico",
        "category": "llm_provider",
        "twitter_handle": "AnthropicAI",
        "github_org": "anthropics"
    },
    {
        "name": "Google DeepMind",
        "website": "https://deepmind.google",
        "description": "Google's AI research lab. Creators of Gemini, AlphaGo, AlphaFold, and more.",
        "logo_url": "https://deepmind.google/favicon.ico",
        "category": "llm_provider",
        "twitter_handle": "GoogleDeepMind",
        "github_org": "google-deepmind"
    },
    {
        "name": "Meta AI",
        "website": "https://ai.meta.com",
        "description": "Meta's AI research division. Creators of Llama, SAM, and other open-source AI models.",
        "logo_url": "https://ai.meta.com/favicon.ico",
        "category": "llm_provider",
        "twitter_handle": "MetaAI",
        "github_org": "meta-llama"
    },
    {
        "name": "Mistral AI",
        "website": "https://mistral.ai",
        "description": "European AI company. Creators of Mistral models - efficient and powerful open-source LLMs.",
        "logo_url": "https://mistral.ai/favicon.ico",
        "category": "llm_provider",
        "twitter_handle": "MistralAI",
        "github_org": "mistralai"
    },
    {
        "name": "Cohere",
        "website": "https://cohere.com",
        "description": "Enterprise AI platform. Building LLMs for business applications.",
        "logo_url": "https://cohere.com/favicon.ico",
        "category": "llm_provider",
        "twitter_handle": "CohereAI",
        "github_org": "cohere-ai"
    },
    {
        "name": "Hugging Face",
        "website": "https://huggingface.co",
        "description": "The AI community platform. Hosting models, datasets, and applications.",
        "logo_url": "https://huggingface.co/favicon.ico",
        "category": "platform",
        "twitter_handle": "huggingface",
        "github_org": "huggingface"
    },
    {
        "name": "Stability AI",
        "website": "https://stability.ai",
        "description": "Open-source AI company. Creators of Stable Diffusion and Stable LM.",
        "logo_url": "https://stability.ai/favicon.ico",
        "category": "generative_ai",
        "twitter_handle": "StabilityAI",
        "github_org": "Stability-AI"
    },
    {
        "name": "Perplexity AI",
        "website": "https://perplexity.ai",
        "description": "AI-powered answer engine. Conversational search with citations.",
        "logo_url": "https://perplexity.ai/favicon.ico",
        "category": "search_engine",
        "twitter_handle": "perplexity_ai",
        "github_org": "perplexityai"
    },
    {
        "name": "Character.AI",
        "website": "https://character.ai",
        "description": "Conversational AI platform. Create and chat with AI characters.",
        "logo_url": "https://character.ai/favicon.ico",
        "category": "platform",
        "twitter_handle": "character_ai",
        "github_org": "characterai"
    },
    {
        "name": "Runway",
        "website": "https://runwayml.com",
        "description": "AI-powered creative tools. Video generation and editing with AI.",
        "logo_url": "https://runwayml.com/favicon.ico",
        "category": "generative_ai",
        "twitter_handle": "runwayml",
        "github_org": "runwayml"
    },
    {
        "name": "Midjourney",
        "website": "https://midjourney.com",
        "description": "AI art generation platform. Creating images from text descriptions.",
        "logo_url": "https://midjourney.com/favicon.ico",
        "category": "generative_ai",
        "twitter_handle": "midjourney",
        "github_org": None
    },
    {
        "name": "Scale AI",
        "website": "https://scale.com",
        "description": "Data platform for AI. Training data, evaluation, and fine-tuning.",
        "logo_url": "https://scale.com/favicon.ico",
        "category": "platform",
        "twitter_handle": "Scale_AI",
        "github_org": "scaleapi"
    },
    {
        "name": "Replicate",
        "website": "https://replicate.com",
        "description": "Run AI models in the cloud. API for open-source AI models.",
        "logo_url": "https://replicate.com/favicon.ico",
        "category": "platform",
        "twitter_handle": "replicate",
        "github_org": "replicate"
    },
    {
        "name": "Anyscale",
        "website": "https://anyscale.com",
        "description": "Ray platform for AI applications. Scale AI workloads efficiently.",
        "logo_url": "https://anyscale.com/favicon.ico",
        "category": "infrastructure",
        "twitter_handle": "anyscalecompute",
        "github_org": "anyscale"
    },
    {
        "name": "LangChain",
        "website": "https://langchain.com",
        "description": "Framework for building LLM applications. Tools and chains for AI apps.",
        "logo_url": "https://langchain.com/favicon.ico",
        "category": "framework",
        "twitter_handle": "LangChainAI",
        "github_org": "langchain-ai"
    },
    {
        "name": "Weights & Biases",
        "website": "https://wandb.ai",
        "description": "MLOps platform. Experiment tracking, model versioning, and collaboration.",
        "logo_url": "https://wandb.ai/favicon.ico",
        "category": "mlops",
        "twitter_handle": "weights_biases",
        "github_org": "wandb"
    },
    {
        "name": "Databricks",
        "website": "https://databricks.com",
        "description": "Unified analytics platform. AI and machine learning at scale.",
        "logo_url": "https://databricks.com/favicon.ico",
        "category": "platform",
        "twitter_handle": "databricks",
        "github_org": "databricks"
    },
    {
        "name": "Together AI",
        "website": "https://together.ai",
        "description": "Decentralized cloud for AI. Run open-source models at scale.",
        "logo_url": "https://together.ai/favicon.ico",
        "category": "infrastructure",
        "twitter_handle": "togethercompute",
        "github_org": "togethercomputer"
    },
    {
        "name": "Inflection AI",
        "website": "https://inflection.ai",
        "description": "Personal AI company. Creators of Pi, your personal AI assistant.",
        "logo_url": "https://inflection.ai/favicon.ico",
        "category": "llm_provider",
        "twitter_handle": "inflectionai",
        "github_org": None
    }
]


async def seed_companies():
    """Seed database with AI companies"""
    logger.info("Starting companies seeding...")
    
    async with AsyncSessionLocal() as db:
        try:
            # Check existing companies
            from sqlalchemy import select
            result = await db.execute(select(Company))
            existing = result.scalars().all()
            existing_names = {c.name for c in existing}
            
            logger.info(f"Found {len(existing)} existing companies")
            
            # Add new companies
            added_count = 0
            for company_data in AI_COMPANIES:
                if company_data["name"] not in existing_names:
                    company = Company(**company_data)
                    db.add(company)
                    added_count += 1
                    logger.info(f"Added company: {company_data['name']}")
            
            await db.commit()
            logger.info(f"Successfully seeded {added_count} new companies")
            logger.info(f"Total companies in database: {len(existing) + added_count}")
            
            return {"status": "success", "added": added_count, "total": len(existing) + added_count}
            
        except Exception as e:
            logger.error(f"Failed to seed companies: {e}")
            await db.rollback()
            raise


def run_seed():
    """Run seed in sync context"""
    return asyncio.run(seed_companies())


if __name__ == "__main__":
    result = run_seed()
    print(f"Seed completed: {result}")

