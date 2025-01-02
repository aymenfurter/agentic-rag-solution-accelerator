import os
import logging
from typing import Dict, Any
import requests
import json
import uuid

def create_or_update_analyzer(schema_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create or update an analyzer in Azure AI Content Understanding."""
    try:
        endpoint = os.environ["CO_AI_ENDPOINT"]
        if endpoint.endswith("/"):
            endpoint = endpoint[:-1]
        key = os.environ["CO_AI_KEY"]
        api_version = "2024-12-01-preview"
        analyzer_id = schema_data["name"]
        
        url = f"{endpoint}/contentunderstanding/analyzers/{analyzer_id}?api-version={api_version}"
        
        # Match the exact structure of the working example
        analyzer_config = {
            "analyzerId": analyzer_id,
            "description": schema_data.get("description", f"Analyzer for {analyzer_id}"),
            "scenario": schema_data.get("scenario", "conversation"),
            "fieldSchema": {
                "fields": {},
                "definitions": {}
            },
            "tags": {
                "projectId": str(uuid.uuid4()),
                "templateId": f"{analyzer_id}-2024-12-01"
            },
            "config": {
                "locales": [],
                "returnDetails": False
            }
        }

        # Add fields based on schema
        fields = {}
        for field in schema_data["fields"]:
            field_name = field["name"]
            field_type = field["type"]
            description = field.get("description", "")
            
            if field_name == "summary":
                fields[field_name] = {
                    "type": "string",
                    "method": "generate",
                    "description": description
                }
            elif field_type == "array":
                fields[field_name] = {
                    "type": "array",
                    "method": "generate",
                    "description": description,
                    "items": {
                        "type": "string",
                        "method": "generate"
                    }
                }
            else:
                fields[field_name] = {
                    "type": field_type,
                    "method": "generate",
                    "description": description
                }

        analyzer_config["fieldSchema"]["fields"] = fields

        headers = {
            "Ocp-Apim-Subscription-Key": key,
            "Content-Type": "application/json"
        }

        logging.info(f"Creating analyzer with config: {json.dumps(analyzer_config, indent=2)}")

        response = requests.put(
            url,
            headers=headers,
            json=analyzer_config
        )
        
        # Handle 409 Conflict as an expected case
        if response.status_code == 409:
            logging.info(f"Analyzer {analyzer_id} already exists (expected)")
            return {
                "analyzerId": analyzer_id,
                "status": "existing"
            }
        
        if not response.ok:
            logging.error(f"Error creating analyzer: {response.status_code} {response.text}")
            response.raise_for_status()
            
        return response.json()

    except Exception as e:
        if isinstance(e, requests.exceptions.HTTPError) and e.response.status_code == 409:
            logging.info(f"Analyzer {analyzer_id} already exists (expected)")
            return {
                "analyzerId": analyzer_id,
                "status": "existing"
            }
        logging.error(f"Error creating analyzer: {str(e)}")
        raise