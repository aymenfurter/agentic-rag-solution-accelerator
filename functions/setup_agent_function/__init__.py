import azure.functions as func
import os
import json
import logging
from .agent_service_utils import create_or_update_agent
from .content_understanding_utils import create_or_update_analyzer
from azure.storage.blob import BlobServiceClient, ContainerClient
from azure.core.exceptions import ResourceExistsError
from .create_ai_search_index import create_search_indexes

def get_or_create_container(conn_str: str, container_name: str) -> ContainerClient:
    blob_client = BlobServiceClient.from_connection_string(conn_str)
    container_client = blob_client.get_container_client(container_name)
    try:
        container_client.create_container()
    except ResourceExistsError:
        pass
    return container_client

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Processing setup agent request")

    try:
        # Handle GET request for setup status
        if req.method == "GET" and req.route_params.get('action') == 'status':
            try:
                container = get_or_create_container(
                    os.environ["STORAGE_CONNECTION_STRING"],
                    "schemas"
                )
                blob_client = container.get_blob_client("user_config.json")
                
                exists = blob_client.exists()
                return func.HttpResponse(
                    json.dumps({"isConfigured": exists}),
                    status_code=200,
                    mimetype="application/json"
                )
            except Exception as e:
                logging.error(f"Error checking setup status: {str(e)}")
                return func.HttpResponse(
                    json.dumps({"error": "Error checking setup status"}),
                    status_code=500,
                    mimetype="application/json"
                )

        # If not a status check, verify and parse request body
        if req.method == "POST":
            try:
                body = req.get_json()
            except ValueError:
                return func.HttpResponse(
                    json.dumps({"error": "Invalid JSON in request body"}),
                    status_code=400,
                    mimetype="application/json"
                )

            # Validate required fields
            if not body.get("fields"):
                return func.HttpResponse(
                    "Missing required fields configuration",
                    status_code=400
                )

            # Validate field count
            total_fields = len(body["fields"])
            if total_fields > 10:
                return func.HttpResponse(
                    "Maximum number of fields (10) exceeded",
                    status_code=400
                )

            # Construct schema data
            schema_data = {
                "fields": body["fields"],
                "name": body.get("name", "customSchema"),
                "instructions": body.get("instructions", "You are a helpful agent for processing documents."),
                "template": body.get("template"),
                "scenario": body.get("scenario", "document")  # Add this line
            }
            
            # Create search indexes first
            try:
                create_search_indexes(schema_data["fields"])
                logging.info("Created search indexes")
            except Exception as e:
                logging.error(f"Error creating search indexes: {str(e)}")
                return func.HttpResponse(
                    "Error creating search indexes",
                    status_code=500
                )

            # Store config in blob storage
            try:
                container = get_or_create_container(
                    os.environ["STORAGE_CONNECTION_STRING"],
                    "schemas"
                )
                
                container.upload_blob(
                    "user_config.json",
                    json.dumps(schema_data, indent=2),
                    overwrite=True
                )
            except Exception as e:
                logging.error(f"Error storing configuration: {str(e)}")
                return func.HttpResponse(
                    "Error storing configuration",
                    status_code=500
                )

            # Create/update analyzer and agent
            try:
                analyzer_result = create_or_update_analyzer(schema_data)
                agent_result = create_or_update_agent(schema_data)
            except Exception as e:
                import requests
                if isinstance(e, requests.exceptions.HTTPError) and e.response.status_code == 409:
                    # Return success even if analyzer already exists
                    return func.HttpResponse(
                        json.dumps({
                            "status": "success",
                            "message": "Using existing analyzer",
                            "analyzerId": schema_data["name"]
                        }),
                        status_code=200,
                        mimetype="application/json"
                    )
                raise

            return func.HttpResponse(
                json.dumps({
                    "status": "success",
                    "analyzerId": analyzer_result.get("analyzerId"),
                    "agentId": agent_result.get("id"),
                }),
                status_code=200,
                mimetype="application/json"
            )
            
        # Handle unsupported methods
        return func.HttpResponse(
            json.dumps({"error": "Method not allowed"}),
            status_code=405,
            mimetype="application/json"
        )
            
    except Exception as e:
        import traceback
        logging.error(traceback.format_exc())
        logging.error(f"Error in setup_agent: {str(e)}")
        return func.HttpResponse(
            str(e),
            status_code=500
        )