import azure.functions as func
import logging
import json
import os
from azure.storage.blob import BlobServiceClient
from shared.chunking.markdown_chunker import MarkdownChunker
from shared.chunking.audio_chunker import AudioTranscriptChunker
from ingestion_function.content_understanding_utils import analyze_file
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential

def main(myblob: func.InputStream):
    logging.info(f"Processing new blob: {myblob.name}")
    
    try:
        # Get blob content
        content = myblob.read()
        blob_name = myblob.name.split("/")[-1]  # e.g. <guid>_<filename>
        file_id = blob_name.split("_")[0]

        # Get blob storage client
        blob_conn_str = os.environ["STORAGE_CONNECTION_STRING"]
        blob_client = BlobServiceClient.from_connection_string(blob_conn_str)
        
        # Get user configuration
        container_client = blob_client.get_container_client("schemas")
        config_blob = container_client.get_blob_client("user_config.json")
        schema_json = json.loads(config_blob.download_blob().readall())

        # Get file type from filename
        file_type = blob_name.split(".")[-1].lower()
        
        # Call Content Understanding for analysis
        analyzer_id = schema_json.get("name", "customAnalyzer")
        analyze_result = analyze_file(analyzer_id, content)

        # Create metadata for chunks
        metadata = {
            "artifactId": file_id,
            "fileName": "_".join(blob_name.split("_")[1:]),  # Original filename
            **analyze_result.get("metadata", {})
        }

        # Choose appropriate chunker based on file type
        chunks = []
        if file_type in ['md', 'markdown']:
            chunker = MarkdownChunker()
            chunks = chunker.create_chunks(content.decode('utf-8'), metadata)
        elif file_type in ['wav', 'mp3', 'ogg']:
            chunker = AudioTranscriptChunker()
            transcript_text = analyze_result.get('transcript', '')
            chunks = chunker.create_chunks(transcript_text, metadata)
        else:
            # Default text chunking through Content Understanding
            chunks = analyze_result.get('chunks', [])

        # Create summary document
        summary = analyze_result.get('summary', '')
        if summary:
            summary_doc = {
                "id": f"{file_id}_summary",
                "content": summary,
                "docType": "artifact",
                "artifactId": file_id,
                "fileName": metadata["fileName"],
                **metadata
            }
            chunks.append(summary_doc)

        # Get Azure AI Search client
        search_endpoint = os.environ["SEARCH_ENDPOINT"]
        search_key = os.environ["SEARCH_ADMIN_KEY"]
        index_name = os.environ["SEARCH_INDEX_NAME"]
        
        search_client = SearchClient(
            endpoint=search_endpoint,
            index_name=index_name,
            credential=AzureKeyCredential(search_key)
        )

        # Upload chunks to search index
        if chunks:
            result = search_client.upload_documents(documents=chunks)
            logging.info(f"Uploaded {len(result)} chunks to search index")
        
        return

    except Exception as e:
        logging.error(f"Error in ingestion function: {str(e)}")
        raise