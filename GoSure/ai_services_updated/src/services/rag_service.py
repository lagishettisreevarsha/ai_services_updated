from src.helper.llm_helper import generate_llm_response
from src.helper.search_helper import get_search_results
from src.config import get_env_value, MONGO_URL


def build_filter_query(filters: dict):
    try:
        return " and ".join([f"{field} eq '{value}'" for field, value in filters.items() if value])
    except Exception as e:
        raise Exception(str(e))

def handle_rag_request(request, token):
    try:
        question = request.question
        tenant_name = None

        filters = {
            "metadata_org_id": request.org_id,
            "metadata_jobinstance_id": request.jobinstance_id,
            "metadata_attachment_id": request.attachment_id,
        }

        filter_query = build_filter_query(filters)

        try:
            min_score_threshold = int(request.min_score_threshold) if request.min_score_threshold else int(
                get_env_value(MONGO_URL, "SEARCH_MIN_SCORE_THRESHOLD", env_key_value="string_value", tenant_name=tenant_name, token=token)
            )
        except Exception as e:
            raise Exception(str(e))

        try:
            search_results = get_search_results(question, filter_query, min_score_threshold, token, tenant_name)
        except Exception as e:
            raise Exception(str(e))

        try:
            chunk_content = "".join([chunk["chunk"] for chunk in search_results])
        except Exception as e:
            raise Exception(str(e))

        try:
            llm_answer = generate_llm_response(chunk_content, question, tenant_name, token)
        except Exception as e:
            raise Exception(str(e))

        return {"question": question, "answer": llm_answer}
    except Exception as e:
        raise Exception(str(e))