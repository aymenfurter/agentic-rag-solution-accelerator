import os
import logging
from typing import Dict, Any
import requests
import json

def create_or_update_analyzer(schema_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create or update an analyzer in Azure AI Content Understanding
    based on the provided schema.
    """
    try:
        endpoint = os.environ["AI_ENDPOINT"]
        if endpoint.endswith("/"):
            endpoint = endpoint[:-1]
        key = os.environ["AI_KEY"]
        api_version = "2024-12-01-preview"
        analyzer_id = schema_data["name"]
        
        url = f"{endpoint}/contentunderstanding/analyzers/{analyzer_id}?api-version={api_version}"
        
        # Build analyzer configuration
        analyzer_config = {
            "description": f"Analyzer for {analyzer_id}",
            "scenario": "document",
            "fieldSchema": {
                "name": analyzer_id,
                "description": "Custom schema for document analysis",
                "fields": {}
            },
            "config": {
                "enableOcr": True,
                "enableLayout": True,
                "returnDetails": True
            }
        }

        # Map field types to Content Understanding types
        type_mapping = {
            "string": "string",
            "array": "array",
            "date": "datetime",
            "datetime": "datetime",
            "integer": "integer",
            "number": "number",
            "boolean": "boolean"
        }

        # Add fields based on schema
        for field in schema_data["fields"]:
            field_name = field["name"]
            field_type = field["type"]
            description = field.get("description", "")
            method = field.get("method", "extract")
            
            field_def = {
                "type": type_mapping.get(field_type, "string"),
                "method": method,
                "description": description
            }
            
            if field_type == "array":
                field_def["items"] = {
                    "type": type_mapping.get(field.get("arrayType", "string"), "string")
                }

            analyzer_config["fieldSchema"]["fields"][field_name] = field_def

        # Add summary field if not already present
        if "summary" not in analyzer_config["fieldSchema"]["fields"]:
            analyzer_config["fieldSchema"]["fields"]["summary"] = {
                "type": "string",
                "method": "generate",
                "description": "Summary of the document content"
            }

        headers = {
            "Ocp-Apim-Subscription-Key": key,
            "Content-Type": "application/json"
        }

        logging.info(f"Creating analyzer with config: {json.dumps(analyzer_config, indent=2)}")

        response = requests.put(url, headers=headers, json=analyzer_config)
        
        if not response.ok:
            logging.error(f"Error creating analyzer: {response.status_code} {response.text}")
        
        response.raise_for_status()
        return response.json()

    except Exception as e:
        logging.error(f"Error creating analyzer: {str(e)}")
        raise