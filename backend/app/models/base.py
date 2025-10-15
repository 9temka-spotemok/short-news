"""
Base database model with enhanced functionality
"""

from datetime import datetime
from typing import Any, Dict, Optional, Type, TypeVar
from uuid import UUID as PyUUID, uuid4
from sqlalchemy import Column, DateTime, func, event
from sqlalchemy.orm import declarative_base, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declared_attr
from pydantic import BaseModel as PydanticBaseModel, Field
import json

# Type variable for model subclasses
ModelType = TypeVar('ModelType', bound='BaseModel')

Base = declarative_base()


class TimestampMixin:
    """Mixin for automatic timestamp management"""
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        nullable=False,
        index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now(), 
        nullable=False,
        index=True
    )


class BaseModel(Base, TimestampMixin):
    """Enhanced base model with common fields and utilities"""
    __abstract__ = True
    
    id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid4,
        index=True
    )
    
    @declared_attr
    def __tablename__(cls) -> str:
        """Auto-generate table name from class name"""
        return cls.__name__.lower() + 's'
    
    def to_dict(self, exclude: Optional[set] = None) -> Dict[str, Any]:
        """
        Convert model to dictionary with optional field exclusion
        
        Args:
            exclude: Set of field names to exclude from output
            
        Returns:
            Dictionary representation of the model
        """
        exclude = exclude or set()
        result = {}
        
        for column in self.__table__.columns:
            if column.name not in exclude:
                value = getattr(self, column.name)
                # Handle datetime serialization
                if isinstance(value, datetime):
                    value = value.isoformat()
                # Handle UUID serialization
                elif isinstance(value, PyUUID):
                    value = str(value)
                result[column.name] = value
        
        return result
    
    def to_json(self, exclude: Optional[set] = None) -> str:
        """
        Convert model to JSON string
        
        Args:
            exclude: Set of field names to exclude from output
            
        Returns:
            JSON string representation of the model
        """
        return json.dumps(self.to_dict(exclude), default=str)
    
    @classmethod
    def from_dict(cls: Type[ModelType], data: Dict[str, Any]) -> ModelType:
        """
        Create model instance from dictionary
        
        Args:
            data: Dictionary with model data
            
        Returns:
            Model instance
        """
        # Filter out fields that don't exist on the model
        valid_fields = {c.name for c in cls.__table__.columns}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        
        return cls(**filtered_data)
    
    def update_from_dict(self, data: Dict[str, Any]) -> None:
        """
        Update model instance from dictionary
        
        Args:
            data: Dictionary with update data
        """
        valid_fields = {c.name for c in self.__table__.columns}
        for key, value in data.items():
            if key in valid_fields and hasattr(self, key):
                setattr(self, key, value)
    
    def __repr__(self) -> str:
        """String representation of the model"""
        return f"<{self.__class__.__name__}(id={self.id})>"
    
    def __str__(self) -> str:
        """Human-readable string representation"""
        return f"{self.__class__.__name__} {self.id}"


# Pydantic base model for API schemas
class BaseSchema(PydanticBaseModel):
    """Base Pydantic schema with common configuration"""
    
    model_config = {
        "from_attributes": True,
        "validate_assignment": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {
            datetime: lambda v: v.isoformat(),
            PyUUID: lambda v: str(v),
        }
    }


class TimestampSchema(BaseSchema):
    """Schema with timestamp fields"""
    
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class IDSchema(BaseSchema):
    """Schema with ID field"""
    
    id: PyUUID = Field(..., description="Unique identifier")


class BaseResponseSchema(IDSchema, TimestampSchema):
    """Base response schema with ID and timestamps"""
    pass
