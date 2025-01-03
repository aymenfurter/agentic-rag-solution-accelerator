import azure.functions as func
import logging
import json
import time
from .initialize_client import initialize_client
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.models import QueryType
from azure.storage.blob import BlobServiceClient

def search_artifact (payload):
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

    return results

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
# Update the process_tool_call function to use the new imports
def process_tool_call(tool_call):
    """Process a tool call and return its output"""
    arguments = json.loads(tool_call['azure_function'].get('arguments', '{}'))
    input_queue_name = arguments['outputqueueuri'].split('/')[-1]
    if input_queue_name == "artifactchunk-input":
        result, _ = search_artifact(tool_call['azure_function'].get('arguments', '{}'))
        return {
            "tool_call_id": tool_call['id'],
            "output": result 
        }
    else:
        return {
            "tool_call_id": tool_call['id'],
            "output": search_chunk(tool_call['azure_function'].get('arguments', '{}')) 
        }

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Starting chat request processing')
    
    try:
        req_body = req.get_json()
        prompt = req_body.get('prompt')
        thread_id = req_body.get('threadId')
        
        logging.info(f'Received request - Thread ID: {thread_id}, Prompt: {prompt}')
        
        # Initialize client and get agent
        project_client, agent_id = initialize_client()
        logging.info(f'Initialized client with agent ID: {agent_id}')
        
        if not thread_id:
            logging.info('No thread ID provided, creating new thread')
            thread = project_client.agents.create_thread()
            return func.HttpResponse(
                json.dumps({"threadId": thread.id}),
                mimetype="application/json",
                status_code=200
            )
            
        if not prompt:
            logging.warning('No prompt provided')
            return func.HttpResponse(
                "Missing prompt",
                status_code=400
            )
            
        try:
            # Get or create thread
            try:
                logging.info(f'Retrieving thread {thread_id}')
                thread = project_client.agents.get_thread(thread_id)
            except Exception as e:
                logging.warning(f'Failed to get thread, creating new one: {str(e)}')
                thread = project_client.agents.create_thread()
                thread_id = thread.id
            
            # Send message
            logging.info('Creating message')
            message = project_client.agents.create_message(
                thread_id=thread_id,
                role="user",
                content=prompt,
            )
            logging.info(f"Created message with ID: {message.id}")
            
            # Create and monitor run
            logging.info('Creating run')
            run = project_client.agents.create_run(
                thread_id=thread_id,
                assistant_id=agent_id
            )
            logging.info(f"Created run with ID: {run.id}")
            
            # Monitor run with timeout
            start_time = time.time()
            timeout = 30  # 30 seconds timeout
            
            while run.status in ["queued", "in_progress", "requires_action"]:
                if time.time() - start_time > timeout:
                    raise Exception("Run timed out after 30 seconds")
                
                logging.info(f"Run status: {run.status}")
                
                if run.status == "requires_action":
                    # Handle required actions
                    if run.required_action.type == "submit_tool_outputs":
                        tool_outputs = []
                        for tool_call in run.required_action.submit_tool_outputs.tool_calls:
                            try:
                                output = process_tool_call(tool_call)
                                if output:
                                    tool_outputs.append(output)
                            except Exception as e:
                                logging.error(f"Error processing tool call: {str(e)}")
                                continue
                        
                        if tool_outputs:
                            logging.info(f"Submitting tool outputs: {tool_outputs}")
                            run = project_client.agents.submit_tool_outputs_to_run(
                                thread_id=thread_id,
                                run_id=run.id,
                                tool_outputs=tool_outputs
                            )
                            continue
                
                time.sleep(2)
                run = project_client.agents.get_run(
                    thread_id=thread_id,
                    run_id=run.id
                )

            logging.info(f"Run completed with status: {run.status}")
            
            if run.status == "failed":
                error_msg = f"Run failed: {run.last_error}"
                logging.error(error_msg)
                raise Exception(error_msg)
            
            if run.status != "completed":
                error_msg = f"Unexpected run status: {run.status}"
                logging.error(error_msg)
                raise Exception(error_msg)
            
            # Get messages from the thread
            logging.info('Retrieving messages')
            messages = project_client.agents.list_messages(thread_id=thread_id)
            
            # Find the last assistant message
            assistant_messages = [
                msg for msg in messages.data
                if msg.role == "assistant"
            ]
            
            if not assistant_messages:
                error_msg = "No response received from assistant"
                logging.error(error_msg)
                raise Exception(error_msg)
                
            # last message is first message in the list
            last_msg = assistant_messages[0]
            
            response = {
                "role": "assistant",
                "content": last_msg.content[0].text.value if last_msg.content else "",
                "timestamp": last_msg.created_at.isoformat()
            }
            
            logging.info('Successfully processed chat request')
            return func.HttpResponse(
                json.dumps(response),
                mimetype="application/json",
                status_code=200
            )
            
        except Exception as e:
            import traceback
            logging.error(traceback.format_exc())
            logging.error(f"Error during chat processing: {str(e)}")
            raise  # Re-raise to be caught by outer try-except
            
    except Exception as e:
        error_msg = f"Chat function error: {str(e)}"
        logging.error(error_msg)
        return func.HttpResponse(
            json.dumps({"error": error_msg}),
            status_code=500
        )
