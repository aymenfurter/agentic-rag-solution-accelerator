import logging
import json
import os
from azure.storage.blob import BlobServiceClient
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

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

    # delete all agents if not found
    if not agent:
        for a in agents_data:
            print ("deleting agent: ", a.id)
            project_client.agents.delete_agent(a.id)
    
    if not agent and agents_data:
        agent = agents_data[0]
    
    if not agent:
        raise ValueError("No agents available")
    
    agent_id = agent.get('id') if isinstance(agent, dict) else getattr(agent, 'id', None)
    if not agent_id:
        raise ValueError("Agent ID not found")
    
    return project_client, agent_id
