from pydantic import BaseModel
from typing import Optional


class MapDataFieldsRequest(BaseModel):
    tenant_name: Optional[str]
    jobtype: str
    sheet_name: Optional[str]


class ExcelFieldExtractionRequest(BaseModel):
    data: str
    sheet_no: Optional[str]
    header_row: Optional[str]
    table_orientation: Optional[str]


class JsonMappingRequest(BaseModel):
    tenant_name: Optional[str]
    target_jobtype: str
    target_output_schema_config_id: str
    mail_instance_id: str
    file_url: Optional[str]


class ScoreRequest(BaseModel):
    tenantName: Optional[str]
    jobInstanceId: str
    configurationJobInstanceId: str
    attachmentSubJobType: str
    attachmentFieldName: str


class SheetRequest(BaseModel):
    tenant_name: Optional[str]
    jobinstance_id: str


class TableListRequest(BaseModel):
    tenant_name: Optional[str]
    jobinstance_id: str


class AttachmentRequest(BaseModel):
    tenant_name: Optional[str]
    attachment_id: str


class CreateTableRequest(BaseModel):
    tenant_name: Optional[str]
    jobinstance_id: str
    sheet_name: Optional[str]
    table_name: Optional[str]
    table_range: Optional[str]
    orientation: Optional[str]
    table_data: str


class DeleteTableRequest(BaseModel):
    tenant_name: Optional[str]
    jobinstance_id: str
    table_name: str


class DatasetMappingRequest(BaseModel):
    tenant_name: Optional[str]
    jobinstance_id: str
    table_name: str
    jobtype: str


class FieldExtractionRequest(BaseModel):
    tenant_name: Optional[str]
    jobinstance_id: str
    table_name: str
    data: str