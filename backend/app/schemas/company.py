"""
Company Pydantic schemas for API
"""

from typing import Optional
from pydantic import BaseModel, HttpUrl, Field
from uuid import UUID


class CompanyBase(BaseModel):
    """Base company schema"""
    name: str = Field(..., description="Company name")
    website: Optional[str] = Field(None, description="Company website URL")
    description: Optional[str] = Field(None, description="Company description")
    logo_url: Optional[str] = Field(None, description="Company logo URL")
    category: Optional[str] = Field(None, description="Company category")
    twitter_handle: Optional[str] = Field(None, description="Twitter/X handle")
    github_org: Optional[str] = Field(None, description="GitHub organization")
    
    # Social media URLs
    facebook_url: Optional[str] = Field(None, description="Facebook page URL")
    instagram_url: Optional[str] = Field(None, description="Instagram profile URL")
    linkedin_url: Optional[str] = Field(None, description="LinkedIn company page URL")
    youtube_url: Optional[str] = Field(None, description="YouTube channel URL")
    tiktok_url: Optional[str] = Field(None, description="TikTok profile URL")


class CompanyCreate(CompanyBase):
    """Schema for creating a new company"""
    pass


class CompanyUpdate(BaseModel):
    """Schema for updating company information"""
    name: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None
    logo_url: Optional[str] = None
    category: Optional[str] = None
    twitter_handle: Optional[str] = None
    github_org: Optional[str] = None
    facebook_url: Optional[str] = None
    instagram_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    youtube_url: Optional[str] = None
    tiktok_url: Optional[str] = None


class CompanyResponse(CompanyBase):
    """Schema for company API response"""
    id: UUID
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


class CompanySocialMediaHandles(BaseModel):
    """Schema for extracted social media handles"""
    twitter: Optional[str] = None
    facebook: Optional[str] = None
    instagram: Optional[str] = None
    linkedin: Optional[str] = None
    youtube: Optional[str] = None
    tiktok: Optional[str] = None








