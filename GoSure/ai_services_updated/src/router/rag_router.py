from urllib import response
from fastapi import APIRouter, HTTPException, Request
from pydantic import ValidationError
from src.models.rag_models import RagRequest
from src.services.rag_service import handle_rag_request


router = APIRouter()

@router.post("/rag/question_evaluation2")
async def rag_question_evaluation(dto: RagRequest, request: Request):
    try:
        token = request.headers.get("Authorization")
        if not token:
            raise HTTPException(status_code=400, detail="Token is required")
        return handle_rag_request(dto, token)
    
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.errors())
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))