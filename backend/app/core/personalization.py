"""
Service for handling personalization logic.
Centralizes all personalization-related operations.

КРИТИЧЕСКИ ВАЖНО: Персонализация основана на user_id компаний, 
а НЕ на subscribed_companies!
"""

from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.core.access_control import get_user_company_ids


class PersonalizationService:
    """Centralized service for personalization logic."""
    
    def __init__(self, db: AsyncSession):
        """
        Initialize PersonalizationService.
        
        Args:
            db: Database session
        """
        self._db = db
    
    async def get_filter_company_ids(
        self,
        user: Optional[User],
        provided_ids: Optional[List[UUID]] = None
    ) -> Optional[List[UUID]]:
        """
        Get company IDs for filtering.
        
        Logic:
        1. If provided_ids is given, return intersection with user's companies (security)
        2. If user is authenticated, get their companies
        3. If user has no companies, return empty list
        4. If user is anonymous, return None (no filtering)
        
        Args:
            user: Current user (None for anonymous)
            provided_ids: Explicitly provided company IDs (from query params)
            
        Returns:
            List[UUID] - company IDs to filter by (intersection of user companies and provided_ids)
            [] - user has no companies or no intersection (return empty results)
            None - no filtering needed (anonymous user)
        """
        # If user is anonymous, no filtering
        if not user:
            return None
        
        # Get user's companies first
        try:
            user_company_ids = await get_user_company_ids(user, self._db)
            # Валидация: проверяем что все ID валидные UUID
            valid_user_ids = []
            for cid in user_company_ids:
                if isinstance(cid, UUID):
                    valid_user_ids.append(cid)
                else:
                    try:
                        valid_user_ids.append(UUID(str(cid)))
                    except (ValueError, TypeError):
                        continue
            
            if not valid_user_ids:
                # КРИТИЧЕСКИ ВАЖНО: если у пользователя нет компаний, 
                # возвращаем пустой список для возврата пустого результата
                return []
            
            # If user explicitly provided company IDs, return intersection (security)
            if provided_ids is not None:
                # Валидация: проверяем что все ID валидные UUID
                valid_provided_ids = []
                for cid in provided_ids:
                    if isinstance(cid, UUID):
                        valid_provided_ids.append(cid)
                    else:
                        # Попытка конвертировать в UUID
                        try:
                            valid_provided_ids.append(UUID(str(cid)))
                        except (ValueError, TypeError):
                            # Пропускаем невалидные UUID
                            continue
                
                # БЕЗОПАСНОСТЬ: возвращаем пересечение (только свои компании из списка)
                intersection = [cid for cid in valid_provided_ids if cid in valid_user_ids]
                return intersection if intersection else []
            
            # No provided_ids - return all user's companies
            return valid_user_ids
            
        except Exception:
            # On error, return empty list to prevent showing all news
            return []
    
    def should_return_empty(self, company_ids: Optional[List[UUID]]) -> bool:
        """
        Check if should return empty result (user has no companies).
        
        Args:
            company_ids: Company IDs from get_filter_company_ids
            
        Returns:
            True if should return empty result, False otherwise
        """
        return company_ids == []
    
    async def parse_company_ids_from_query(
        self,
        company_ids: Optional[str] = None,
        company_id: Optional[str] = None
    ) -> tuple[Optional[List[UUID]], Optional[UUID]]:
        """
        Parse company IDs from query parameters.
        
        Args:
            company_ids: Comma-separated company IDs string
            company_id: Single company ID string
            
        Returns:
            Tuple of (list of UUIDs, single UUID or None)
        """
        parsed_company_ids = None
        normalised_company_id = None
        
        # Parse company_ids parameter
        if company_ids:
            parsed_company_ids = [cid.strip() for cid in company_ids.split(',') if cid.strip()]
        elif company_id:
            parsed_company_ids = [company_id]
        
        # Normalize to UUIDs
        if parsed_company_ids:
            normalised_ids = []
            for cid in parsed_company_ids:
                try:
                    normalised_ids.append(UUID(cid))
                except (ValueError, TypeError):
                    # Invalid UUID, skip it
                    continue
            
            parsed_company_ids = normalised_ids if normalised_ids else None
            
            # If single ID, also set normalised_company_id
            if len(parsed_company_ids) == 1:
                normalised_company_id = parsed_company_ids[0]
        elif company_id:
            try:
                normalised_company_id = UUID(company_id)
            except (ValueError, TypeError):
                normalised_company_id = None
        
        return parsed_company_ids, normalised_company_id
