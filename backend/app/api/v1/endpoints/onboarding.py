"""
Onboarding endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func, and_
from loguru import logger
from uuid import uuid4
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone as tz, timedelta

from app.core.database import get_db
from app.models.onboarding import OnboardingSession, OnboardingStep
from app.api.dependencies import get_current_user_optional
from app.models import User
from app.core.access_control import invalidate_user_cache

router = APIRouter()


async def get_valid_session(
    session_token: str,
    db: AsyncSession
) -> OnboardingSession:
    """
    Get onboarding session by token and validate it's not expired.
    
    Raises:
        HTTPException: If session not found or expired
    """
    result = await db.execute(
        select(OnboardingSession).where(OnboardingSession.session_token == session_token)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Check if session is expired
    if session.expires_at and session.expires_at < datetime.now(tz.utc):
        logger.warning(f"Expired onboarding session accessed: {session_token[:8]}...")
        raise HTTPException(status_code=410, detail="Session expired. Please start a new onboarding session.")
    
    return session


@router.post("/start")
async def start_onboarding(
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Start a new onboarding session
    
    Creates a new onboarding session for the user (authenticated or anonymous).
    Returns a session_token that should be used for all subsequent onboarding requests.
    
    Returns:
        - session_token: Unique token for this onboarding session
        - session_id: UUID of the session
        - current_step: Current step in the onboarding flow (default: "company_input")
    """
    try:
        session_token = str(uuid4())
        
        # Set expiration time: 24 hours from now
        expires_at = datetime.now(tz.utc) + timedelta(hours=24)
        
        session = OnboardingSession(
            user_id=current_user.id if current_user else None,
            session_token=session_token,
            current_step=OnboardingStep.COMPANY_INPUT,
            expires_at=expires_at
        )
        
        db.add(session)
        await db.commit()
        await db.refresh(session)
        
        logger.info(
            f"Created onboarding session {session.id} for user {current_user.id if current_user else 'anonymous'}"
        )
        
        return {
            "session_token": session_token,
            "session_id": str(session.id),
            "current_step": session.current_step.value
        }
    except Exception as e:
        logger.error(f"Failed to start onboarding session: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to start onboarding session: {str(e)}")


@router.post("/company/analyze")
async def analyze_company(
    request: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Analyze company website for onboarding
    
    Extracts company information from the website URL and generates AI description.
    Saves the data to the onboarding session.
    
    Request body:
        - session_token: Token from /onboarding/start
        - website_url: URL of the company website (e.g., "https://example.com")
    
    Returns:
        - company: Company data with AI description and industry signals
        - current_step: Updated step (should be "company_card")
    """
    from app.services.company_info_extractor import extract_company_info
    from loguru import logger
    
    session_token = request.get("session_token")
    website_url = request.get("website_url")
    
    if not session_token or not website_url:
        raise HTTPException(status_code=400, detail="session_token and website_url are required")
    
    # Get and validate session
    session = await get_valid_session(session_token, db)
    
    try:
        # Extract company info from website
        company_info = await extract_company_info(website_url)
        
        # Add website URL to company info
        company_info['website'] = website_url
        
        # Generate AI description and industry signals using GPT service
        try:
            from app.services.gpt_service import GPTService
            gpt_service = GPTService()
            
            # Generate AI description (always in English)
            ai_description = await gpt_service.generate_company_description(company_info)
            if ai_description:
                company_info['ai_description'] = ai_description
                # Always use AI-generated description (in English) instead of meta_description
                company_info['description'] = ai_description
            
            # Generate industry signals
            industry_signals = await gpt_service.suggest_industry_signals(company_info)
            if industry_signals:
                company_info['industry_signals'] = industry_signals
        except Exception as gpt_error:
            logger.warning(f"Failed to generate AI description/signals: {gpt_error}. Continuing without GPT features.")
        
        # Save company data to session
        session.company_data = company_info
        session.current_step = OnboardingStep.COMPANY_CARD
        await db.commit()
        await db.refresh(session)
        
        logger.info(f"Analyzed company for onboarding: {company_info.get('name')}")
        
        return {
            "company": company_info,
            "current_step": session.current_step.value
        }
    except Exception as e:
        logger.error(f"Failed to analyze company {website_url}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to analyze company: {str(e)}")


@router.get("/company")
async def get_company(
    session_token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Get company data from onboarding session"""
    session = await get_valid_session(session_token, db)
    
    return {
        "company": session.company_data or {},
        "current_step": session.current_step.value
    }


@router.get("/competitors/suggest")
async def suggest_competitors(
    session_token: str = Query(...),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """Suggest competitors for onboarding"""
    from app.services.competitor_service import CompetitorAnalysisService
    from app.models.company import Company
    from datetime import datetime, timedelta, timezone
    from loguru import logger
    from sqlalchemy import or_, func, and_
    
    session = await get_valid_session(session_token, db)
    
    if not session.company_data:
        raise HTTPException(status_code=400, detail="Company data not found. Please analyze company first.")
    
    company_data = session.company_data
    company_name = company_data.get('name')
    company_category = company_data.get('category')
    company_website = company_data.get('website')
    
    try:
        # For onboarding, always use GPT to generate competitors
        # Onboarding is for new users who don't have companies in the database yet
        from app.services.gpt_service import GPTService
        gpt_service = GPTService()
        
        logger.info(f"Using GPT to generate competitors for onboarding: {company_name}")
        
        competitors = []
        
        # Generate competitors list using GPT
        gpt_competitors = await gpt_service.suggest_competitors_list(company_data, limit=limit)
        
        if gpt_competitors and len(gpt_competitors) > 0:
            # Convert GPT suggestions to competitor format
            # Note: GPT already provides descriptions, so we don't need to generate additional AI descriptions
            # This saves time and API calls
            for gpt_comp in gpt_competitors:
                # Generate temporary UUID for new competitors (not in DB yet)
                # This will be used to track competitors during onboarding
                temp_id = str(uuid4())
                
                competitor_dict = {
                    "company": {
                        "id": temp_id,  # Temporary ID for tracking during onboarding
                        "name": gpt_comp.get("name", ""),
                        "website": gpt_comp.get("website", ""),
                        "description": gpt_comp.get("description", ""),  # Already in English from GPT
                        "logo_url": None,
                        "category": company_category,
                        "ai_description": gpt_comp.get("description", "")  # Use GPT description as ai_description
                    },
                    "similarity_score": 0.8,  # High score for GPT-generated competitors
                    "common_categories": [company_category] if company_category else [],
                    "reason": gpt_comp.get("reason", "AI-generated competitor")
                }
                
                competitors.append(competitor_dict)
            
            logger.info(f"GPT generated {len(competitors)} competitors for {company_name}")
        else:
            # If GPT fails, return empty list (don't use database fallback for onboarding)
            logger.warning(f"GPT failed to generate competitors for {company_name}. Returning empty list.")
            competitors = []
        
        logger.info(f"Suggested {len(competitors)} competitors for onboarding session {session_token[:8]}")
        
        return {
            "competitors": competitors,
            "current_step": session.current_step.value
        }
    except Exception as e:
        logger.error(f"Failed to suggest competitors: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to suggest competitors: {str(e)}")


@router.post("/competitors/replace")
async def replace_competitor(
    request: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """Replace a competitor in onboarding with a new one"""
    from app.services.competitor_service import CompetitorAnalysisService
    from app.models.company import Company
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import or_, func, and_
    from uuid import UUID
    
    session_token = request.get("session_token")
    competitor_id_to_replace = request.get("competitor_id_to_replace")
    
    if not session_token:
        raise HTTPException(status_code=400, detail="session_token is required")
    
    if not competitor_id_to_replace:
        raise HTTPException(status_code=400, detail="competitor_id_to_replace is required")
    
    session = await get_valid_session(session_token, db)
    
    if not session.company_data:
        raise HTTPException(status_code=400, detail="Company data not found. Please analyze company first.")
    
    try:
        # Validate competitor_id_to_replace format
        try:
            competitor_uuid_to_replace = UUID(competitor_id_to_replace)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid competitor_id_to_replace format")
        
        # Get excluded competitor IDs (the one being replaced + already selected)
        excluded_ids = [competitor_uuid_to_replace]
        if session.selected_competitors:
            for comp in session.selected_competitors:
                comp_id = comp.get("id")
                if comp_id:
                    try:
                        excluded_ids.append(UUID(comp_id))
                    except ValueError:
                        continue
        
        company_data = session.company_data
        company_name = company_data.get('name')
        company_category = company_data.get('category')
        company_website = company_data.get('website')
        
        # Try to find the company in database first (only for current user or global)
        company = None
        if company_website:
            from urllib.parse import urlparse
            parsed = urlparse(company_website)
            normalized_url = f"{parsed.scheme}://{parsed.netloc}".lower().replace('www.', '')
            
            # Filter by user_id: only show companies for current user or global (user_id is None)
            if session.user_id:
                user_filter = Company.user_id == session.user_id
            else:
                # Anonymous user - only show global companies
                user_filter = Company.user_id.is_(None)
            
            company_result = await db.execute(
                select(Company).where(
                    and_(
                        or_(
                            func.lower(func.replace(Company.website, 'www.', '')) == normalized_url,
                            Company.name.ilike(f"%{company_name}%")
                        ),
                        user_filter
                    )
                ).limit(1)
            )
            company = company_result.scalar_one_or_none()
        
        new_competitor = None
        
        if company:
            # Use CompetitorAnalysisService if company exists in DB
            competitor_service = CompetitorAnalysisService(db)
            date_from = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=30)
            date_to = datetime.now(timezone.utc).replace(tzinfo=None)
            
            # Get more suggestions to find one that's not excluded
            suggestions = await competitor_service.suggest_competitors(
                company.id,
                limit=50,  # Get more to find replacement
                date_from=date_from,
                date_to=date_to
            )
            
            # Find first competitor that's not in excluded list
            for s in suggestions:
                if not s or not isinstance(s, dict) or not s.get("company"):
                    continue
                
                comp_id = s.get("company", {}).get("id")
                if not comp_id:
                    continue
                
                try:
                    comp_uuid = UUID(str(comp_id))
                    if comp_uuid not in excluded_ids:
                        comp_description = s.get("company", {}).get("description", "")
                        comp_ai_description = s.get("company", {}).get("ai_description", "")
                        
                        new_competitor = {
                            "company": {
                                "id": str(comp_id),
                                "name": s.get("company", {}).get("name", ""),
                                "website": s.get("company", {}).get("website", ""),
                                "description": comp_description,
                                "logo_url": s.get("company", {}).get("logo_url"),
                                "category": s.get("company", {}).get("category"),
                                # Use existing AI description if available, otherwise use description
                                "ai_description": comp_ai_description or comp_description or ""
                            },
                            "similarity_score": s.get("similarity_score", 0.0),
                            "common_categories": s.get("common_categories", []),
                            "reason": s.get("reason", "Similar company")
                        }
                        
                        # Only generate AI description if we don't have one
                        if not comp_ai_description and not comp_description:
                            try:
                                from app.services.gpt_service import GPTService
                                gpt_service = GPTService()
                                competitor_data = new_competitor["company"]
                                ai_description = await gpt_service.generate_competitor_description(
                                    competitor_data,
                                    company_name or "Company"
                                )
                                if ai_description:
                                    new_competitor["company"]["ai_description"] = ai_description
                                    new_competitor["company"]["description"] = ai_description
                            except Exception as gpt_error:
                                logger.warning(f"Failed to generate AI description for replacement competitor: {gpt_error}")
                        
                        break
                except ValueError:
                    continue
        
        # If not found via service, try by category (only for current user or global)
        if not new_competitor and company_category:
            # Filter by user_id: only show companies for current user or global
            if session.user_id:
                user_filter = Company.user_id == session.user_id
            else:
                # Anonymous user - only show global companies
                user_filter = Company.user_id.is_(None)
            
            category_companies = await db.execute(
                select(Company).where(
                    and_(
                        Company.category == company_category,
                        user_filter,
                        ~Company.id.in_(excluded_ids)  # Exclude replaced and selected
                    )
                ).limit(20)
            )
            category_companies_list = category_companies.scalars().all()
            
            for comp in category_companies_list:
                if comp.id not in excluded_ids:
                    comp_description = comp.description or ""
                    
                    new_competitor = {
                        "company": {
                            "id": str(comp.id),
                            "name": comp.name,
                            "website": comp.website or "",
                            "description": comp_description,
                            "logo_url": comp.logo_url,
                            "category": comp.category,
                            # Use existing description as ai_description if available
                            "ai_description": comp_description or ""
                        },
                        "similarity_score": 0.7,
                        "common_categories": [company_category] if company_category else [],
                        "reason": f"Same category: {company_category}"
                    }
                    
                    # Only generate AI description if we don't have one
                    if not comp_description:
                        try:
                            from app.services.gpt_service import GPTService
                            gpt_service = GPTService()
                            competitor_data = new_competitor["company"]
                            ai_description = await gpt_service.generate_competitor_description(
                                competitor_data,
                                company_name or "Company"
                            )
                            if ai_description:
                                new_competitor["company"]["ai_description"] = ai_description
                                new_competitor["company"]["description"] = ai_description
                        except Exception as gpt_error:
                            logger.warning(f"Failed to generate AI description for replacement competitor: {gpt_error}")
                    
                    break
        
        # If still not found, get any company excluding the replaced one (only for current user or global)
        if not new_competitor:
            # Filter by user_id: only show companies for current user or global
            if session.user_id:
                user_filter = Company.user_id == session.user_id
            else:
                # Anonymous user - only show global companies
                user_filter = Company.user_id.is_(None)
            
            any_companies = await db.execute(
                select(Company).where(
                    and_(
                        user_filter,
                        ~Company.id.in_(excluded_ids)
                    )
                ).limit(20)
            )
            any_companies_list = any_companies.scalars().all()
            
            for comp in any_companies_list:
                if comp.id not in excluded_ids:
                    comp_description = comp.description or ""
                    
                    new_competitor = {
                        "company": {
                            "id": str(comp.id),
                            "name": comp.name,
                            "website": comp.website or "",
                            "description": comp_description,
                            "logo_url": comp.logo_url,
                            "category": comp.category,
                            # Use existing description as ai_description if available
                            "ai_description": comp_description or ""
                        },
                        "similarity_score": 0.5,
                        "common_categories": [],
                        "reason": "Available company"
                    }
                    
                    # Only generate AI description if we don't have one
                    if not comp_description:
                        try:
                            from app.services.gpt_service import GPTService
                            gpt_service = GPTService()
                            competitor_data = new_competitor["company"]
                            ai_description = await gpt_service.generate_competitor_description(
                                competitor_data,
                                company_name or "Company"
                            )
                            if ai_description:
                                new_competitor["company"]["ai_description"] = ai_description
                                new_competitor["company"]["description"] = ai_description
                        except Exception as gpt_error:
                            logger.warning(f"Failed to generate AI description for replacement competitor: {gpt_error}")
                    
                    break
        
        if not new_competitor:
            raise HTTPException(
                status_code=404,
                detail="No replacement competitor found. Please try again or select from suggested competitors."
            )
        
        logger.info(
            f"Replaced competitor {competitor_id_to_replace} with {new_competitor['company']['id']} "
            f"for session {session_token[:8]}"
        )
        
        return new_competitor
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to replace competitor: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to replace competitor: {str(e)}")


@router.post("/competitors/select")
async def select_competitors(
    request: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """Select competitors in onboarding"""
    from app.models.company import Company
    from uuid import UUID
    
    session_token = request.get("session_token")
    selected_competitor_ids = request.get("selected_competitor_ids", [])
    competitor_data = request.get("competitor_data", [])  # Optional full competitor data from frontend
    
    if not session_token:
        raise HTTPException(status_code=400, detail="session_token is required")
    
    if not selected_competitor_ids or len(selected_competitor_ids) == 0:
        raise HTTPException(status_code=400, detail="At least one competitor must be selected")
    
    result = await db.execute(
        select(OnboardingSession).where(OnboardingSession.session_token == session_token)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        # Prepare list to store selected competitors data
        selected_competitors_list = []
        
        # Build map of competitor data by ID (from frontend or from previous suggestions)
        competitor_data_map = {}
        if competitor_data and len(competitor_data) > 0:
            # Map competitor_data by ID for quick lookup
            for comp in competitor_data:
                comp_id = comp.get("id")
                if comp_id:
                    competitor_data_map[comp_id] = comp
        
        # Also check previously suggested competitors in session (if any)
        # This helps with temporary IDs from GPT-generated competitors
        if hasattr(session, 'selected_competitors') and session.selected_competitors:
            for comp in session.selected_competitors:
                comp_id = comp.get("id")
                if comp_id and comp_id not in competitor_data_map:
                    competitor_data_map[comp_id] = comp
        
        # Process selected competitor IDs
        for competitor_id in selected_competitor_ids:
            # First, try to find in competitor_data_map (includes temporary IDs)
            if competitor_id in competitor_data_map:
                comp_data = competitor_data_map[competitor_id]
                # Ensure all required fields are present
                selected_competitors_list.append({
                    "id": comp_data.get("id", competitor_id),  # Keep original ID (temp or real)
                    "name": comp_data.get("name", ""),
                    "website": comp_data.get("website", ""),
                    "description": comp_data.get("description") or comp_data.get("ai_description", ""),
                    "logo_url": comp_data.get("logo_url"),
                    "category": comp_data.get("category"),
                    "ai_description": comp_data.get("ai_description") or comp_data.get("description", "")
                })
                continue
            
            # Fallback: try to fetch from DB (for existing companies)
            try:
                competitor_uuid = UUID(competitor_id)
                comp_result = await db.execute(
                    select(Company).where(Company.id == competitor_uuid)
                )
                comp = comp_result.scalar_one_or_none()
                if comp:
                    selected_competitors_list.append({
                        "id": str(comp.id),
                        "name": comp.name,
                        "website": comp.website or "",
                        "description": comp.description or "",
                        "logo_url": comp.logo_url,
                        "category": comp.category,
                        "ai_description": comp.description or ""  # Use description as ai_description if available
                    })
                    continue
            except ValueError:
                # Not a valid UUID - might be a temporary ID, try to find in previous suggestions
                pass
            
            # If still not found, log warning but continue (don't fail completely)
            logger.warning(f"Competitor {competitor_id} not found in competitor_data or database")
        else:
            # Fetch competitors from database
            for competitor_id in selected_competitor_ids:
                try:
                    competitor_uuid = UUID(competitor_id)
                    # Filter by user_id: only allow selecting companies for current user or global
                    if session.user_id:
                        user_filter = Company.user_id == session.user_id
                    else:
                        # Anonymous user - only allow global companies
                        user_filter = Company.user_id.is_(None)
                    
                    comp_result = await db.execute(
                        select(Company).where(
                            and_(
                                Company.id == competitor_uuid,
                                user_filter
                            )
                        )
                    )
                    comp = comp_result.scalar_one_or_none()
                    if comp:
                        selected_competitors_list.append({
                            "id": str(comp.id),
                            "name": comp.name,
                            "website": comp.website or "",
                            "description": comp.description or "",
                            "logo_url": comp.logo_url,
                            "category": comp.category
                        })
                    else:
                        logger.warning(f"Competitor {competitor_id} not found in database or access denied")
                except (ValueError, Exception) as e:
                    logger.warning(f"Invalid competitor ID {competitor_id}: {e}")
                    continue
        
        if len(selected_competitors_list) == 0:
            raise HTTPException(
                status_code=400, 
                detail="None of the selected competitors could be found or processed"
            )
        
        # Save selected competitors to session
        session.selected_competitors = selected_competitors_list
        session.current_step = OnboardingStep.OBSERVATION_SETUP
        await db.commit()
        await db.refresh(session)
        
        logger.info(
            f"Selected {len(selected_competitors_list)} competitors for onboarding session {session_token[:8]}"
        )
        
        return {
            "status": "success",
            "selected_count": len(selected_competitors_list),
            "current_step": session.current_step.value
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to select competitors: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to select competitors: {str(e)}")


@router.post("/observation/setup")
async def setup_observation(
    request: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """Setup observation for competitors - launch Celery task"""
    from app.tasks.observation import setup_competitor_observation
    from uuid import UUID
    
    session_token = request.get("session_token")
    
    if not session_token:
        raise HTTPException(status_code=400, detail="session_token is required")
    
    result = await db.execute(
        select(OnboardingSession).where(OnboardingSession.session_token == session_token)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if not session.selected_competitors or len(session.selected_competitors) == 0:
        raise HTTPException(status_code=400, detail="No competitors selected. Please select competitors first.")
    
    try:
        # Extract company IDs from selected competitors
        company_ids = []
        for competitor in session.selected_competitors:
            competitor_id = competitor.get("id")
            if competitor_id:
                try:
                    # Validate UUID format
                    UUID(competitor_id)
                    company_ids.append(competitor_id)
                except ValueError:
                    logger.warning(f"Invalid competitor ID format: {competitor_id}")
                    continue
        
        if len(company_ids) == 0:
            raise HTTPException(
                status_code=400, 
                detail="No valid competitor IDs found. Please ensure competitors are selected."
            )
        
        # Launch Celery task
        task = setup_competitor_observation.delay(session_token, company_ids)
        task_id = task.id
        
        # Save task_id and initial status in observation_config
        if not session.observation_config:
            session.observation_config = {}
        
        session.observation_config.update({
            "task_id": task_id,
            "status": "processing",
            "started_at": datetime.now(tz.utc).isoformat(),
            "company_ids": company_ids,
            "total_companies": len(company_ids)
        })
        
        await db.commit()
        await db.refresh(session)
        
        logger.info(
            f"Started observation setup task {task_id} for session {session_token[:8]} "
            f"with {len(company_ids)} companies"
        )
        
        return {
            "task_id": task_id,
            "status": "processing",
            "total_companies": len(company_ids)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to setup observation: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to setup observation: {str(e)}")


@router.get("/observation/status")
async def get_observation_status(
    task_id: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Get observation setup status from Celery task"""
    from celery.result import AsyncResult
    from app.celery_app import celery_app
    
    if not task_id:
        raise HTTPException(status_code=400, detail="task_id is required")
    
    try:
        # Get Celery task result
        task_result = AsyncResult(task_id, app=celery_app)
        
        # Map Celery states to our status format
        celery_state = task_result.state
        
        # Determine status
        if celery_state == 'PENDING':
            status = 'pending'
            progress = 0
            message = 'Задача ожидает выполнения...'
        elif celery_state == 'PROGRESS':
            status = 'processing'
            # Get progress from task meta
            meta = task_result.info or {}
            progress = meta.get('progress', 0)
            message = meta.get('message', 'Обработка...')
        elif celery_state == 'SUCCESS':
            status = 'completed'
            progress = 100
            result = task_result.info or {}
            message = result.get('message', 'Наблюдение настроено успешно!')
        elif celery_state == 'FAILURE':
            status = 'failed'
            progress = 0
            error_info = task_result.info
            if isinstance(error_info, Exception):
                message = str(error_info)
            elif isinstance(error_info, dict):
                message = error_info.get('message', 'Ошибка при настройке наблюдения')
            else:
                message = 'Ошибка при настройке наблюдения'
        else:
            status = 'pending'
            progress = 0
            message = f'Неизвестный статус: {celery_state}'
        
        # Get extended meta information if available
        meta = task_result.info or {} if celery_state in ['PROGRESS', 'SUCCESS'] else {}
        
        response = {
            "task_id": task_id,
            "status": status,
            "progress": progress,
            "message": message
        }
        
        # Add extended information if available
        if isinstance(meta, dict):
            if 'current_step' in meta:
                response['current_step'] = meta['current_step']
            if 'current_company' in meta:
                response['current_company'] = meta['current_company']
            if 'total' in meta:
                response['total'] = meta['total']
            if 'completed' in meta:
                response['completed'] = meta['completed']
            if 'errors' in meta:
                response['errors'] = meta['errors']
        
        return response
        
    except Exception as e:
        logger.error(f"Failed to get observation status for task {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get observation status: {str(e)}")


@router.post("/complete")
async def complete_onboarding(
    request: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Complete onboarding - create companies and add to user subscriptions"""
    from app.models.company import Company
    from app.models.preferences import UserPreferences
    from sqlalchemy.orm.attributes import flag_modified
    from urllib.parse import urlparse
    from uuid import UUID
    import uuid as uuid_module
    from datetime import datetime, timezone as tz
    
    session_token = request.get("session_token")
    user_id_from_request = request.get("user_id")  # User ID from registration during onboarding
    
    if not session_token:
        raise HTTPException(status_code=400, detail="session_token is required")
    
    result = await db.execute(
        select(OnboardingSession).where(OnboardingSession.session_token == session_token)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Determine final user_id: from request, from current_user, or from session
    final_user_id = None
    if current_user:
        final_user_id = current_user.id
    elif user_id_from_request:
        try:
            final_user_id = UUID(user_id_from_request)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid user_id format")
    elif session.user_id:
        final_user_id = session.user_id
    
    if not final_user_id:
        raise HTTPException(
            status_code=400, 
            detail="User ID is required. Please register or login to complete onboarding."
        )
    
    # Update session with user_id if not set
    if not session.user_id:
        session.user_id = final_user_id
    
    if not session.company_data:
        raise HTTPException(status_code=400, detail="Company data not found in session")
    
    if not session.selected_competitors or len(session.selected_competitors) == 0:
        raise HTTPException(status_code=400, detail="No competitors selected")
    
    try:
        company_ids_to_subscribe = []
        
        # Helper function to normalize URL
        def normalize_url(url: str) -> str:
            if not url:
                return ""
            parsed = urlparse(url)
            normalized = f"{parsed.scheme}://{parsed.netloc}".lower().replace('www.', '')
            return normalized.rstrip('/')
        
        # 1. Create or get parent company from company_data
        company_data = session.company_data
        parent_website = company_data.get('website')
        
        if not parent_website:
            raise HTTPException(status_code=400, detail="Company website is required")
        
        normalized_parent_url = normalize_url(parent_website)
        
        # Check if parent company exists - only user's companies or global
        # Filter by user_id: only show companies for current user or global (user_id is None)
        user_filter = or_(
            Company.user_id == final_user_id,
            Company.user_id.is_(None)  # Global companies
        )
        
        parent_result = await db.execute(
            select(Company).where(
                or_(
                    func.lower(func.replace(Company.website, 'www.', '')) == normalized_parent_url.lower(),
                    Company.name.ilike(f"%{company_data.get('name', '')}%")
                ),
                user_filter
            ).order_by(
                # Prefer user's own companies first, then global companies
                Company.user_id.nulls_last() if final_user_id else Company.user_id.nulls_first()
            ).limit(1)
        )
        parent_company = parent_result.scalar_one_or_none()
        
        if parent_company:
            logger.info(f"Using existing parent company: {parent_company.name}")
            # Only allow using own companies or global companies
            if parent_company.user_id is not None and parent_company.user_id != final_user_id:
                # Company belongs to another user, create new one instead
                logger.info(f"Parent company belongs to another user, creating new one")
                parent_company = None
            elif parent_company.user_id is None:
                # Global company found, create a copy for this user so it appears in "My Competitors"
                logger.info(f"Global parent company found, creating user copy: {parent_company.name}")
                parent_company = Company(
                    name=parent_company.name,
                    website=parent_company.website,
                    description=company_data.get("description") or parent_company.description,
                    logo_url=company_data.get("logo_url") or parent_company.logo_url,
                    category=company_data.get("category") or parent_company.category,
                    user_id=final_user_id  # Create as user's company
                )
                db.add(parent_company)
                await db.flush()
                # Инвалидируем кеш при создании компании
                invalidate_user_cache(final_user_id)
            else:
                # Company already belongs to user, update if needed
                if not parent_company.description and company_data.get("description"):
                    parent_company.description = company_data["description"]
                if not parent_company.logo_url and company_data.get("logo_url"):
                    parent_company.logo_url = company_data["logo_url"]
                if not parent_company.category and company_data.get("category"):
                    parent_company.category = company_data["category"]
        
        if not parent_company:
            # Create new parent company
            logger.info(f"Creating new parent company: {company_data.get('name')}")
            parent_company = Company(
                name=company_data.get("name"),
                website=parent_website,
                description=company_data.get("description"),
                logo_url=company_data.get("logo_url"),
                category=company_data.get("category"),
                user_id=final_user_id
            )
            db.add(parent_company)
            await db.flush()
            # Инвалидируем кеш при создании компании
            invalidate_user_cache(final_user_id)
            
            # Schedule initial source scan for new parent company
            try:
                from app.tasks.scraping import scan_company_sources_initial
                scan_company_sources_initial.delay(str(parent_company.id))
                logger.info(f"Scheduled initial source scan for new parent company {parent_company.id}")
            except Exception as e:
                logger.warning(f"Failed to schedule initial source scan for parent company {parent_company.id}: {e}")
        
        company_ids_to_subscribe.append(parent_company.id)
        
        # 2. Process selected competitors
        competitor_companies = []
        for competitor_data in session.selected_competitors:
            competitor_id = competitor_data.get("id")
            competitor_name = competitor_data.get("name")
            competitor_website = competitor_data.get("website")
            
            if competitor_id:
                # Try to use existing company by ID
                try:
                    competitor_uuid = UUID(competitor_id)
                    comp_result = await db.execute(
                        select(Company).where(Company.id == competitor_uuid)
                    )
                    comp = comp_result.scalar_one_or_none()
                    
                    if comp:
                        competitor_companies.append(comp)
                        company_ids_to_subscribe.append(comp.id)
                        continue
                except ValueError:
                    pass
            
            # Create new company for competitor if not found
            if competitor_website:
                normalized_comp_url = normalize_url(competitor_website)
                
                # Check if competitor company exists by URL
                # For competitors, prefer global companies (user_id is None) or user's own companies
                # This prevents "Multiple rows were found" error
                comp_result = await db.execute(
                    select(Company).where(
                        and_(
                            func.lower(func.replace(Company.website, 'www.', '')) == normalized_comp_url.lower(),
                            or_(
                                Company.user_id.is_(None),  # Global companies first
                                Company.user_id == final_user_id  # Or user's own companies
                            )
                        )
                    ).order_by(
                        # Prefer global companies (user_id is None)
                        Company.user_id.nulls_first()
                    ).limit(1)
                )
                comp = comp_result.scalar_one_or_none()
                
                if comp:
                    # If company is global (user_id is None), create a copy for this user
                    # so it appears in "My Competitors"
                    if comp.user_id is None:
                        logger.info(f"Global company found, creating user copy: {competitor_name}")
                        # Use ai_description if available, otherwise use description
                        comp_description = competitor_data.get("ai_description") or competitor_data.get("description") or ""
                        # Create a copy for this user
                        comp = Company(
                            name=comp.name,
                            website=comp.website,
                            description=comp.description or comp_description,
                            logo_url=comp.logo_url,
                            category=comp.category or company_category,
                            user_id=final_user_id  # Create as user's company
                        )
                        db.add(comp)
                        await db.flush()
                        # Инвалидируем кеш при создании компании
                        invalidate_user_cache(final_user_id)
                    else:
                        # Company already belongs to user, use it
                        logger.info(f"Using existing user company: {competitor_name}")
                    
                    competitor_companies.append(comp)
                    company_ids_to_subscribe.append(comp.id)
                    continue
            
            # Create new competitor company
            logger.info(f"Creating new competitor company: {competitor_name}")
            # Use ai_description if available, otherwise use description
            comp_description = competitor_data.get("ai_description") or competitor_data.get("description") or ""
            comp = Company(
                name=competitor_name,
                website=competitor_website or "",
                description=comp_description,
                logo_url=competitor_data.get("logo_url"),
                category=competitor_data.get("category"),
                user_id=final_user_id  # Create as user's company so it appears in "My Competitors"
            )
            db.add(comp)
            await db.flush()
            # Инвалидируем кеш при создании компании
            invalidate_user_cache(final_user_id)
            competitor_companies.append(comp)
            company_ids_to_subscribe.append(comp.id)
            
            # Schedule initial source scan for new competitor company
            try:
                from app.tasks.scraping import scan_company_sources_initial
                scan_company_sources_initial.delay(str(comp.id))
                logger.info(f"Scheduled initial source scan for new competitor company {comp.id}")
            except Exception as e:
                logger.warning(f"Failed to schedule initial source scan for competitor {comp.id}: {e}")
        
        # 3. Get or create user preferences
        prefs_result = await db.execute(
            select(UserPreferences).where(UserPreferences.user_id == final_user_id)
        )
        user_prefs = prefs_result.scalar_one_or_none()
        
        if not user_prefs:
            logger.info(f"Creating user preferences for user {final_user_id}")
            user_prefs = UserPreferences(
                id=uuid_module.uuid4(),
                user_id=final_user_id,
                subscribed_companies=[],
                interested_categories=[],
                keywords=[],
                notification_frequency='daily',
                digest_enabled=True,  # Enable digests by default after onboarding
                digest_frequency='daily',
                digest_custom_schedule={},
                digest_format='short',
                digest_include_summaries=True,
                telegram_chat_id=None,
                telegram_enabled=False,
                timezone='UTC',
                week_start_day=0
            )
            db.add(user_prefs)
            await db.flush()
        
        # 4. Add all companies to subscribed_companies (avoid duplicates)
        if user_prefs.subscribed_companies is None:
            user_prefs.subscribed_companies = []
        
        # Combine existing and new subscriptions, remove duplicates
        existing_subscriptions = list(user_prefs.subscribed_companies) if user_prefs.subscribed_companies else []
        new_subscriptions = list(set(existing_subscriptions + company_ids_to_subscribe))
        user_prefs.subscribed_companies = new_subscriptions
        
        # Mark as modified for SQLAlchemy to detect ARRAY field change
        flag_modified(user_prefs, "subscribed_companies")
        
        # 5. Update session
        session.current_step = OnboardingStep.COMPLETED
        session.completed_at = datetime.now(tz.utc)
        
        # Commit all changes
        await db.commit()
        
        # 6. Create trial subscription
        try:
            from app.services.subscription_service import SubscriptionService
            subscription_service = SubscriptionService(db)
            
            # Get user email for dev environment checks
            user_result = await db.execute(
                select(User).where(User.id == final_user_id)
            )
            user = user_result.scalar_one_or_none()
            user_email = user.email if user else None
            
            trial_subscription = await subscription_service.create_trial_subscription(
                final_user_id,
                user_email=user_email
            )
            logger.info(
                f"Created trial subscription for user {final_user_id}, "
                f"expires at {trial_subscription.trial_ends_at if trial_subscription.trial_ends_at else 'never (dev)'}"
            )
        except Exception as e:
            # Not critical if trial creation fails - can be created later via API
            logger.warning(f"Failed to create trial subscription for user {final_user_id}: {e}")
        
        logger.info(
            f"Completed onboarding for user {final_user_id}: "
            f"parent company {parent_company.id}, {len(competitor_companies)} competitors, "
            f"total subscriptions: {len(new_subscriptions)}"
        )
        
        response_data = {
            "status": "success",
            "company_id": str(parent_company.id),
            "competitor_count": len(competitor_companies),
            "total_subscriptions": len(new_subscriptions),
            "companies": [
                {
                    "id": str(comp.id),
                    "name": comp.name,
                    "website": comp.website or ""
                }
                for comp in [parent_company] + competitor_companies
            ]
        }
        
        logger.info(f"Onboarding completed successfully for user {final_user_id}")
        return response_data
        
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        logger.error(f"Failed to complete onboarding: {e}", exc_info=True)
        await db.rollback()
        # Return a proper error response instead of just raising
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to complete onboarding: {str(e)}"
        )
