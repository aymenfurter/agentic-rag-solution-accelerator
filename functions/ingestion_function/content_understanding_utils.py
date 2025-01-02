import os
import logging
import json
import time
import requests
from typing import Dict, Any, Union

def analyze_file(analyzer_id: str, file_content: Union[bytes, str], file_name: str = None) -> Dict[str, Any]:
    """
    Analyze file content using Azure AI Content Understanding.
    
    Args:
        analyzer_id: ID of the analyzer to use
        file_content: The content of the file to analyze
        file_name: Name of the file being analyzed
        
    Returns:
        dict: Analysis results containing extracted information
    """
    try:
        endpoint = os.environ["CO_AI_ENDPOINT"]
        if endpoint.endswith("/"):
            endpoint = endpoint[:-1]
        key = os.environ["CO_AI_KEY"]
        api_version = "2024-12-01-preview"

        # Start analysis
        url = f"{endpoint}/contentunderstanding/analyzers/{analyzer_id}:analyze?api-version={api_version}"
        
        headers = {
            "Ocp-Apim-Subscription-Key": key,
            "Content-Type": "application/json"
        }

        # Prepare file content
        file_bytes = file_content if isinstance(file_content, bytes) else file_content.encode('utf-8')
        import base64
        encoded_content = base64.b64encode(file_bytes).decode('utf-8')
        
        body = {
            "base64Source": encoded_content
        }

        # Start analysis
        response = requests.post(url, headers=headers, json=body)
        if not response.ok:
            logging.error(f"Error starting analysis: {response.status_code} {response.text}")
            response.raise_for_status()

        # Get operation URL from header
        operation_url = response.headers.get("Operation-Location")
        if not operation_url:
            raise ValueError("No Operation-Location header in response")

        # Poll for results
        max_retries = 30
        retry_delay = 1  # seconds
        for _ in range(max_retries):
            result_response = requests.get(
                operation_url,
                headers={"Ocp-Apim-Subscription-Key": key}
            )
            
            if not result_response.ok:
                logging.error(f"Error getting results: {result_response.status_code} {result_response.text}")
                result_response.raise_for_status()
                
            result = result_response.json()
            status = result.get("status", "").lower()
            
            if status == "succeeded":
                # Process results based on content type
                contents = result.get("result", {}).get("contents", [])
                if not contents:
                    raise ValueError("No contents in analysis results")
                
                content = contents[0]  # Get first content
                content_type = content.get("kind", "document")
                
                # Extract fields
                fields = content.get("fields", {})
                
                # Common metadata
                metadata = {
                    "content": content.get("markdown", ""),
                    "fileName": file_name,
                    "contentType": content_type
                }
                
                # Add extracted fields to metadata
                for field_name, field_data in fields.items():
                    if field_data.get("type") == "string":
                        metadata[field_name] = field_data.get("valueString")
                    elif field_data.get("type") == "array":
                        metadata[field_name] = [
                            item.get("valueObject", {}) 
                            for item in field_data.get("valueArray", [])
                        ]
                
                return {
                    "metadata": metadata,
                    "chunks": []  # Let Content Understanding handle chunking
                }
                
            elif status in ["running", "notstarted"]:
                time.sleep(retry_delay)
                continue
            else:
                raise ValueError(f"Analysis failed with status: {status}")
                
        raise TimeoutError("Analysis timed out")

    except Exception as e:
        logging.error(f"Error in analyze_file: {str(e)}")
        raise
