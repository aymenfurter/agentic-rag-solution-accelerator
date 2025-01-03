import json
import logging
import os
import azure.functions as func
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.models import QueryType
from azure.storage.blob import BlobServiceClient

def main(msg: func.QueueMessage, outputQueueItem: func.Out[str]) -> None:
    # Azure AI Agent Service currently does not invoke this funciton. Logic currently in chat_function