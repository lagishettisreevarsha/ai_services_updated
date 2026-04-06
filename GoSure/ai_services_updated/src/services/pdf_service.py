import json
from datetime import datetime
from src.azure.ai_search import azure_llm_process
from src.file_mapping.excel_extraction import get_file_type
from src.gosure_initialization.gosure_access import get_access_to_gosure_api


from src.helper.pdf_helper import extract_tables_from_pdf, get_file_stream_by_file_url, process_pdf_content_get_fields_response, format_pdf_llm_response_into_desired_json,map_data, convert_date_field_iso_format, process_df_get_json_data, process_pdf_data_get_df

PDF_PROCESSING_JOBTYPE = "PDF File Processing"

def llm_process_get_headers(df, token, tenant_name):
    potential_headers_row = df.iloc[0].tolist()
    potential_headers_col = df.iloc[:, 0].tolist()

    prompt = f"""
    You are an AI model specialized in data analysis. Your task is to determine the header index and table orientation from a given DataFrame.

    {potential_headers_row}
    {potential_headers_col}
    """

    llm_response = azure_llm_process(prompt, token, tenant_name)

    try:
        if llm_response is not None:
            response = json.loads(llm_response)
            orientation = response["table_orientation"]
            header_index = response["header_index"]

            if orientation == "column-wise":
                header_row = df.iloc[:, header_index].dropna().astype(str).tolist()
            elif orientation == "row-wise":
                header_row = df.iloc[header_index].dropna().astype(str).tolist()
            else:
                return [], "", -1

            return header_row, orientation, header_index
        return [], "", -1
    except Exception:
        return [], "", -1

def process_pdf_and_call_llm(token, tenant_name, attachment_id):
    try:
        pdf_data_list = []
        gosure_api = get_access_to_gosure_api(token, tenant_name)
        instance = gosure_api.get_jobinstance(attachment_id)

        if isinstance(instance, dict) and "jobs" in instance and len(instance["jobs"]) > 0:
            instance_data = instance["jobs"][0]["data"]
            attachment_data = instance_data["Attachments"]

            file_name, file_url = (
                attachment_data[0][0]["fileName"],
                attachment_data[0][0]["fileUrl"],
            )

            file_type, file_bytes = get_file_stream_by_file_url(gosure_api, file_url, get_file_type)

            pdf_table_list = extract_tables_from_pdf(file_bytes, file_name)

            for df_json in pdf_table_list:
                df_table = df_json["table_df"]

                df = df_table.apply(lambda col: col.map(
                    lambda x: x.strftime("%d-%m-%Y") if isinstance(x, datetime) else x
                ))

                pdf_json_df = json.dumps(df.to_dict(orient="records"))

                header_list, orientation, header_index = llm_process_get_headers(df, token, tenant_name)

                pdf_data_list.append({
                    "table_name": df_json["table_name"],
                    "header_row_index": header_index,
                    "orientation": orientation,
                    "header_list": json.dumps(header_list),
                    "df_json": pdf_json_df,
                })

            pdf_processing_jobtype_id = gosure_api.get_jobtype_id(PDF_PROCESSING_JOBTYPE)

            data = {"attachment_id": attachment_id, "pdf_data": pdf_data_list}
            pdf_instance = {"jobTypeId": pdf_processing_jobtype_id, "data": data}

            pdf_instance_id = gosure_api.create_jobinstance(pdf_instance)

            return {
                "status": "completed",
                "attachment_id": attachment_id,
                "pdf_instance_id": pdf_instance_id,
                "file_type": file_type,
                "file_name": file_name,
            }

    except Exception as e:
        return {"status": "error", "message": str(e)}

def get_field_names(gosure_api, jobtype_name):
    try:
        fields_response = gosure_api.get_jobtype_fields(jobtype_name)
        if fields_response != 404:
            field_lists = fields_response["orgs"][0]["Fields"]
            return [field.get("name") for field in field_lists]
        return []
    except Exception:
        return []

def process_instance_id_and_map_dataset_fields_for_pdf_table(
    token, tenant_name, jobtype_name, table_name, jobinstance_id
):
    try:
        g_api = get_access_to_gosure_api(token, tenant_name)
        instance = g_api.get_jobinstance(jobinstance_id)

        if isinstance(instance, dict) and "jobs" in instance and len(instance["jobs"]) > 0:
            instance_data = instance["jobs"][0]["data"]
            pdf_data = instance_data["pdf_data"]

            df, orientation = process_pdf_data_get_df(pdf_data, table_name)

            fields = get_field_names(g_api, jobtype_name)

            response = process_pdf_content_get_fields_response(
                fields, df.columns.tolist(), token, tenant_name
            )

            return format_pdf_llm_response_into_desired_json(response)

    except Exception as e:
        return {"error": str(e)}

def extract_values_from_pdf_by_instance_id(token, tenant_name, mapped_json, table_name, jobinstance_id):
    try:
        g_api = get_access_to_gosure_api(token, tenant_name)
        instance = g_api.get_jobinstance(jobinstance_id)

        if isinstance(instance, dict) and "jobs" in instance and len(instance["jobs"]) > 0:
            instance_data = instance["jobs"][0]["data"]
            pdf_data = instance_data["pdf_data"]

            df, orientation = process_pdf_data_get_df(pdf_data, table_name)

            if df is not None:
                extracted_json_data = process_df_get_json_data(df, orientation)
                mapped_output = map_data(extracted_json_data, mapped_json)
                return convert_date_field_iso_format(mapped_output)

        return "table name is invalid"

    except Exception:
        return None