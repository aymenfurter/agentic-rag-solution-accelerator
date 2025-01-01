# /upload_file_function/__init__.py
import azure.functions as func
import os
from azure.storage.blob import BlobServiceClient
import uuid
import json
import logging

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Processing upload file request')
    
    try:
        # Get the file from the request
        file = req.files.get('file')
        if not file:
            return func.HttpResponse("No file attached.", status_code=400)

        # Read file content        
        file_content = file.read()
        
        # Generate unique ID and create filename
        file_id = str(uuid.uuid4())
        original_filename = file.filename
        file_name = f"{file_id}_{original_filename}"

        # Get metadata if provided
        metadata = json.loads(req.form.get('metadata', '{}'))
        metadata.update({
            'artifactId': file_id,
            'fileName': original_filename
        })

        # Get blob storage connection
        blob_conn_str = os.environ["STORAGE_CONNECTION_STRING"]
        blob_client = BlobServiceClient.from_connection_string(blob_conn_str)
        
        # Get files container
        container = blob_client.get_container_client("files")
        try:
            container.create_container()
        except:
            pass

        # Upload file to blob storage
        blob = container.upload_blob(
            name=file_name,
            data=file_content,
            overwrite=True,
            metadata=metadata
        )

        return func.HttpResponse(
            json.dumps({
                "fileId": file_id,
                "originalName": original_filename,
                "blobName": file_name
            }),
            status_code=200,
            mimetype="application/json"
        )
            
    except Exception as e:
        logging.error(f'Error in upload_file: {str(e)}')
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )