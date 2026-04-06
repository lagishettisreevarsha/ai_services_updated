from fastapi import HTTPException


def validate_token(token, tenant):
    try:
        if not token and not tenant:
            raise HTTPException(status_code=400, detail="Tenant name or Access Token is required")
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def convert_to_int(value):
    try:
        if value and str(value).isdigit():
            return int(value)
        return value
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))