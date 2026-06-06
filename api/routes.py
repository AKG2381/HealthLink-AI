"""
API routes for HealthLink.
FastAPI endpoints for health assessment and related operations.
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from config.settings import Settings, get_settings
from config.logging import get_logger
from core.llm import LLMClient, get_llm_client
from core.database import (
    get_db_session,
    get_db_manager,
    get_all_doctors,
    get_doctors_by_specialty,
    get_doctor_by_id,
    DoctorModel,
)
from core.schemas import (
    HealthAssessmentRequest,
    HealthAssessmentResponse,
    HealthCheckResponse,
    ErrorResponse,
    DoctorDB
)
from core.orchestrator import orchestrate_health_assessment, validate_assessment_request
from utils.validators import validate_user_input


logger = logging.getLogger("healthlink.api")

router = APIRouter()


def get_db(settings: Settings = Depends(get_settings)) -> Session:
    """
    Request-scoped database session dependency.

    Using this via Depends() ensures FastAPI runs the generator's finally block
    after the response, so the session is always closed (the previous code called
    next() manually and leaked a connection on every request).
    """
    db_manager = get_db_manager(settings)
    session = db_manager.get_session()
    try:
        yield session
    finally:
        session.close()


@router.get("/health", response_model=HealthCheckResponse, tags=["System"])
def health_check(settings: Settings = Depends(get_settings)):
    """
    Health check endpoint.

    Returns system status and service availability.
    """
    logger.info("Health check requested")

    services_status = {
        "llm": "healthy" if settings.anthropic_api_key else "unavailable",
        "database": "healthy",
        "rag": ("healthy" if settings.pinecone_api_key else "unavailable") if settings.enable_rag else "disabled"
    }

    return HealthCheckResponse(
        status="healthy",
        version="1.0.0",
        services=services_status
    )


@router.post(
    "/assess",
    response_model=HealthAssessmentResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    },
    tags=["Assessment"]
)
def assess_health(
    request: HealthAssessmentRequest,
    db_session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """
    Main health assessment endpoint.

    Processes user's health concerns through the complete agent pipeline:
    1. Symptom extraction and analysis
    2. Doctor recommendations
    3. Scheduling suggestions
    4. Comprehensive summary

    Args:
        request: Health assessment request with user input

    Returns:
        Complete health assessment with recommendations

    Example:
        ```json
        {
            "user_input": "I have a severe headache and fever for 3 days",
            "user_id": "user123",
            "preferred_date": "2024-02-15"
        }
        ```
    """
    logger.info(f"Health assessment requested for user: {request.user_id or 'anonymous'}")

    # Validate request
    is_valid, validation_error = validate_assessment_request(request)
    if not is_valid:
        logger.warning(f"Invalid request: {validation_error}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=validation_error
        )

    is_valid, validation_error = validate_user_input(request.user_input)
    if not is_valid:
        logger.warning(f"Invalid user input: {validation_error}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=validation_error
        )

    logger.info(f"Processing request with input: {request.user_input[:100]}")

    try:
        response = orchestrate_health_assessment(
            request=request,
            db_session=db_session,
            llm_client=None,
            settings=settings
        )

        logger.info(f"Assessment complete [request_id={response.request_id}]")
        return response

    except Exception as e:
        logger.error(f"Assessment failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred processing your request. Please try again."
        )


@router.get("/test_simple", tags=["Debug"])
async def test_simple():
    """Simple test endpoint."""
    return {"message": "test works"}


@router.get(
    "/doctors",
    tags=["Doctors"]
)
def list_doctors(
    db_session: Session = Depends(get_db),
    specialty: Optional[str] = Query(None, description="Filter by medical specialty"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of doctors to return"),
):
    """
    List available doctors, optionally filtered by specialty.

    Returns:
        List of doctors
    """
    logger.info(f"Listing doctors (specialty={specialty!r}, limit={limit})")

    try:
        if specialty:
            doctors = get_doctors_by_specialty(db_session, specialty)
        else:
            doctors = get_all_doctors(db_session)
        doctors = doctors[:limit]

        doctor_responses = [
            DoctorDB(
                id=d.id,
                name=d.name,
                specialty=d.specialty,
                experience_years=d.experience_years,
                rating=d.rating,
                availability=d.availability,
                location=d.location,
                email=d.email,
                phone=d.phone
            )
            for d in doctors
        ]

        logger.info(f"Returning {len(doctor_responses)} doctors")
        return doctor_responses

    except Exception as e:
        logger.error(f"Failed to list doctors: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve doctors"
        )


@router.get(
    "/doctors/{doctor_id}",
    response_model=DoctorDB,
    responses={404: {"model": ErrorResponse}},
    tags=["Doctors"]
)
def get_doctor(
    doctor_id: int,
    db_session: Session = Depends(get_db),
):
    """
    Get doctor by ID.

    Args:
        doctor_id: Doctor's unique identifier

    Returns:
        Doctor information
    """
    logger.info(f"Getting doctor with ID: {doctor_id}")

    try:
        doctor = get_doctor_by_id(db_session, doctor_id)

        if not doctor:
            logger.warning(f"Doctor not found: {doctor_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Doctor with ID {doctor_id} not found"
            )

        return DoctorDB(
            id=doctor.id,
            name=doctor.name,
            specialty=doctor.specialty,
            experience_years=doctor.experience_years,
            rating=doctor.rating,
            availability=doctor.availability,
            location=doctor.location,
            email=doctor.email,
            phone=doctor.phone
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get doctor: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve doctor"
        )


@router.get(
    "/specialties",
    response_model=List[str],
    tags=["Doctors"]
)
def list_specialties(db_session: Session = Depends(get_db)):
    """
    List all available medical specialties.

    Returns:
        List of unique specialties
    """
    logger.info("Listing medical specialties")

    try:
        doctors = get_all_doctors(db_session)
        specialties = sorted(list(set(d.specialty for d in doctors)))

        logger.info(f"Returning {len(specialties)} specialties")
        return specialties

    except Exception as e:
        logger.error(f"Failed to list specialties: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve specialties"
        )