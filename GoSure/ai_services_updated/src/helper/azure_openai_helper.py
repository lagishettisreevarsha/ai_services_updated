import os
import logging
from typing import List, Dict, Tuple

from openai import AzureOpenAI
from src.models.rag_models import ContextChunk, Result

logger = logging.getLogger(__name__)


def get_llm_client(api_version: str):
    try:
        try:
            api_key = os.getenv("OPENAI_API_KEY")
            endpoint = os.getenv("OPENAI_API_BASE")
        except Exception as e:
            raise Exception(str(e))

        if not api_key or not endpoint:
            raise ValueError("Azure OpenAI credentials missing")

        try:
            client = AzureOpenAI(api_key=api_key,api_version=api_version,azure_endpoint=endpoint)
        except Exception as e:
            raise Exception(str(e))

        return client

    except Exception as e:
        logger.error(f"LLM client init failed: {e}")
        raise Exception(str(e))


def generate_chat_completion(
    messages: List[Dict],
    api_version: str,
    model: str
) -> str:
    try:
        try:
            client = get_llm_client(api_version)
        except Exception as e:
            raise Exception(str(e))

        try:
            response = client.chat.completions.create(model=model,messages=messages)
        except Exception as e:
            raise Exception(str(e))

        try:
            return response.choices[0].message.content if response.choices else ""
        except Exception as e:
            raise Exception(str(e))

    except Exception as e:
        logger.error(f"Chat completion failed: {e}")
        return ""


def process_search_results(search_results: List[Dict]) -> Tuple[List[ContextChunk], str]:
    try:
        chunks = []
        content_chunks = []

        for result in search_results:
            try:
                chunks.append(
                    ContextChunk(
                        chunk_id=result.get("chunk_id"),
                        title=result.get("title"),
                        score=float(result.get("@search.score", 0))
                    )
                )
            except Exception as e:
                logger.exception(str(e))

            try:
                if result.get("chunk"):
                    content_chunks.append(result["chunk"])
            except Exception as e:
                logger.exception(str(e))

        return chunks, " ".join(content_chunks)

    except Exception as e:
        logger.exception(f"Error processing search results: {e}")
        return [], ""


def convert_to_json(result: Result) -> Dict:
    try:
        try:
            response = {
                "question": result.question,
                "answer": result.answer,
                "reason": result.reason,
                "context_chunks": [
                    {
                        "chunk_id": chunk.chunk_id,
                        "title": chunk.title,
                        "score": chunk.score
                    }
                    for chunk in result.context_chunks
                ],
            }
        except Exception as e:
            raise Exception(str(e))

        return response

    except Exception as e:
        logger.exception(f"Conversion to JSON failed: {e}")
        return {}