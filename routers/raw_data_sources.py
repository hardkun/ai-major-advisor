from fastapi import APIRouter, HTTPException, status

from crud.raw_data_sources import (
    create_raw_data_source,
    get_raw_data_source_by_id,
    list_raw_data_sources,
    update_raw_data_source,
)
from schemas.raw_data_sources import (
    RawDataSourceCreate,
    RawDataSourceResponse,
    RawDataSourceUpdate,
)


router = APIRouter(prefix="/raw-data-sources", tags=["raw-data-sources"])


@router.post(
    "",
    response_model=RawDataSourceResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_raw_data_source(data: RawDataSourceCreate) -> RawDataSourceResponse:
    return create_raw_data_source(data)


@router.get("", response_model=list[RawDataSourceResponse])
def get_raw_data_sources() -> list[RawDataSourceResponse]:
    return list_raw_data_sources()


@router.get("/{source_id}", response_model=RawDataSourceResponse)
def get_raw_data_source(source_id: int) -> RawDataSourceResponse:
    source = get_raw_data_source_by_id(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="原始数据源不存在")
    return source


@router.patch("/{source_id}", response_model=RawDataSourceResponse)
def edit_raw_data_source(
    source_id: int,
    data: RawDataSourceUpdate,
) -> RawDataSourceResponse:
    source = update_raw_data_source(
        source_id,
        data.model_dump(exclude_unset=True),
    )
    if not source:
        raise HTTPException(status_code=404, detail="原始数据源不存在")
    return source
