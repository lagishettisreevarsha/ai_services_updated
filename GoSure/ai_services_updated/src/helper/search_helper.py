from src.helper.search_helper import search 

def get_search_results(question, filter_query, min_score, token, tenant_name):
    try:
        return search(question, filter_query, min_score, token, tenant_name)
    
    except Exception as e:
        raise Exception(str(e))