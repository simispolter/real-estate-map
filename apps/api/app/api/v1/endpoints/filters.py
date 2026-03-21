from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.public import FiltersMetadataResponse
from app.services.catalog import get_filter_metadata

router = APIRouter()


@router.get("/metadata", response_model=FiltersMetadataResponse)
async def get_filters_metadata(
    session: AsyncSession = Depends(get_db_session),
) -> FiltersMetadataResponse:
    return FiltersMetadataResponse.model_validate(await get_filter_metadata(session))
