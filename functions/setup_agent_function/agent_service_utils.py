import os
import logging
from typing import Dict, Any
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    AzureFunctionStorageQueue, 
    AzureFunctionTool,
    FileSearchTool,
    ToolResources
)
from azure.identity import DefaultAzureCredential

def parse_project_connection_string(conn_string: str) -> Dict[str, str]:
    """Parse the project connection string into components."""
    components = {}
    for part in conn_string.split(';'):
        if '=' in part:
            key, value = part.split('=', 1)
            components[key.lower()] = value
    return components

def create_or_update_agent(schema_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create or update an agent in Azure AI Agent Service."""
    try:
        # Get function app name from WEBSITE_CONTENTSHARE
        function_app_name = os.environ.get("WEBSITE_CONTENTSHARE", "")
        if not function_app_name:
            raise ValueError("Could not determine function app name from WEBSITE_CONTENTSHARE")
            
        # Construct base function URL
        function_base_url = f"https://{function_app_name}.azurewebsites.net/api"

        project_client = AIProjectClient.from_connection_string(
            credential=DefaultAzureCredential(),
            conn_str=os.environ["AI_PROJECT_CONNECTION_STRING"]
        )

        # Build field instructions with filter examples
        field_instructions = []
        filter_examples = []
        
        for field in schema_data["fields"]:
            field_name = field["name"]
            field_type = field["type"]
            description = field.get("description", "")
            
            if field_type == "array":
                field_instructions.append(
                    f"- {field_name}: List of strings. {description}"
                )
                filter_examples.append(f"array_contains({field_name}, 'value')")
            elif field_type == "date":
                field_instructions.append(
                    f"- {field_name}: Date/time value (ISO 8601). {description}"
                )
                filter_examples.append(f"{field_name} gt '2023-01-01T00:00:00Z'")
            else:
                field_instructions.append(
                    f"- {field_name}: Text value. {description}"
                )
                filter_examples.append(f"{field_name} eq 'value'")

        base_instructions = f"""{schema_data['instructions']}

Available fields for searching and filtering:
{chr(10).join(field_instructions)}

You can create filters using OData syntax. Examples:
{chr(10).join(filter_examples)}

When searching documents, construct relevant filters based on the user's request.
"""

        # Create function tools
        artifact_tool = AzureFunctionTool(
            name="Artifact",
            description="Search high-level artifact information using semantic search",
            parameters={
                "type": "object",
                "properties": {
                    "searchText": {"type": "string"},
                    "filter": {"type": "string", "description": "OData filter expression"},
                },
                "required": ["searchText"]
            },
            input_queue=AzureFunctionStorageQueue(
                queue_name="artifact-input",
                storage_service_endpoint=os.environ["STORAGE_CONNECTION_STRING"]
            ),
            output_queue=AzureFunctionStorageQueue(
                queue_name="artifact-output",
                storage_service_endpoint=os.environ["STORAGE_CONNECTION_STRING"]
            )
        )

        chunk_tool = AzureFunctionTool(
            name="ArtifactChunk",
            description="Search detailed chunk-level information using semantic search",
            parameters={
                "type": "object",
                "properties": {
                    "searchText": {"type": "string"},
                    "filter": {"type": "string", "description": "OData filter expression"},
                },
                "required": ["searchText"]
            },
            input_queue=AzureFunctionStorageQueue(
                queue_name="artifactchunk-input",
                storage_service_endpoint=os.environ["STORAGE_CONNECTION_STRING"]
            ),
            output_queue=AzureFunctionStorageQueue(
                queue_name="artifactchunk-output",
                storage_service_endpoint=os.environ["STORAGE_CONNECTION_STRING"]
            )
        )

        tool_definitions = [
            artifact_tool.definitions,
            chunk_tool.definitions
        ]

        agent = project_client.agents.create_agent(
            model=os.environ["GPT_DEPLOYMENT_NAME"],
            name=schema_data["name"],
            instructions=base_instructions,
            headers={"x-ms-enable-preview": "true"},
            tools=tool_definitions
        )

        return agent.to_dict()

    except Exception as e:
        logging.error(f"Error creating agent: {str(e)}")
        raise