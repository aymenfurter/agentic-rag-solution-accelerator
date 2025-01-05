import azure.functions as func
import logging
import json
import os
from azure.storage.blob import BlobServiceClient
from .markdown_chunker import MarkdownChunker
from .audio_chunker import AudioTranscriptChunker 
from .content_understanding_utils import analyze_file
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from datetime import datetime
import base64

def sanitize_document_id(id_str: str) -> str:
    """Convert a string to a valid document key using URL-safe Base64 encoding"""
    encoded = base64.urlsafe_b64encode(id_str.encode()).decode()
    return encoded.rstrip('=')  # Remove trailing '=' padding

def process_content_item(content_item: dict, metadata: dict, schema_json: dict) -> tuple[dict, list]:
    """Process a single content item and return artifact doc and chunks"""
    content_kind = content_item.get("kind", "document")
    
    # Extract fields and their values from content item
    fields = content_item.get("fields", {})
    content_metadata = {
        **metadata
    }
    
    # Extract values from fields, handling complex field structures
    for k, v in fields.items():
        if isinstance(v, dict):
            if v.get("type") == "array":
                content_metadata[k] = [
                    item.get("valueString", "") 
                    for item in v.get("valueArray", [])
                ] or []
            else:
                content_metadata[k] = v.get("valueString", "")
        else:
            content_metadata[k] = v

    # Create artifact document with correct field names (no chunk prefix)
    artifact_doc = {
        "id": metadata["id"],  # Use id for artifacts
        "content": content_item.get("markdown", ""),
        "docType": metadata["docType"],
        "timestamp": metadata["timestamp"],
        "fileName": metadata["fileName"]
    }
    
    # Add schema-defined fields
    for k, v in content_metadata.items():
        if k in [f["name"] for f in schema_json.get("fields", [])]:
            artifact_doc[k] = v
    
    # Create chunks
    chunks = []
    if content_kind == "audioVisual":
        chunker = AudioTranscriptChunker()
        markdown_content = content_item.get("markdown", "")
        chunks = chunker.create_chunks(markdown_content, metadata)
    else:
        chunker = MarkdownChunker()
        markdown_content = content_item.get("markdown", "")
        chunks = chunker.create_chunks(markdown_content, metadata)
    
    return artifact_doc, chunks

def format_datetime(dt):
    """Format datetime in ISO 8601 format with Z suffix"""
    return dt.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

def main(myblob: func.InputStream):
    logging.info(f"Processing new blob: {myblob.name}")
    
    try:
        # Get blob content
        content = myblob.read()
        blob_name = myblob.name.split("/")[-1]
        
        # Sanitize the document ID
        safe_id = sanitize_document_id(blob_name)
        
        # Get user configuration
        blob_client = BlobServiceClient.from_connection_string(os.environ["STORAGE_CONNECTION_STRING"])
        container_client = blob_client.get_container_client("schemas")
        config_blob = container_client.get_blob_client("user_config.json")
        schema_json = json.loads(config_blob.download_blob().readall())
        
        # Create base metadata with properly formatted timestamp and safe ID
        base_metadata = {
            "id": safe_id,
            "fileName": blob_name,
            "timestamp": format_datetime(datetime.utcnow()),
            "docType": "artifact"
        }
        
        # Get content understanding analysis
        analyze_result = analyze_file(schema_json.get("name"), content)
        if not analyze_result or not analyze_result.get("contents"):
            raise ValueError("No content analysis results")
        
        # Process all content items
        all_artifacts = []
        all_chunks = []
        
        for content_item in analyze_result["contents"]:
            artifact_doc, chunks = process_content_item(
                content_item,
                base_metadata,
                schema_json  # Pass schema_json to process_content_item
            )
            all_artifacts.append(artifact_doc)
            all_chunks.extend(chunks)
        
        # Upload to search
        search_endpoint = os.environ["SEARCH_ENDPOINT"]
        search_key = os.environ["SEARCH_ADMIN_KEY"]
        
        artifact_client = SearchClient(
            endpoint=search_endpoint,
            index_name="artifacts",
            credential=AzureKeyCredential(search_key)
        )
        
        chunk_client = SearchClient(
            endpoint=search_endpoint,
            index_name="chunks",
            credential=AzureKeyCredential(search_key)
        )
        
        if all_artifacts:
            artifact_client.upload_documents(documents=all_artifacts)
        if all_chunks:
            chunk_client.upload_documents(documents=all_chunks)
            
    except Exception as e:
        logging.error(f"Error in ingestion function: {str(e)}")
        raise