from fastapi import APIRouter, Request, UploadFile, File, HTTPException
from src.models.api_mapping_models import *
from src.services.api_mapping_service import *

router = APIRouter()


@router.post("/job-instances/file/mapping2")
async def map_data_fields(dto: MapDataFieldsRequest, request: Request, file: UploadFile = File(...)):
    try:
        token = request.headers.get("Authorization")
        return await map_data_fields_service(dto, file, token)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/file/mapping/fields-extraction2")
async def map_excel_data_field_value(dto: ExcelFieldExtractionRequest, file: UploadFile = File(...)):
    try:
        return await map_excel_data_field_value_service(dto, file)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/job-creation/excel/mapping2")
async def json_mapping(dto: JsonMappingRequest, request: Request, file: UploadFile = File(None)):
    try:
        token = request.headers.get("Authorization")
        return await json_mapping_service(dto, file, token)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/calculate/weightage-score2")
async def get_score(dto: ScoreRequest, request: Request):
    try:
        token = request.headers.get("Authorization")
        return await get_score_service(dto, token)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/v2/data-extraction/excel/sheet-list2")
async def get_sheet_names(dto: SheetRequest, request: Request):
    try:
        token = request.headers.get("Authorization")
        return await get_sheet_names_service(dto, token)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/v2/data-extraction/{file_type}/table-list2")
async def get_file_table_names(file_type: str, dto: TableListRequest, request: Request):
    try:
        token = request.headers.get("Authorization")
        return await get_file_table_names_service(dto, file_type, token)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/v2/data-extraction/excel/file-processing2")
async def data_extraction(dto: AttachmentRequest, request: Request):
    try:
        token = request.headers.get("Authorization")
        return await data_extraction_service(dto, token)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/v2/data-extraction/excel/create-table2")
async def create_table(dto: CreateTableRequest, request: Request):
    try:
        token = request.headers.get("Authorization")
        return await create_table_service(dto, token)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/v2/data-extraction/{file_type}/delete-table2")
async def delete_table(file_type: str, dto: DeleteTableRequest, request: Request):
    try:
        token = request.headers.get("Authorization")
        return await delete_table_service(dto, file_type, token)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/v2/data-extraction/excel/dataset-mapping2")
async def dataset_mapping(dto: DatasetMappingRequest, request: Request):
    try:
        token = request.headers.get("Authorization")
        return await dataset_mapping_service(dto, token)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/v2/data-extraction/excel/fields-extraction2")
async def excel_field_extraction(dto: FieldExtractionRequest, request: Request):
    try:
        token = request.headers.get("Authorization")
        return await excel_field_extraction_service(dto, token)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/v2/data-extraction/{file_type}/file-processing2")
async def docx_file_processing(file_type: str, dto: AttachmentRequest, request: Request):
    try:
        token = request.headers.get("Authorization")
        return await docx_file_processing_service(dto, file_type, token)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/v2/data-extraction/{file_type}/dataset-mapping2")
async def docx_dataset_mapping(file_type: str, dto: DatasetMappingRequest, request: Request):
    try:
        token = request.headers.get("Authorization")
        return await docx_dataset_mapping_service(dto, file_type, token)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/v2/data-extraction/{file_type}/fields-extraction2")
async def docx_field_extraction(file_type: str, dto: FieldExtractionRequest, request: Request):
    try:
        token = request.headers.get("Authorization")
        return await docx_field_extraction_service(dto, file_type, token)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))