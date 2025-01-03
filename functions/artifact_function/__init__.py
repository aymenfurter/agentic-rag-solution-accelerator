# /artifact_function/__init__.py
import azure.functions as func
import os
import json
import logging
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.models import QueryType
from azure.storage.blob import BlobServiceClient

def main(msg: func.QueueMessage, outputQueueItem: func.Out[str]) -> None:
    logging.info('Python queue trigger function processed a queue item')
    
    try:
        # Parse the queue message
        message_payload = json.loads(msg.get_body().decode('utf-8'))
        correlation_id = message_payload.get('CorrelationId')
        payload = message_payload.get('payload', {})
        
        # Extract search parameters
        search_text = payload.get("searchText", "*")
        filter_expr = payload.get("filter")
        semantic_ranking = payload.get("semanticRanking", False)
        top_k = min(payload.get("topK", 5), 50)
        
        # Get config to find index name
        blob_client = BlobServiceClient.from_connection_string(os.environ["STORAGE_CONNECTION_STRING"])
        container_client = blob_client.get_container_client("schemas")
        config_blob = container_client.get_blob_client("user_config.json")
        schema_json = json.loads(config_blob.download_blob().readall())
        
        # Initialize search client
        search_client = SearchClient(
            endpoint=os.environ["SEARCH_ENDPOINT"],
            index_name="artifacts",  # Use static name
            credential=AzureKeyCredential(os.environ["SEARCH_ADMIN_KEY"])
        )
        
        # Build dynamic field selection from config
        standard_fields = ["id", "content", "docType", "timestamp", "fileName"]
        custom_fields = [f["name"] for f in schema_json.get("fields", [])]
        all_fields = standard_fields + custom_fields
        
        # Force limit to 5 results max
        top_k = min(5, top_k)
        search_options = {
            "filter": f"docType eq 'artifact' {f'and {filter_expr}' if filter_expr else ''}",
            "top": top_k,
            "select": ",".join(all_fields),
            "include_total_count": True
        }
        
        if semantic_ranking:
            search_options.update({
                "query_type": QueryType.SEMANTIC,
                "query_language": "en-us",
                "semantic_configuration_name": "artifact-semantic"
            })
            
        # Perform search
        results = search_client.search(
            search_text=search_text,
            **search_options
        )
        
        # Format results with dynamic fields and limit content size
        docs = []
        max_content_size = 1000  # Limit content field size
        
        for result in results:
            doc = {
                field: result.get(field) 
                for field in all_fields 
                if field in result
            }
            # Trim content if too large
            if 'content' in doc and len(doc['content']) > max_content_size:
                doc['content'] = doc['content'][:max_content_size] + '...'
            
            doc["score"] = result.get("@search.score")
            docs = docs[:5]  # Ensure max 5 docs
            docs.append(doc)

        output_message = {
            "Value": {
                "results": docs,
                "count": results.get_count()
            },
            "CorrelationId": correlation_id
        }
        
        # Check if output message is too large
        message_size = len(json.dumps(output_message).encode('utf-8'))
        if message_size > 60000:  # Leave buffer below 64KB limit
            # Truncate results if needed
            while message_size > 60000 and docs:
                docs.pop()
                output_message["Value"]["results"] = docs
                message_size = len(json.dumps(output_message).encode('utf-8'))
                
        outputQueueItem.set(json.dumps(output_message))
        
    except Exception as e:
        logging.error(f"Error in artifact_function: {str(e)}")
        # Send error to output queue
        error_message = {
            "error": str(e),
            "CorrelationId": correlation_id
        }
        outputQueueItem.set(json.dumps(error_message))