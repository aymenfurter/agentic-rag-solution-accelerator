import azure.functions as func
import logging
import json
from chat_function.initialize_client import initialize_client

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Creating new chat thread')
    
    try:
        # Initialize client
        project_client, agent_id = initialize_client()
        
        # Create new thread
        thread = project_client.agents.create_thread()
        
        return func.HttpResponse(
            json.dumps({"threadId": thread.id}),
            mimetype="application/json",
            status_code=200
        )
            
    except Exception as e:
        logging.error(f"Error creating chat thread: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500
        )
