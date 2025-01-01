# /artifact_function/__init__.py
import azure.functions as func
import os
import json
import logging
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.models import QueryType

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Processing artifact search request")
    
    try:
        # Get request payload
        body = req.get_json()
        payload = body.get("payload", {})
        
        # Extract search parameters
        search_text = payload.get("searchText", "*")
        filter_expr = payload.get("filter")  # OData filter
        semantic_ranking = payload.get("semanticRanking", False)
        top_k = min(payload.get("topK", 5), 50)  # Limit max results
        
        # Initialize search client
        search_client = SearchClient(
            endpoint=os.environ["SEARCH_ENDPOINT"],
            index_name=os.environ["SEARCH_INDEX_NAME"],
            credential=AzureKeyCredential(os.environ["SEARCH_ADMIN_KEY"])
        )
        
        # Build search options
        search_options = {
            "filter": f"docType eq 'artifact' {f'and {filter_expr}' if filter_expr else ''}",
            "top": top_k,
            "select": "id,timestamp,summary,artifactId,fileName",
            "include_total_count": True
        }
        
        if semantic_ranking:
            search_options.update({
                "query_type": QueryType.SEMANTIC,
                "query_language": "en-us",
                "semantic_configuration_name": "default"
            })
            
        # Perform search
        results = search_client.search(
            search_text=search_text,
            **search_options
        )
        
        # Format results
        docs = []
        for result in results:
            docs.append({
                "id": result["id"],
                "timestamp": result.get("timestamp"),
                "summary": result.get("summary"),
                "artifactId": result.get("artifactId"),
                "fileName": result.get("fileName"),
                "score": result.get("@search.score")
            })
        
        return func.HttpResponse(
            json.dumps({
                "results": docs,
                "count": results.get_count()
            }),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f"Error in artifact_function: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )