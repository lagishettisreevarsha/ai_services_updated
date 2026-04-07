import logging
import json
from typing import List, Dict

from src.models.rag_models import ContextChunk, Result, StructuredResponse
from src.config import get_env_value, MONGO_URL
from src.helper.azure_openai_helper import (process_search_results, convert_to_json, generate_chat_completion)

logger = logging.getLogger(__name__)


def compliance_check(content: str,question: str,api_version: str,model: str) -> StructuredResponse:
    try:
        try:
            prompt = f"""
            Your task is to evaluate the following content against the given question.

            Return ONLY JSON in this format:
            {{
                "answer": "Yes/No/N/A",
                "reason": "text"
            }}

            Content:
            {content}

            Question:
            {question}
            """
        except Exception as e:
            raise Exception(str(e))

        try:
            response = generate_chat_completion(
                messages=[{"role": "user", "content": prompt}],
                api_version=api_version,
                model=model
            )
        except Exception as e:
            raise Exception(str(e))

        if not response:
            return StructuredResponse(answer="N/A", reason="")

        try:
            parsed = json.loads(response)
        except Exception as e:
            logger.error(str(e))
            return StructuredResponse(answer="N/A", reason="Parsing failed")

        try:
            return StructuredResponse(answer=parsed.get("answer", "N/A"),reason=parsed.get("reason", ""))
        except Exception as e:
            raise Exception(str(e))

    except Exception as e:
        logger.exception(f"Compliance check failed: {e}")
        return StructuredResponse(answer="N/A", reason="")


def llm_rag_pipeline(search_results: List[Dict],question: str,token: str,tenant_name: str) -> Dict:
    try:
        try:
            api_version = get_env_value(MONGO_URL,"AZURE_OPENAI_API_VERSION",tenant_name=tenant_name,token=token)
        except Exception as e:
            raise Exception(str(e))

        try:
            model = get_env_value(MONGO_URL,"LLM_MODEL",tenant_name=tenant_name,token=token)
        except Exception as e:
            raise Exception(str(e))

        try:
            chunks, content = process_search_results(search_results)
        except Exception as e:
            raise Exception(str(e))

        try:
            response = compliance_check(content=content,question=question,api_version=api_version,model=model)
        except Exception as e:
            raise Exception(str(e))

        try:
            result = Result(question=question,answer=response.answer,reason=response.reason,context_chunks=chunks)
        except Exception as e:
            raise Exception(str(e))

        try:
            return convert_to_json(result)
        except Exception as e:
            raise Exception(str(e))

    except Exception as e:
        logger.exception(f"RAG pipeline failed: {e}")
        return {}