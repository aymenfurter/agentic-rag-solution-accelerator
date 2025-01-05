import azure.functions as func
import logging
import os
from azure.storage.blob import BlobServiceClient
import mimetypes

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Processing get file request')
    
    try:
        # Get filename from route parameter
        filename = req.route_params.get('filename')
        if not filename:
            return func.HttpResponse("Filename not provided", status_code=400)

        # Get blob storage connection
        blob_conn_str = os.environ["STORAGE_CONNECTION_STRING"]
        blob_client = BlobServiceClient.from_connection_string(blob_conn_str)
        
        # Get container client
        container = blob_client.get_container_client("files")
        
        # Get blob client
        blob = container.get_blob_client(filename)
        
        # Check if blob exists
        if not blob.exists():
            return func.HttpResponse("File not found", status_code=404)

        # Get content type
        content_type, _ = mimetypes.guess_type(filename)
        if not content_type:
            content_type = 'application/octet-stream'

        # Download blob
        blob_data = blob.download_blob()
        
        # Get metadata
        metadata = blob.get_blob_properties().metadata

        # Set response headers for content disposition
        headers = {
            'Content-Type': content_type,
            'x-ms-meta-filename': metadata.get('fileName', filename),
            'Content-Disposition': f'inline; filename="{metadata.get("fileName", filename)}"'
        }

        return func.HttpResponse(
            body=blob_data.readall(),
            headers=headers,
            status_code=200
        )
            
    except Exception as e:
        logging.error(f'Error in get_file: {str(e)}')
        return func.HttpResponse(
            f"Error retrieving file: {str(e)}",
            status_code=500
        )
