from io import BytesIO
import pdfplumber
import pandas as pd
import urllib.parse
import numpy as np
from datetime import datetime
import json
from dateutil import parser
import concurrent.futures
from openai import AzureOpenAI
from src.config import MONGO_URL, get_env_value

def get_file_stream_by_file_url(g_api, fileurl, get_file_type):
    file_type = get_file_type(fileurl)
    decoded_url = urllib.parse.unquote(fileurl)
    file_bytes = g_api.get_attachment(decoded_url)
    return file_type, file_bytes

def is_page_scanned(page):
    text = page.extract_text()
    if text and text.strip():
        return False
    images = page.images
    if images:
        return True
    return False

def extract_tables_from_pdf(pdf_path, filename='Sample_Pdf'):
    input_file_byte = BytesIO(pdf_path)
    scanned_pages = []
    all_tables_info = []

    with pdfplumber.open(input_file_byte) as pdf:
        for i, page in enumerate(pdf.pages):
            scanned = is_page_scanned(page)
            scanned_pages.append(scanned)

            tables = page.extract_tables()
            for table_id, table in enumerate(tables):
                if not table:
                    continue
                df = pd.DataFrame(table)
                df = df.map(lambda x: np.nan if pd.isna(x) or str(x).strip() == "" else x)
                df.dropna(how="all", axis=0, inplace=True)
                df.dropna(how="all", axis=1, inplace=True)
                df = df.where(pd.notna(df), "")
                df = df.reset_index(drop=True)

                all_tables_info.append({
                    "page_number": i + 1,
                    "is_scanned": scanned,
                    "table_name": f"{filename}_Page_{i + 1}_Table_{table_id + 1}",
                    "table_df": df
                })

    return all_tables_info

def chunk_fields(fields, batch_size=15):
    for i in range(0, len(fields), batch_size):
        yield fields[i:i + batch_size]

def extract_fields_values_from_pdf_table(fields_batch, excel_content, token, tenant_name):
    AZURE_OPENAI_ENDPOINT = get_env_value(MONGO_URL, "AZURE_OPENAI_ENDPOINT", tenant_name=tenant_name, token=token)
    AZURE_OPENAI_API_KEY = get_env_value(MONGO_URL, "AZURE_OPENAI_API_KEY", tenant_name=tenant_name, token=token)
    AZURE_OPENAI_API_VERSION = get_env_value(MONGO_URL, "AZURE_OPENAI_API_VERSION", tenant_name=tenant_name, token=token)
    LLM_MODEL = get_env_value(MONGO_URL, "LLM_MODEL", tenant_name=tenant_name, token=token)

    prompt = f"{fields_batch} {excel_content}"

    client = AzureOpenAI(
        api_version=AZURE_OPENAI_API_VERSION,
        azure_endpoint=f"{AZURE_OPENAI_ENDPOINT}?api-version={AZURE_OPENAI_API_VERSION}",
        api_key=AZURE_OPENAI_API_KEY,
    )

    chat_completion = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model=LLM_MODEL
    )

    return chat_completion.choices[0].message.content

def process_pdf_content_get_fields_response(fields, content, token, tenant_name):
    all_extracted_data = []

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = {
            executor.submit(extract_fields_values_from_pdf_table, batch, content, token, tenant_name): batch
            for batch in chunk_fields(fields)
        }

        for future in concurrent.futures.as_completed(futures):
            try:
                all_extracted_data.append(future.result())
            except Exception:
                pass

    return all_extracted_data

def format_pdf_llm_response_into_desired_json(extracted_data):
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

def check_value_and_convert_data(json_data):
    json_dict = {}
    for key, values in json_data.items():
        value = str(values)
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
    return json_dict

def convert_date_field_iso_format(json_list):
    processed_list = []
    for json_data in json_list:
        json_dict = check_value_and_convert_data(json_data)
        processed_list.append(json_dict)
    return processed_list

def process_df_get_json_data(df, orientation):
    header_row = 0

    if orientation == "column-wise":
        df = df.map(lambda x: np.nan if pd.isna(x) or str(x).strip() == "" else x)
        df.dropna(how="all", axis=0, inplace=True)
        df.dropna(how="all", axis=1, inplace=True)
        df = df.where(pd.notna(df), "")

        transpose_df = df.T.reset_index(drop=True)
        df_ = transpose_df.loc[:, ~transpose_df.columns.duplicated()]
        df_.columns = df_.iloc[header_row]
        df_ = df_.iloc[header_row + 1:].reset_index(drop=True)

    else:
        df.columns = df.iloc[header_row]
        df_ = df.iloc[header_row + 1:].reset_index(drop=True)

    extracted_json_data = []
    for _, row in df_.iterrows():
        extracted_json_data.append(row.to_dict())

    return extracted_json_data

def process_pdf_data_get_df(pdf_data, table_name):
    data_list = []
    orientation = ""
    header_row = ""

    for data in pdf_data:
        if data["table_name"] == table_name:
            df_json = data["df_json"]
            orientation = data["orientation"]
            header_row = data["header_row_index"]
            df_list = json.loads(df_json)
            data_list.append(df_list)

    if data_list != [] and orientation != "" and header_row != "":
        extracted_json_data_ = data_list[0]
        df = pd.DataFrame(extracted_json_data_)
        return df, orientation
    else:
        return None, None