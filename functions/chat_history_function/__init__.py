import azure.functions as func
import logging
import json

from azure.storage.blob import BlobServiceClient
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

import os

def initialize_client():
    """Initialize the agent client and create a new thread"""
    project_client = AIProjectClient.from_connection_string(
        credential=DefaultAzureCredential(),
        conn_str=os.environ["AI_PROJECT_CONNECTION_STRING"]
    )
    
    # Get agent ID from config
    blob_client = BlobServiceClient.from_connection_string(os.environ["STORAGE_CONNECTION_STRING"])
    container_client = blob_client.get_container_client("schemas")
    config_blob = container_client.get_blob_client("user_config.json")
    schema_json = json.loads(config_blob.download_blob().readall())
    
    agent_name = schema_json.get("name") if isinstance(schema_json.get("name"), str) else "customAgent"
    
    # Get agents list
    agents_response = project_client.agents.list_agents()
    agents_data = []
    if isinstance(agents_response, dict):
        agents_data = agents_response.get('data', [])
    elif hasattr(agents_response, 'data'):
        agents_data = agents_response.data
    else:
        agents_data = list(agents_response)
    
    # Find matching agent
    agent = None
    for a in agents_data:
        if isinstance(a, dict):
            if a.get('name') == agent_name:
                agent = a
                break
        elif getattr(a, 'name', None) == agent_name:
            agent = a
            break
    
    if not agent and agents_data:
        agent = agents_data[0]
    
    if not agent:
        raise ValueError("No agents available")
    
    agent_id = agent.get('id') if isinstance(agent, dict) else getattr(agent, 'id', None)
    if not agent_id:
        raise ValueError("Agent ID not found")
    
    return project_client, agent_id


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Processing chat history request')
    
    try:
        thread_id = req.route_params.get('threadId')
        if not thread_id:
            return func.HttpResponse(
                "No thread ID provided",
                status_code=400
            )
            
        # Initialize client
        project_client, agent_id = initialize_client()
        
        # Get thread messages
        messages = project_client.agents.list_messages(thread_id=thread_id)
        
        # Format messages
        formatted_messages = []
        for msg in messages.data:
            formatted_messages.append({
                "role": msg.role,
                "content": msg.content[0].text.value if msg.content else "",
                "timestamp": msg.created_at.isoformat()
            })

        formatted_messages = formatted_messages[::-1]
            
        return func.HttpResponse(
            json.dumps({"messages": formatted_messages}),
            mimetype="application/json"
        )
            
    except Exception as e:
        logging.error(f"Error getting chat history: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500
        )
