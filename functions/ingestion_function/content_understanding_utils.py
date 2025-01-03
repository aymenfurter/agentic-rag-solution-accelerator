import os
import logging
import requests
import time
import uuid

def analyze_file(analyzer_id: str, content: bytes) -> dict:
    """Analyze file content using Azure AI Content Understanding binary API."""
    try:
        endpoint = os.environ["CO_AI_ENDPOINT"].rstrip('/')
        key = os.environ["CO_AI_KEY"]
        api_version = "2024-12-01-preview"
        
        # Use binary analyze endpoint
        url = f"{endpoint}/contentunderstanding/analyzers/{analyzer_id}:analyze?_overload=analyzeBinary&api-version={api_version}"
        
        headers = {
            "Ocp-Apim-Subscription-Key": key,
            "Content-Type": "application/octet-stream",
            "Operation-Id": str(uuid.uuid4()),
            "x-ms-client-request-id": str(uuid.uuid4())
        }
        
        logging.info(f"Making binary analyze request to {url}")
        response = requests.post(url, headers=headers, data=content)
        
        if response.status_code == 202:  # Accepted - async operation
            operation_url = response.headers.get('Operation-Location')
            if not operation_url:
                raise ValueError("No Operation-Location header in response")
            
            max_retries = 120
            retry_delay = 2
            
            for attempt in range(max_retries):
                logging.info(f"Polling attempt {attempt + 1} of {max_retries}")
                result_response = requests.get(
                    operation_url,
                    headers={"Ocp-Apim-Subscription-Key": key}
                )
                
                if not result_response.ok:
                    logging.error(f"Error response: {result_response.text}")
                    result_response.raise_for_status()
                
                result = result_response.json()
                status = result.get('status', '').lower()
                
                if status == 'succeeded':
                    logging.info("Analysis completed successfully")
                    return result.get('result', {})
                elif status in ['failed', 'canceled']:
                    error_msg = result.get('error', {}).get('message', 'Unknown error')
                    raise Exception(f"Analysis failed: {error_msg}")
                elif status in ['notstarted', 'running']:
                    time.sleep(retry_delay)
                else:
                    raise Exception(f"Unknown status: {status}")
            
            raise TimeoutError("Analysis timed out")
            
        else:
            logging.error(f"Error response: {response.text}")
            response.raise_for_status()
            
    except Exception as e:
        logging.error(f"Error in analyze_file: {str(e)}")
        if isinstance(e, requests.exceptions.HTTPError):
            logging.error(f"Response content: {e.response.text}")
        raise
