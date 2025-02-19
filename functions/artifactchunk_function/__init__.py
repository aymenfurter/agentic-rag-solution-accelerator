import json
import logging
import os
import azure.functions as func
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.models import QueryType
from azure.storage.blob import BlobServiceClient

def check_message_size(message):
    """Check if message size is within Azure Queue limit"""
    return len(json.dumps(message).encode('utf-8')) <= 60000  # Buffer below 64KB limit

def search_chunk (payload):
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

    return results


def main(msg: func.QueueMessage, outputQueueItem: func.Out[str]) -> None:
    logging.info('Python queue trigger function processed a queue item')
    
    try:
        # Parse the queue message
        message_payload = json.loads(msg.get_body().decode('utf-8'))
        correlation_id = message_payload.get('CorrelationId')
        payload = message_payload.get('payload', {})
        
        # Perform search
        results = search_chunk(payload)
        
        # Format results with size limit checking
        docs = []
        total_count = results.get_count()
        
        for result in results:
            doc = {
                "id": result["chunk_id"],
                "content": result.get("chunk_content", "")[:1000],  # Limit content size
                "timestamp": result.get("chunk_timestamp"),
                "fileName": result.get("chunk_fileName"),
                "score": result.get("@search.score")
            }
            
            # Add optional fields if present
            if "segmentTimestamp" in result:
                doc["segmentTimestamp"] = result["segmentTimestamp"]
            if "headers" in result:
                doc["headers"] = result["headers"]
            
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
                logging.warning(f"Skipping chunk due to size limit. Current chunks: {len(docs)}")
                break
        
        docs_as_string = json.dumps(docs)
        output_message = {
            "Value": docs_as_string,
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