from src.helper.excel_helper import (
    get_field_names,
    process_pdf_content_get_fields_response,
    format_llm_response_into_desired_json,
    extract_and_process_excel_and_return_headers,
    extract_excel_data_into_dataframe,
    map_data,
    convert_date_field_iso_format
)



from src.gosure_initialization.gosure_access import get_access_to_gosure_api
import json


def get_field_values_from_excel_content(
    token,
    tenant_name,
    jobtype_name,
    file_path,
    sheet_name,
):
    g_api = get_access_to_gosure_api(token, tenant_name)

    list_of_field = get_field_names(g_api, jobtype_name)

    response, table_orientation = extract_and_process_excel_and_return_headers(
        file_path, sheet_name
    )

    if response != []:
        header_rows = response[0]
        list_of_headers = response[1]

        json_response = process_pdf_content_get_fields_response(
            list_of_field, list_of_headers, token, tenant_name
        )

        fields_response = format_llm_response_into_desired_json(json_response)

        return fields_response, list_of_headers, header_rows, table_orientation
    else:
        return None, None, None, None


def get_field_from_excel(
    file_path, sheet_name, header_row, mapped_json, table_orientation
):
    header_row = int(header_row)

    df = extract_excel_data_into_dataframe(file_path, sheet_name)

    if table_orientation == "Column-wise headers":
        df = df.set_index(header_row)

        transpose_df = df.T.reset_index(drop=True)

        transpose_df = transpose_df.loc[:, ~transpose_df.columns.duplicated()]

        extracted_json_data = transpose_df.to_dict(orient="records")

    else:
        df.columns = df.iloc[header_row]

        df = df.iloc[header_row + 1:].reset_index(drop=True)

        extracted_json_data = []

        for index, row in df.iterrows():
            row_dict = row.to_dict()
            extracted_json_data.append(row_dict)

    mapped_output = map_data(extracted_json_data, mapped_json)

    converted_json = convert_date_field_iso_format(mapped_output)

    return converted_json