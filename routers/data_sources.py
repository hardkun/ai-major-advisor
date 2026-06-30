from fastapi import APIRouter, status

from crud.data_sources import create_data_source, list_data_sources
from schemas.data_sources import DataSourceCreate, DataSourceResponse


router = APIRouter(prefix="/data-sources", tags=["data-sources"])


@router.post("", response_model=DataSourceResponse, status_code=status.HTTP_201_CREATED)
def add_data_source(data: DataSourceCreate) -> DataSourceResponse:
    return create_data_source(data)


@router.get("", response_model=list[DataSourceResponse])
def get_data_sources() -> list[DataSourceResponse]:
    return list_data_sources()

