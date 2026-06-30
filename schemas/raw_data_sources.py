from pydantic import BaseModel, Field


class RawDataSourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    source_type: str | None = None
    url: str | None = None
    parser_type: str | None = Field(
        default=None,
        examples=["csv_url", "html_table", "excel_url", "pdf", "manual_upload", "school_page"],
    )
    enabled: bool = True
    description: str | None = None
    school_name: str | None = None
    discovery_score: int = 0
    discovery_mode: str | None = None
    is_demo: bool = False
    is_candidate: bool = False
    candidate_status: str | None = None
    official_check_status: str | None = None
    official_check_message: str | None = None
    official_score: int = 0
    candidate_reject_reason: str | None = None
    reference_only: bool = False
    field_mapping_json: str | None = None
    parser_config_json: str | None = None
    parent_source_id: int | None = None
    file_type: str | None = None
    local_file_path: str | None = None
    file_size: int | None = None
    file_download_status: str | None = None
    file_download_message: str | None = None


class RawDataSourceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    source_type: str | None = None
    url: str | None = None
    parser_type: str | None = None
    enabled: bool | None = None
    description: str | None = None
    school_name: str | None = None
    discovery_score: int | None = None
    discovery_mode: str | None = None
    is_demo: bool | None = None
    is_candidate: bool | None = None
    candidate_status: str | None = None
    official_check_status: str | None = None
    official_check_message: str | None = None
    official_score: int | None = None
    candidate_reject_reason: str | None = None
    reference_only: bool | None = None
    field_mapping_json: str | None = None
    parser_config_json: str | None = None
    parent_source_id: int | None = None
    file_type: str | None = None
    local_file_path: str | None = None
    file_size: int | None = None
    file_download_status: str | None = None
    file_download_message: str | None = None


class RawDataSourceResponse(BaseModel):
    id: int
    name: str
    source_type: str | None
    url: str | None
    parser_type: str | None
    enabled: bool
    description: str | None
    school_name: str | None = None
    discovery_score: int | None = 0
    discovery_mode: str | None = None
    is_demo: bool = False
    is_candidate: bool = False
    candidate_status: str | None = None
    official_check_status: str | None = None
    official_check_message: str | None = None
    official_score: int | None = 0
    candidate_reject_reason: str | None = None
    reference_only: bool = False
    field_mapping_json: str | None
    parser_config_json: str | None
    parent_source_id: int | None = None
    file_type: str | None = None
    local_file_path: str | None = None
    file_size: int | None = None
    file_download_status: str | None = None
    file_download_message: str | None = None
    last_check_status: str | None = None
    last_check_message: str | None = None
    last_content_type: str | None = None
    last_detected_type: str | None = None
    last_table_count: int | None = 0
    last_file_links_json: str | None = None
    last_checked_at: str | None = None
    collect_diagnosis_status: str | None = None
    collect_diagnosis_message: str | None = None
    last_preview_json: str | None = None
    last_preview_at: str | None = None
    created_at: str
    updated_at: str
