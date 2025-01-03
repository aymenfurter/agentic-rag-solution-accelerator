# /artifact_function/__init__.py
import azure.functions as func
import os
import json
import logging
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.models import QueryType
from azure.storage.blob import BlobServiceClient

def check_message_size(message):
    """Check if message size is within Azure Queue limit"""
    return len(json.dumps(message).encode('utf-8')) <= 60000  # Buffer below 64KB limit

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
        
        # Build search options with dynamic field selection
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
        
        # Format results with size limit checking
        docs = []
        total_count = results.get_count()
        
        for result in results:
            doc = {
                field: (result.get(field)[:1000] if field == 'content' and isinstance(result.get(field), str) 
                       else result.get(field))
                for field in all_fields 
                if field in result
            }
            doc["score"] = result.get("@search.score")
            
            # Test if adding this doc would exceed size limit
            test_message = {
                "Value": {
                    "results": docs + [doc],
                    "count": total_count
                },
                "CorrelationId": correlation_id
            }
            
            if check_message_size(test_message):
                docs.append(doc)
            else:
                logging.warning(f"Skipping document due to size limit. Current docs: {len(docs)}")
                break
        
        docs_as_string = json.dumps(docs)
        output_message = {
            "Value": docs_as_string,
            "CorrelationId": correlation_id
        }
        outputQueueItem.set(json.dumps(output_message))
        
    except Exception as e:
        logging.error(f"Error in artifact_function: {str(e)}")
        # Send error to output queue
        error_message = {
            "error": str(e),
            "CorrelationId": correlation_id
        }
        outputQueueItem.set(json.dumps(error_message))