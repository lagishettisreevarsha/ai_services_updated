import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from fastapi import HTTPException

from services.excel_service import get_field_from_excel, get_field_values_from_excel_content
from services.pdf_service import delete_table_data_from_instance_id_pdf, extract_values_from_pdf_by_instance_id, get_table_list_from_id_pdf, process_instance_id_and_map_dataset_fields_for_pdf_table, process_pdf_and_call_llm
from src.helper.api_mapping_helper import validate_token, convert_to_int


executor = ThreadPoolExecutor()
INVALID_FILE_TYPE = "Invalid file type"


async def map_data_fields_service(dto, file, token):
    try:
        validate_token(token, dto.tenant_name)

        if file.filename == "":
            raise HTTPException(400, "No selected file")

        sheet = convert_to_int(dto.sheet_name)
        file_type = get_file_type(file)

        if file_type != "XLSX":
            raise HTTPException(400, "Add Excel file for processing of format xlsx")

        res = get_field_values_from_excel_content(token, dto.tenant_name, dto.jobtype, file.file, sheet)

        return {
            "Fields": res[0],
            "headers_list": res[1],
            "header_row": res[2],
            "table_orientation": res[3],
        }

    except Exception as e:
        raise HTTPException(500, str(e))


async def map_excel_data_field_value_service(dto, file):
    try:
        sheet = convert_to_int(dto.sheet_no)

        res = get_field_from_excel(file.file, sheet, dto.header_row, dto.data, dto.table_orientation)

        return {"Result_json": res}

    except Exception as e:
        raise HTTPException(500, str(e))


async def json_mapping_service(dto, file, token):
    try:
        validate_token(token, dto.tenant_name)

        if not file:
            if not dto.file_url:
                raise HTTPException(400, "Either 'file' or 'file_url' is mandatory")

            file = convert_url_to_pdf_bytes(token, dto.tenant_name, dto.file_url)
            file_type = get_file_type(dto.file_url)
        else:
            file_type = get_file_type(file)

        if file_type != "XLSX":
            raise HTTPException(400, "Add Excel file for processing of format xlsx")

        content = get_all_tables_from_excel(file)

        executor.submit(
            asyncio.run,
            excel_background_process_async(
                token,
                dto.tenant_name,
                dto.target_jobtype,
                dto.target_output_schema_config_id,
                dto.mail_instance_id,
                content,
            ),
        )

        return {"message": "Processing started in background"}

    except Exception as e:
        raise HTTPException(500, str(e))


async def get_score_service(dto, token):
    try:
        validate_token(token, dto.tenantName)

        executor.submit(
            asyncio.run,
            module_score_calculation_async(
                token,
                dto.tenantName,
                dto.jobInstanceId,
                dto.configurationJobInstanceId,
                dto.attachmentSubJobType,
                dto.attachmentFieldName,
            ),
        )

        return {"message": "CRE Score Calculation started "}

    except Exception as e:
        raise HTTPException(500, str(e))


async def get_sheet_names_service(dto, token):
    try:
        validate_token(token, dto.tenant_name)

        res = get_sheet_list_from_id(token, dto.tenant_name, dto.jobinstance_id)
        return {"sheet_list": res}

    except Exception as e:
        raise HTTPException(500, str(e))


async def get_file_table_names_service(dto, file_type, token):
    try:
        validate_token(token, dto.tenant_name)

        if file_type == "excel":
            res = get_table_list_from_id(token, dto.tenant_name, dto.jobinstance_id)
        elif file_type == "docx":
            res = get_table_list_from_id_docx(token, dto.tenant_name, dto.jobinstance_id)
        elif file_type == "pdf":
            res = get_table_list_from_id_pdf(token, dto.tenant_name, dto.jobinstance_id)
        elif file_type == "image":
            res = get_table_list_from_id_image(token, dto.tenant_name, dto.jobinstance_id)
        else:
            return {"response": INVALID_FILE_TYPE}

        return {"table_list": res}

    except Exception as e:
        raise HTTPException(500, str(e))


async def data_extraction_service(dto, token):
    try:
        validate_token(token, dto.tenant_name)

        res = process_excel_file_url_from_instance_id(token, dto.tenant_name, dto.attachment_id)
        return {"response": res}

    except Exception as e:
        raise HTTPException(500, str(e))


async def create_table_service(dto, token):
    try:
        validate_token(token, dto.tenant_name)

        if not dto.table_name and not dto.table_range:
            return {"response": "table name or table range is mandatory"}

        data_list = json.loads(dto.table_data)["data"]

        res = add_new_table_in_instances(
            token,
            dto.tenant_name,
            dto.jobinstance_id,data_list,
            dto.sheet_name,
            dto.table_name,
            dto.table_range,
            dto.orientation,
        )

        return {"response": res}

    except Exception as e:
        raise HTTPException(500, str(e))


async def delete_table_service(dto, file_type, token):
    try:
        validate_token(token, dto.tenant_name)

        if file_type == "excel":
            res = delete_table_data_from_instance_id(token, dto.tenant_name, dto.jobinstance_id, dto.table_name)
        elif file_type == "docx":
            res = delete_table_data_from_instance_id_docx(token, dto.tenant_name, dto.jobinstance_id, dto.table_name)
        elif file_type == "pdf":
            res = delete_table_data_from_instance_id_pdf(token, dto.tenant_name, dto.jobinstance_id, dto.table_name)
        elif file_type == "image":
            res = delete_table_data_from_instance_id_image(token, dto.tenant_name, dto.jobinstance_id, dto.table_name)
        else:
            return {"response": INVALID_FILE_TYPE}

        return {"response": res}

    except Exception as e:
        raise HTTPException(500, str(e))


async def dataset_mapping_service(dto, token):
    try:
        validate_token(token, dto.tenant_name)

        res = process_instance_id_and_map_dataset_fields(
            token, dto.tenant_name, dto.jobtype, dto.jobinstance_id, dto.table_name
        )

        return {"response": res}

    except Exception as e:
        raise HTTPException(500, str(e))


async def excel_field_extraction_service(dto, token):
    try:
        validate_token(token, dto.tenant_name)

        res = extract_values_from_excel_by_instance_id(
            token, dto.tenant_name, dto.data, dto.table_name, dto.jobinstance_id
        )

        return {"Result_json": res}

    except Exception as e:
        raise HTTPException(500, str(e))


async def docx_file_processing_service(dto, file_type, token):
    try:
        validate_token(token, dto.tenant_name)

        if file_type == "docx":
            res = process_tables_from_docx(token, dto.tenant_name, dto.attachment_id)
        elif file_type == "pdf":
            res = process_pdf_and_call_llm(token, dto.tenant_name, dto.attachment_id)
        elif file_type == "image":
            res = process_tables_from_image(token, dto.tenant_name, dto.attachment_id)
        else:
            return {"response": INVALID_FILE_TYPE}

        return {"response": res}

    except Exception as e:
        raise HTTPException(500, str(e))


async def docx_dataset_mapping_service(dto, file_type, token):
    try:
        validate_token(token, dto.tenant_name)

        if file_type == "docx":
            res = process_instance_id_and_map_dataset_fields_for_docx(token, dto.tenant_name, dto.jobtype, dto.table_name, dto.jobinstance_id)
        elif file_type == "pdf":
            res = process_instance_id_and_map_dataset_fields_for_pdf_table(token, dto.tenant_name, dto.jobtype, dto.table_name, dto.jobinstance_id)
        elif file_type == "image":
            res = process_instance_id_and_map_dataset_fields_for_image_table(token, dto.tenant_name, dto.jobtype, dto.table_name, dto.jobinstance_id)
        else:
            return {"response": INVALID_FILE_TYPE}

        return {"response": res}

    except Exception as e:
        raise HTTPException(500, str(e))


async def docx_field_extraction_service(dto, file_type, token):
    try:
        validate_token(token, dto.tenant_name)

        if file_type == "docx":
            res = extract_values_from_docx_by_instance_id(token, dto.tenant_name, dto.data, dto.table_name, dto.jobinstance_id)
        elif file_type == "pdf":
            res = extract_values_from_pdf_by_instance_id(token, dto.tenant_name, dto.data, dto.table_name, dto.jobinstance_id)
        elif file_type == "image":
            res = extract_values_from_img_by_instance_id(token, dto.tenant_name, dto.data, dto.table_name, dto.jobinstance_id)
        else:
            return {"response": INVALID_FILE_TYPE}

        return {"Result_json": res}

    except Exception as e:
        raise HTTPException(500, str(e))