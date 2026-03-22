from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.public import ExternalLayersResponse, MapExternalLayersResponse, MapProjectsResponse
from app.services.catalog import ProjectListFilters, get_map_projects
from app.services.external_layers import get_map_external_layer_features, list_public_external_layers

router = APIRouter()


@router.get("/projects", response_model=MapProjectsResponse)
async def get_map_projects_endpoint(
    q: str | None = None,
    city: str | None = None,
    company_id: str | None = None,
    project_business_type: str | None = None,
    government_program_type: str | None = None,
    project_urban_renewal_type: str | None = None,
    permit_status: str | None = None,
    location_confidence: str | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> MapProjectsResponse:
    filters = ProjectListFilters(
        q=q,
        city=city,
        company_id=UUID(company_id) if company_id else None,
        project_business_type=project_business_type,
        government_program_type=government_program_type,
        project_urban_renewal_type=project_urban_renewal_type,
        permit_status=permit_status,
        location_confidence=location_confidence,
        page=1,
        page_size=500,
    )
    return MapProjectsResponse.model_validate(await get_map_projects(session, filters))


@router.get("/layers", response_model=ExternalLayersResponse)
async def get_map_layers_endpoint(
    session: AsyncSession = Depends(get_db_session),
) -> ExternalLayersResponse:
    return ExternalLayersResponse(items=await list_public_external_layers(session))


@router.get("/layers/features", response_model=MapExternalLayersResponse)
async def get_map_layer_features_endpoint(
    layer_ids: str | None = None,
    city: str | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> MapExternalLayersResponse:
    parsed_ids = [UUID(value) for value in layer_ids.split(",") if value.strip()] if layer_ids else []
    return MapExternalLayersResponse.model_validate(
        await get_map_external_layer_features(session, parsed_ids, city=city),
    )
