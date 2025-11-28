"""
SQLAlchemy repository for report persistence operations.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from uuid import UUID

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from loguru import logger

from app.models.report import Report, ReportStatus


@dataclass
class ReportRepository:
    """Repository for report data access operations."""

    session: AsyncSession

    async def create(self, report_data: dict) -> Report:
        """
        Create a new report.
        
        Args:
            report_data: Dictionary with report fields (user_id, query, status, etc.)
            
        Returns:
            Created Report instance
        """
        # Нормализовать status - убеждаемся что это правильный enum с правильным значением в нижнем регистре
        if "status" in report_data:
            status_value = report_data["status"]
            logger.debug(f"Processing status: {status_value}, type: {type(status_value)}")
            
            # Конвертируем в правильный enum
            if isinstance(status_value, ReportStatus):
                # Уже enum - убеждаемся что значение в нижнем регистре
                normalized_value = status_value.value.lower()
                report_data["status"] = ReportStatus(normalized_value)
                logger.debug(f"Normalized enum status to: {report_data['status']} (value: '{report_data['status'].value}')")
            elif isinstance(status_value, str):
                # Строка - конвертируем в enum в нижнем регистре
                try:
                    normalized_value = status_value.lower()
                    report_data["status"] = ReportStatus(normalized_value)
                    logger.debug(f"Converted string '{status_value}' to enum {report_data['status']} (value: '{report_data['status'].value}')")
                except (ValueError, AttributeError) as e:
                    logger.warning(f"Invalid status value '{status_value}', using PROCESSING: {e}")
                    report_data["status"] = ReportStatus.PROCESSING
            else:
                logger.warning(f"Unexpected status type {type(status_value)}, using PROCESSING")
                report_data["status"] = ReportStatus.PROCESSING
        else:
            # Если status не указан, используем PROCESSING по умолчанию
            report_data["status"] = ReportStatus.PROCESSING
        
        logger.debug(f"Final report_data status: {report_data.get('status')} (value: '{report_data.get('status').value if isinstance(report_data.get('status'), ReportStatus) else 'N/A'}')")
        
        # Создаем объект Report
        report = Report(**report_data)
        
        # Финальная проверка status перед сохранением в БД
        if hasattr(report, 'status') and isinstance(report.status, ReportStatus):
            # Убеждаемся что значение в нижнем регистре (как в БД)
            current_value = report.status.value
            if current_value != current_value.lower():
                logger.warning(f"Report status value is not lowercase: '{current_value}', fixing")
                report.status = ReportStatus(current_value.lower())
            # Проверяем что значение валидное
            if report.status.value not in ['processing', 'ready', 'error']:
                logger.error(f"Invalid status value: '{report.status.value}', using PROCESSING")
                report.status = ReportStatus.PROCESSING
            logger.debug(f"Report status before flush: {report.status} (value: '{report.status.value}')")
        else:
            logger.error(f"Report status is not ReportStatus enum: {type(getattr(report, 'status', None))}")
            report.status = ReportStatus.PROCESSING
        
        # КРИТИЧЕСКАЯ ПРОВЕРКА: перед добавлением в сессию убеждаемся что status это правильный enum
        # SQLAlchemy может конвертировать enum в строку, поэтому проверяем еще раз
        if hasattr(report, 'status'):
            final_status_value = report.status.value if isinstance(report.status, ReportStatus) else str(report.status)
            if final_status_value != final_status_value.lower():
                logger.error(f"CRITICAL: Status value is not lowercase before DB insert: '{final_status_value}'")
                report.status = ReportStatus(final_status_value.lower())
            elif final_status_value not in ['processing', 'ready', 'error']:
                logger.error(f"CRITICAL: Invalid status value before DB insert: '{final_status_value}'")
                report.status = ReportStatus.PROCESSING
        
        self.session.add(report)
        await self.session.flush()
        await self.session.refresh(report)
        logger.info(f"Created report {report.id} for user {report.user_id} with status {report.status.value}")
        return report

    async def get_by_id(
        self,
        report_id: UUID | str,
        *,
        user_id: Optional[UUID] = None,  # НОВЫЙ ПАРАМЕТР для фильтрации по user_id
        include_relations: bool = False
    ) -> Optional[Report]:
        """
        Get report by ID.
        
        Args:
            report_id: Report UUID or string
            user_id: Optional user ID to filter by (for access control)
            include_relations: Whether to load related entities (user, company)
            
        Returns:
            Report instance or None
        """
        stmt = select(Report)
        
        if include_relations:
            stmt = stmt.options(
                selectinload(Report.user),
                selectinload(Report.company)
            )
        
        target_id = report_id
        if isinstance(report_id, str):
            try:
                target_id = UUID(report_id)
            except ValueError:
                logger.error(f"Invalid report ID format: {report_id}")
                return None
        
        stmt = stmt.where(Report.id == target_id)
        
        # НОВЫЙ ФИЛЬТР ПО user_id (для безопасности и изоляции данных)
        if user_id:
            stmt = stmt.where(Report.user_id == user_id)
        
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_user(
        self,
        user_id: UUID | str,
        limit: int = 20,
        offset: int = 0
    ) -> List[Report]:
        """
        Get reports for a user with pagination.
        
        Args:
            user_id: User UUID or string
            limit: Maximum number of reports to return
            offset: Number of reports to skip
            
        Returns:
            List of Report instances
        """
        target_id = user_id
        if isinstance(user_id, str):
            try:
                target_id = UUID(user_id)
            except ValueError:
                logger.error(f"Invalid user ID format: {user_id}")
                return []
        
        stmt = (
            select(Report)
            .where(Report.user_id == target_id)
            .order_by(desc(Report.created_at))
            .limit(limit)
            .offset(offset)
        )
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_status(
        self,
        report_id: UUID | str,
        status: ReportStatus | str,
        error_message: Optional[str] = None,
        completed_at: Optional[datetime] = None
    ) -> Optional[Report]:
        """
        Update report status.
        
        Args:
            report_id: Report UUID or string
            status: New status (ReportStatus enum or string)
            error_message: Error message if status is error
            completed_at: Completion timestamp
            
        Returns:
            Updated Report instance or None
        """
        report = await self.get_by_id(report_id)
        if not report:
            logger.warning(f"Report {report_id} not found for status update")
            return None
        
        # Convert string to enum if needed
        if isinstance(status, str):
            try:
                status = ReportStatus(status)
            except ValueError:
                logger.error(f"Invalid status value: {status}")
                return None
        
        report.status = status
        if error_message is not None:
            report.error_message = error_message
        if completed_at is not None:
            report.completed_at = completed_at
        
        await self.session.flush()
        await self.session.refresh(report)
        logger.info(f"Updated report {report_id} status to {status}")
        return report

    async def update_report_data(
        self,
        report_id: UUID | str,
        report_data: Dict[str, Any],
        company_id: Optional[UUID] = None,
        status: Optional[ReportStatus | str] = None,
        completed_at: Optional[datetime] = None
    ) -> Optional[Report]:
        """
        Update report data and related fields.
        
        Args:
            report_id: Report UUID or string
            report_data: Full report data dictionary (company, news, categories, sources, pricing, competitors)
            company_id: Associated company ID (optional)
            status: New status (optional, defaults to READY if not provided)
            completed_at: Completion timestamp (optional)
            
        Returns:
            Updated Report instance or None
        """
        try:
            report = await self.get_by_id(report_id)
            if not report:
                logger.warning(f"Report {report_id} not found for data update")
                return None
        except Exception as e:
            logger.error(f"Error getting report {report_id}: {e}", exc_info=True)
            return None
        
        # Update report data - убеждаемся что данные сериализуемы
        try:
            import json
            # Проверяем сериализуемость
            json.dumps(report_data, default=str)
            report.report_data = report_data
        except (TypeError, ValueError) as e:
            logger.error(f"Report data is not JSON serializable: {e}", exc_info=True)
            # Пытаемся очистить от не-сериализуемых объектов
            def clean_for_json(obj):
                if isinstance(obj, dict):
                    return {k: clean_for_json(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [clean_for_json(item) for item in obj]
                elif isinstance(obj, (datetime,)):
                    return obj.isoformat() if hasattr(obj, 'isoformat') else str(obj)
                elif hasattr(obj, '__dict__') and not isinstance(obj, (str, int, float, bool, type(None))):
                    return str(obj)
                else:
                    return obj
            report.report_data = clean_for_json(report_data)
            logger.info("Cleaned report_data for JSON serialization")
        
        # Update company_id if provided
        if company_id is not None:
            report.company_id = company_id
        
        # Update status if provided, otherwise set to READY
        if status is not None:
            if isinstance(status, str):
                try:
                    status = ReportStatus(status)
                except ValueError:
                    logger.error(f"Invalid status value: {status}")
                    return None
            report.status = status
        else:
            # If no status provided, set to READY when data is saved
            report.status = ReportStatus.READY
        
        # Update completed_at if provided or set to now
        if completed_at is not None:
            report.completed_at = completed_at
        elif report.completed_at is None:
            report.completed_at = datetime.now(timezone.utc)
        
        try:
            await self.session.flush()
            await self.session.refresh(report)
            logger.info(f"Updated report {report_id} data and status to {report.status.value}")
            return report
        except Exception as e:
            logger.error(f"Error flushing/refreshing report {report_id}: {e}", exc_info=True)
            # Не делаем rollback здесь, пусть вызывающий код решает
            raise

    async def get_by_status(
        self,
        status: ReportStatus | str,
        limit: Optional[int] = None
    ) -> List[Report]:
        """
        Get reports by status.
        
        Args:
            status: ReportStatus enum or string
            limit: Maximum number of reports to return (optional)
            
        Returns:
            List of Report instances
        """
        # Convert string to enum if needed
        if isinstance(status, str):
            try:
                status = ReportStatus(status)
            except ValueError:
                logger.error(f"Invalid status value: {status}")
                return []
        
        stmt = (
            select(Report)
            .where(Report.status == status)
            .order_by(desc(Report.created_at))
        )
        
        if limit is not None:
            stmt = stmt.limit(limit)
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

