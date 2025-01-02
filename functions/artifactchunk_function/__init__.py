import json
import logging
import os
import azure.functions as func
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
        question_rewriting = payload.get("questionRewriting", False)
        top_k = min(payload.get("topK", 5), 50)
        
        # Get config to find index name
        blob_client = BlobServiceClient.from_connection_string(os.environ["STORAGE_CONNECTION_STRING"])
        container_client = blob_client.get_container_client("schemas")
        config_blob = container_client.get_blob_client("user_config.json")
        schema_json = json.loads(config_blob.download_blob().readall())
        
        # Initialize search client with static index name
        search_client = SearchClient(
            endpoint=os.environ["SEARCH_ENDPOINT"],
            index_name="chunks",
            credential=AzureKeyCredential(os.environ["SEARCH_ADMIN_KEY"])
        )
        
        # Build search options with chunk-specific fields
        search_options = {
            "filter": f"chunk_docType eq 'chunk' {f'and {filter_expr}' if filter_expr else ''}",
            "top": top_k,
            "select": "chunk_id,chunk_content,chunk_timestamp,chunk_fileName",
            "include_total_count": True
        }
        
        if semantic_ranking:
            search_options.update({
                "query_type": QueryType.SEMANTIC,
                "query_language": "en-us",
                "semantic_configuration_name": "chunk-semantic"
            })

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
                "id": result["chunk_id"],
                "content": result.get("chunk_content"),
                "timestamp": result.get("chunk_timestamp"),
                "fileName": result.get("chunk_fileName"),  # Use consistent field name
                "score": result.get("@search.score")
            }
            
            if "segmentTimestamp" in result:
                doc["segmentTimestamp"] = result["segmentTimestamp"]
            if "headers" in result:
                doc["headers"] = result["headers"]
                
            docs.append(doc)
        
        # Send results to output queue
        output_message = {
            "Value": {
                "results": docs,
                "count": results.get_count()
            },
            "CorrelationId": correlation_id
        }
        outputQueueItem.set(json.dumps(output_message))
        
    except Exception as e:
        logging.error(f"Error in artifactchunk_function: {str(e)}")
        # Send error to output queue
        error_message = {
            "error": str(e),
            "CorrelationId": correlation_id
        }        
        outputQueueItem.set(json.dumps(error_message))