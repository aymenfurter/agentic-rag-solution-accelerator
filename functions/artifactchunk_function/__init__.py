import azure.functions as func
import os
import json
import logging
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.models import QueryType, VectorizedQuery

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Processing artifact chunk search request")
    
    try:
        # Get request payload
        body = req.get_json()
        payload = body.get("payload", {})
        
        # Extract search parameters
        search_text = payload.get("searchText", "*")
        filter_expr = payload.get("filter")
        semantic_ranking = payload.get("semanticRanking", False)
        question_rewriting = payload.get("questionRewriting", False)
        top_k = min(payload.get("topK", 5), 50)  # Limit max results
        
        # Initialize search client
        search_client = SearchClient(
            endpoint=os.environ["SEARCH_ENDPOINT"],
            index_name=os.environ["SEARCH_INDEX_NAME"],
            credential=AzureKeyCredential(os.environ["SEARCH_ADMIN_KEY"])
        )
        
        # Build search options
        search_options = {
            "filter": f"docType eq 'chunk' {f'and {filter_expr}' if filter_expr else ''}",
            "top": top_k,
            "select": "id,content,timestamp,artifactId,fileName,segmentTimestamp,headers",
            "include_total_count": True
        }
        
        if semantic_ranking:
            search_options.update({
                "query_type": QueryType.SEMANTIC,
                "query_language": "en-us",
                "semantic_configuration_name": "default"
            })

        # If question rewriting is enabled, we could enhance the query
        # This would typically be done via an LLM call to rephrase the query
        if question_rewriting:
            # TODO: Implement question rewriting using Azure AI Services
            pass
            
        # Perform search
        results = search_client.search(
            search_text=search_text,
            **search_options
        )
        
        # Format results
        docs = []
        for result in results:
            doc = {
                "id": result["id"],
                "content": result.get("content"),
                "timestamp": result.get("timestamp"),
                "artifactId": result.get("artifactId"),
                "fileName": result.get("fileName"),
                "score": result.get("@search.score")
            }
            
            # Add optional fields if present
            if "segmentTimestamp" in result:
                doc["segmentTimestamp"] = result["segmentTimestamp"]
            if "headers" in result:
                doc["headers"] = result["headers"]
                
            docs.append(doc)
        
        return func.HttpResponse(
            json.dumps({
                "results": docs,
                "count": results.get_count()
            }),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f"Error in artifactchunk_function: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )