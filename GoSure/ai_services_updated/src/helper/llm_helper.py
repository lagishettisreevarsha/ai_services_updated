im  0port logging
from openai import AzureOpenAI
from src.config import get_env_value, MONGO_URL

def get_llm_client_initialize(endpoint: str, api_key: str, api_version: str):
    try:
        if not endpoint:
            raise ValueError("AZURE_OPENAI_ENDPOINT is not set.")
        if not api_key:
            raise ValueError("AZURE_OPENAI_API_KEY is not set.")
        if not api_version:
            raise ValueError("AZURE_OPENAI_API_VERSION is not set.")

        return AzureOpenAI(api_version=api_version, azure_endpoint=f"{endpoint}?api-version={api_version}", api_key=api_key)
    except Exception as e:
        logging.error(f"Failed to initialize Azure OpenAI client. Error: {e}")
        raise Exception(str(e))

def get_llm_client(tenant_name, token):
    try:
        endpoint = get_env_value(MONGO_URL, "AZURE_OPENAI_ENDPOINT", tenant_name=tenant_name, token=token)
        api_key = get_env_value(MONGO_URL, "AZURE_OPENAI_API_KEY", tenant_name=tenant_name, token=token)
        api_version = get_env_value(MONGO_URL, "AZURE_OPENAI_API_VERSION", tenant_name=tenant_name, token=token)
        return get_llm_client_initialize(endpoint, api_key, api_version)
    except Exception as e:
        raise Exception(str(e))

def generate_llm_response(pdf_content, question, tenant_name, token):
    try:
        model = get_env_value(MONGO_URL, "LLM_MODEL", tenant_name=tenant_name, token=token)
        client = get_llm_client(tenant_name, token)

        prompt = f"""
    You are an intelligent assistant.
    Answer only from the given context.
    If no answer is found, return N/A.

    Context:
    {pdf_content}

    Question:
    {question}
    """
        response = client.chat.completions.create(messages=[{"role": "user", "content": prompt}], model=model)
        return response.choices[0].message.content if response.choices else "N/A"
    
    except Exception as e:
        logging.error(f"LLM response generation failed: {e}")
        raise Exception(str(e))