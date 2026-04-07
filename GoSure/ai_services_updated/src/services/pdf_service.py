from src.helper.pdf_helper import (
    llm_process_get_headers,
    get_file_stream_by_file_url,
    extract_tables_from_pdf,
    get_field_names,
    process_pdf_content_get_fields_response,
    format_pdf_llm_response_into_desired_json,
    process_map_json_pdf_data,
    process_and_map_pdf_data,
    process_pdf_data_get_df,
    process_df_get_json_data,
    map_data,
    convert_date_field_iso_format
)

from src.gosure_initialization.gosure_access import get_access_to_gosure_api
from datetime import datetime
import json

PDF_PROCESSING_JOBTYPE = "PDF File Processing"


def process_pdf_and_call_llm(token, tenant_name, attachment_id):
    try:
        pdf_data_list = []
        gosure_api = get_access_to_gosure_api(token, tenant_name)
        instance = gosure_api.get_jobinstance(attachment_id)

        if isinstance(instance, dict) and "jobs" in instance and isinstance(instance["jobs"], list) and len(instance["jobs"]) > 0:
            instance_data = instance["jobs"][0]["data"]
            attachment_data = instance_data["Attachments"]

            file_name, file_url = (
                attachment_data[0][0]["fileName"],
                attachment_data[0][0]["fileUrl"],
            )

            file_type, file_bytes = get_file_stream_by_file_url(gosure_api, file_url)
            pdf_table_list = extract_tables_from_pdf(file_bytes, file_name)

            for i, df_json in enumerate(pdf_table_list):
                df_table = df_json["table_df"]

                df = df_table.apply(lambda col: col.map(
                    lambda x: (
                        x.strftime("%d-%m-%Y")
                        if isinstance(x, datetime)
                        else x
                    )
                ))

                pdf_json_df = json.dumps(df.to_dict(orient="records"))

                header_list, orientation, header_index = llm_process_get_headers(
                    df, token, tenant_name
                )

                pdf_data_list.append({
                    "table_name": df_json['table_name'],
                    "header_row_index": header_index,
                    "orientation": orientation,
                    "header_list": json.dumps(header_list),
                    "df_json": pdf_json_df,
                })

            pdf_processing_jobtype_id = gosure_api.get_jobtype_id(
                PDF_PROCESSING_JOBTYPE
            )

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
        return {"status": "error", "message": f"Processing failed due to: {str(e)}"}


def process_instance_id_and_map_dataset_fields_for_pdf_table(
    token, tenant_name, jobtype_name, table_name, jobinstance_id
):
    try:
        g_api = get_access_to_gosure_api(token, tenant_name)
        instance = g_api.get_jobinstance(jobinstance_id)

        if isinstance(instance, dict) and "jobs" in instance and isinstance(instance["jobs"], list) and len(instance["jobs"]) > 0:
            instance_data = instance["jobs"][0]["data"]
            pdf_data = instance_data["pdf_data"]

            return process_and_map_pdf_data(
                pdf_data, table_name, g_api, jobtype_name, token, tenant_name
            )

    except Exception as e:
        return {"error": str(e)}


def delete_table_data_from_instance_id_pdf(
    token,
    tenant_name,
    jobinstance_id,
    table_name,
):

    gosure_api = get_access_to_gosure_api(token, tenant_name)
    instance = gosure_api.get_jobinstance(jobinstance_id)

    if isinstance(instance, dict) and "jobs" in instance and isinstance(instance["jobs"], list) and len(instance["jobs"]) > 0:
        instance_data = instance["jobs"][0]["data"]
        pdf_data = instance_data["pdf_data"]

        table_names = [x["table_name"] for x in pdf_data]

        if table_name in table_names:
            updated_pdf_data = list(
                filter(lambda x: x["table_name"] != table_name, pdf_data)
            )

            instance_data["pdf_data"] = updated_pdf_data

            data = {"data": instance_data}

            gosure_api.update_jobinstance(jobinstance_id, data)

            print("deleted data in instances and updated sucessfully....")

            resp = "deleted data in instances and updated sucessfully...."
            return resp
        else:
            resp = f"{table_name} -  is not found"
            return resp


def get_table_list_from_id_pdf(token, tenant_name, ins_id):
    table_list = []

    gosure_api = get_access_to_gosure_api(token, tenant_name)
    instance = gosure_api.get_jobinstance(ins_id)

    if isinstance(instance, dict) and "jobs" in instance and isinstance(instance["jobs"], list) and len(instance["jobs"]) > 0:
        instance_data = instance["jobs"][0]["data"]
        pdf_data = instance_data["pdf_data"]

        for data in pdf_data:
            table_name = data["table_name"]
            if table_name not in table_list:
                table_list.append(table_name)

        return table_list


def extract_values_from_pdf_by_instance_id(
    token,
    tenant_name,
    mapped_json,
    table_name,
    jobinstance_id,
):
    try:
        g_api = get_access_to_gosure_api(token, tenant_name)
        instance = g_api.get_jobinstance(jobinstance_id)

        if isinstance(instance, dict) and "jobs" in instance and isinstance(instance["jobs"], list) and len(instance["jobs"]) > 0:
            instance_data = instance["jobs"][0]["data"]
            pdf_data = instance_data["pdf_data"]

            df, orientation = process_pdf_data_get_df(pdf_data, table_name)

            if df is not None and orientation is not None:
                extracted_json_data = process_df_get_json_data(df, orientation)
                mapped_output = map_data(extracted_json_data, mapped_json)
                converted_json = convert_date_field_iso_format(mapped_output)

                return converted_json
            else:
                return "table name is invalid"
        else:
            return "Error in instance data"

    except Exception as e:
        print(f"error {e}")