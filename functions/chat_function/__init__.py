import azure.functions as func
import logging
import json
import time
from .initialize_client import initialize_client
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.models import QueryType
from azure.storage.blob import BlobServiceClient

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
                    # submit timeout message to run
                    project_client.agents.cancel_run(thread_id=thread.id, run_id=run.id)
                    raise Exception("Run timed out after 60 seconds")
                
                logging.info(f"Run status: {run.status}")
                
                time.sleep(1)
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
