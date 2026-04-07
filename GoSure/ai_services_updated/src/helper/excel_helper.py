from datetime import datetime
import pandas as pd
from dotenv import load_dotenv
from werkzeug.datastructures import FileStorage
from concurrent.futures import ThreadPoolExecutor
from dateutil import parser
import json
import concurrent.futures

from src.config import MONGO_URL, get_env_value
from openai import AzureOpenAI
from src.file_mapping.excel_extraction import (
    extract_and_process_excel_and_return_headers,
    extract_excel_data_into_dataframe,
)

load_dotenv()


def get_field_names(gosure_api, jobtype_name):
    try:
        fields_response = gosure_api.get_jobtype_fields(jobtype_name)

        if fields_response != 404:
            field_lists = fields_response["orgs"][0]["Fields"]
            field_names = [field.get("name") for field in field_lists]
            return field_names
        else:
            print(f"Jobtype '{jobtype_name}' is not found")
            return []
    except Exception as e:
        print(f"Jobtype '{jobtype_name}' is not found: {e}")
        return []


def chunk_fields(fields, batch_size=15):
    for i in range(0, len(fields), batch_size):
        yield fields[i: i + batch_size]


def extract_fields_values_from_excel(fields_batch, excel_content, token, tenant_name):
    prompt = f"""
    You are an expert data extractor specialized in mapping fields to their corresponding headers from Excel data.

    ### **Task:**
    - **Exact Match:** If a field name from the list exists as a header in the Excel content, return the exact header name.  
    - **Close Match:** If an exact match is not found, identify the closest matching header based on synonyms, abbreviations, variations, and context.  
    - **Missing Fields:** If no relevant match is found, return an empty string ("").  

    ### **Instructions:**
    - Prioritize semantic relevance over strict word matching.  
    - Consider abbreviations, alternate phrasing, common industry terms, and header formatting differences.  

    ### **Fields to Map:**  
    {fields_batch}  

    ### **Available Headers:**  
    {excel_content}  

    {{
        "field1": "Corresponding Header"
    }}
    """

    AZURE_OPENAI_ENDPOINT = get_env_value(MONGO_URL, "AZURE_OPENAI_ENDPOINT", tenant_name=tenant_name, token=token)
    AZURE_OPENAI_API_KEY = get_env_value(MONGO_URL, "AZURE_OPENAI_API_KEY", tenant_name=tenant_name, token=token)
    AZURE_OPENAI_API_VERSION = get_env_value(MONGO_URL, "AZURE_OPENAI_API_VERSION", tenant_name=tenant_name, token=token)
    LLM_MODEL = get_env_value(MONGO_URL, "LLM_MODEL", tenant_name=tenant_name, token=token)

    client = AzureOpenAI(
        api_version=AZURE_OPENAI_API_VERSION,
        azure_endpoint=f"{AZURE_OPENAI_ENDPOINT}?api-version={AZURE_OPENAI_API_VERSION}",
        api_key=AZURE_OPENAI_API_KEY,
    )

    chat_completion = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model=LLM_MODEL
    )

    generated_text = chat_completion.choices[0].message.content

    return generated_text


def process_pdf_content_get_fields_response(fields, content, token, tenant_name):
    all_extracted_data = []

    if not fields:
        print("Fields are empty")
        return []

    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_batch = {
            executor.submit(
                extract_fields_values_from_excel,
                batch,
                content,
                token,
                tenant_name
            ): batch
            for batch in chunk_fields(fields)
        }

        for future in concurrent.futures.as_completed(future_to_batch):
            try:
                extracted_data = future.result()
                all_extracted_data.append(extracted_data)
            except Exception as e:
                print(f"Error processing batch {future_to_batch[future]}: {e}")

    return all_extracted_data


def format_llm_response_into_desired_json(extracted_data):
    combined_dict = {}

    for json_string in extracted_data:
        parsed_json = json.loads(json_string)
        combined_dict.update(parsed_json)

    return combined_dict


def map_data(table_data, mapped_json_template):
    mapped_json_template = json.loads(mapped_json_template)

    mapped_output = []

    for record in table_data:
        mapped_record = {}

        for key, value in mapped_json_template.items():
            if value == "":
                mapped_record[key] = ""
            else:
                mapped_record[key] = record.get(value, "")

        mapped_output.append(mapped_record)

    return mapped_output


def get_date_format(date_str):
    try:
        if isinstance(date_str, str) and date_str.strip().isdigit():
            return date_str

        parsed_date = parser.parse(date_str)
        return parsed_date
    except ValueError:
        return None


def convert_to_date_format(date_str):
    dt = get_date_format(date_str)

    if isinstance(dt, str):
        return dt
    elif dt:
        return dt.strftime("%m/%d/%Y")
    else:
        return date_str


def is_name_string(value):
    return not any(char.isdigit() for char in value)


def convert_date_field_iso_format(json_list):
    processed_list = []

    for json_data in json_list:
        json_dict = {}

        for key, value in json_data.items():
            if isinstance(value, str):
                if value.strip() == "":
                    json_dict[key] = value
                elif is_name_string(value):
                    json_dict[key] = value
                else:
                    iso_value = convert_to_date_format(value)
                    if iso_value != value:
                        json_dict[key] = iso_value
                    else:
                        json_dict[key] = value
            else:
                json_dict[key] = value

        processed_list.append(json_dict)

    return processed_list