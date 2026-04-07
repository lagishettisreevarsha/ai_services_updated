from io import BytesIO
import pdfplumber
import pandas as pd
import urllib.parse
import numpy as np
import json
from datetime import datetime
from dateutil import parser
import concurrent.futures

from src2.azure.ai_search import azure_llm_process
from src2.file_mapping.excel_extraction import get_file_type
from src2.config import MONGO_URL, get_env_value
from openai import AzureOpenAI


def llm_process_get_headers(df, token, tenant_name):
    potential_headers_row = df.iloc[0].tolist()
    potential_headers_col = df.iloc[:, 0].tolist()

    prompt = f"""
    You are an AI model specialized in data analysis. Your task is to determine the header index and table orientation from a given DataFrame.

    ### Input Details:
    - Potential Column Headers (First Row):
    {potential_headers_row}
    - Potential Row Headers (First Column):
    {potential_headers_col}

    ### Task:
    1. Identify the header index:
    - At least 80% values must be non-null
    - Headers should not contain actual data values

    2. Determine table orientation:
    - row-wise
    - column-wise

    ### Output:
    {{
        header_index = index
        table_orientation = row-wise | column-wise
    }}
    """

    llm_response = azure_llm_process(prompt, token, tenant_name)

    try:
        header_row = None

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
        else:
            return [], "", -1

    except Exception:
        return [], "", -1


def get_file_stream_by_file_url(g_api, fileurl):
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


def get_field_names(gosure_api, jobtype_name):
    try:
        fields_response = gosure_api.get_jobtype_fields(jobtype_name)

        if fields_response != 404:
            field_lists = fields_response["orgs"][0]["Fields"]
            field_names = [field.get("name") for field in field_lists]
            return field_names
        else:
            return []
    except Exception:
        return []


def chunk_fields(fields, batch_size=15):
    for i in range(0, len(fields), batch_size):
        yield fields[i: i + batch_size]


def extract_fields_values_from_pdf_table(fields_batch, excel_content, token, tenant_name):
    AZURE_OPENAI_ENDPOINT = get_env_value(MONGO_URL, "AZURE_OPENAI_ENDPOINT", tenant_name=tenant_name, token=token)
    AZURE_OPENAI_API_KEY = get_env_value(MONGO_URL, "AZURE_OPENAI_API_KEY", tenant_name=tenant_name, token=token)
    AZURE_OPENAI_API_VERSION = get_env_value(MONGO_URL, "AZURE_OPENAI_API_VERSION", tenant_name=tenant_name, token=token)
    LLM_MODEL = get_env_value(MONGO_URL, "LLM_MODEL", tenant_name=tenant_name, token=token)

    prompt = f"""
    Fields: {fields_batch}
    Headers: {excel_content}
    """

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

    if not fields:
        return []

    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_batch = {
            executor.submit(extract_fields_values_from_pdf_table, batch, content, token, tenant_name): batch
            for batch in chunk_fields(fields)
        }

        for future in concurrent.futures.as_completed(future_to_batch):
            extracted_data = future.result()
            all_extracted_data.append(extracted_data)

    return all_extracted_data


def format_pdf_llm_response_into_desired_json(extracted_data):
    combined_dict = {}

    for json_string in extracted_data:
        parsed_json = json.loads(json_string)
        combined_dict.update(parsed_json)

    return combined_dict


def process_map_json_pdf_data(g_api, jobtype_name, header_list, orientation, token, tenant_name):
    list_of_field = get_field_names(g_api, jobtype_name)

    if header_list != [] and orientation != "":
        json_response = process_pdf_content_get_fields_response(
            list_of_field, header_list, token, tenant_name
        )

        fields_response = format_pdf_llm_response_into_desired_json(json_response)

        return fields_response


def process_and_map_pdf_data(pdf_data, table_name, g_api, jobtype_name, token, tenant_name):
    header_list = []
    orientation = ""

    for data in pdf_data:
        if data["table_name"] == table_name:
            header_list = data["header_list"]
            orientation = data["orientation"]

    if header_list == [] and orientation == "":
        return "table name is invalid"
    else:
        return process_map_json_pdf_data(
            g_api, jobtype_name, header_list, orientation, token, tenant_name
        )


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

    for index, row in df_.iterrows():
        row_dict = row.to_dict()
        extracted_json_data.append(row_dict)

    return extracted_json_data


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


def check_value_and_convert_data(json):
    json_dict = {}

    for key, values in json.items():
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