Create a detailed design document for me. I want to build a solution accelerator at https://github.com/aymenfurter/agentic-rag-solution-accelerator

Description: A solution accelerator showcasing how to build agentic RAG apps using Azure AI Content Understanding and Azure AI Agent Service

GOAL: 
- Chat via Azure AI Agent Service
- Usage of tool use (i.e. calling 2 azure functions) to connect to Azure AI Search
- Azure AI Search uses Reranker feature and also question rewriting feature
- The app should be python based
- The app must use fastapi 
- There must be two functions (for the tool use of the agents)
- For frontend the app must use fluentui
- User should be able to deploy the app using one-click deployment (Deploy to Azure button in GitHub)
- The frontend should run on static web apps. The backend actions should be implemented using functions. There is one Http function for the management of the agent service (i.e. setting up the agent in Azure AI Agent Service. for querying the data azure functions tools must be augmented with the filter information, agents must be aware of available fields to filter, search and also possible values for multi string .. ), there is one function that agents use to get information about artifacts (i.e. infos about uploaded files like timestamp and metadata, but also genai infos, these infos are extracted using ai agent service and are dynamically specified by the user on first startup - more on that later. A function that can be used to get info on document-level (standard rag, but with the feature of filtering based on artifact - so the ai can also drill-down queries). A function that is proxies file upload to storage account, A function that is triggered by a new file uploaded then calls document understanding (with the user-defined schema) then takes the response and chunks the file (based on file type different chunkers are used) and stores the data in the expected format in the Azure AI Search (obviously creating also the schema based on the - in the storage account stored user supplied json schema)
- IMPORTNAT: users must be able to specify what kind of app they want to build on first startup. This information must be stored on a storage account somewhere und read at startup of the app (and kept in memory). What do yI mean with that? essentially users should be able to specify what they care about as a list of fields (exactly same fields that are then given to the agent service). The list of fields can be either strnigs, list of strings or table (table can be again a list of fields). Maximum of fields including subfields is 10. There are also templates available like call center, standard rag, etc. for users to pick from. 
- Now that we have the list of fields its simple. we create the analyzer in content understanding, we allow users to upload files to a storage account, when files are uploaded they are firing a function, we get back the LLM augmented list, store them in AI Search together with mroe metadata like timestamp and complete the action

## Design Doc 

Below is a comprehensive design document for an Agentic RAG solution accelerator using Azure AI Content Understanding (for ingestion), Azure AI Agent Service (for chat-based function calls), Azure AI Search (for storing and retrieving data), Azure Functions (HTTP + blob-trigger), and a FluentUI front end on Azure Static Web Apps. This design integrates the key requirements:

- User-specified fields & templates on first startup  
- Azure AI Content Understanding ingestion triggered by new files in Azure Storage  
- Azure AI Agent with two functions (tools) for reading data from Azure AI Search:  
  - **Artifact** function: for high-level artifact metadata or summary queries  
  - **ArtifactChunk** function: for fine-grained chunk-level queries (with filters, question rewriting, semantic re-rank, etc.)  
- Timestamp is stored as an ISO 8601 datetime field in the index for filtering  
- Filtering is supported via OData $filter expressions in Azure AI Search  
- One-click Deploy approach (ARM or Bicep), Python-based code, usage of azure-functions runtime (not FastAPI).  
- FluentUI for the front-end.

---

### **1. Architecture Overview**

**Flow at a Glance**

1. **First Startup**:
   - User picks or edits a template of fields (e.g. “call center,” “standard RAG,” etc.).
   - System stores the schema (with possible enumerations or allowed values) in Storage.
   - We create an analyzer in Azure AI Content Understanding with these fields.
   - We create (or update) an agent in Azure AI Agent Service with instructions + two function “tools” (Artifact & ArtifactChunk).

2. **File Upload**:
   - User uploads an artifact (audio, PDF, etc.) to an HTTP function → stored in Storage → triggers the blob ingestion function.

3. **Blob Trigger Ingestion**:
   - Reads the user’s schema from Storage.
   - Calls Azure AI Content Understanding to extract structured data (including a summary).
   - “Chunks” the data (with or without embeddings in code, or direct “vector” indexer).
   - Stores chunk-level data in Azure AI Search with possible metadata like timestamp, heading, or user fields.

4. **Chat**:
   - The user interacts with the Azure AI Agent.
   - The agent sees a query. If it needs data from the index, it calls one of two functions:
     1. Artifact function for a higher-level summary or metadata queries (like “which files mention negative sentiment after 2023-09-01?”).
     2. ArtifactChunk for more granular chunk-level queries (like “where exactly is ‘red hat’ mentioned?”).
   - The function uses Azure AI Search (with question rewriting, reranker, filters on timestamps, enumerations, etc.) to retrieve relevant docs and returns them to the agent.
   - The agent composes a final answer.

---

### **2. High-Level Diagram**

```sql
                [Front-End: FluentUI + Static Web App]
                           |  (HTTP)
                           V
 [Azure Functions - HTTP]  +------------------------------------+
    * SetupAgent  (schema, instructions)                        |
    * UploadFile (to Storage)                                   |
    * Artifact => calls Search for high-level metadata          |  Azure AI Agent Svc
    * ArtifactChunk => calls Search for chunk-level data <----> |   - instructions
                           ^                                    |   - Tools: Artifact, ArtifactChunk
                           |  (Blob Trigger)
                           |   
 [Azure Storage] <--- BLOB TRIGGER --> [Ingestion Function] --> [Azure AI Content Understanding]
   - user files                                     |             (Analyze new file)
   - user schema (JSON)                             |----> chunk & embed  -> [Azure AI Search Index]
```

---

### **3. Data Model & User-Specified Fields**

#### 3.1 Template or Custom Fields

On first startup, user picks from a template (like `callCenter`, `standardRag`, etc.) or manually enters up to 10 fields/subfields.

**Example** “callCenter” might define:

```jsonc
{
  "name": "callCenter",
  "fields": [
    {
      "name": "peopleMentioned",
      "type": "array",
      "description": "Possible values: any string array"
    },
    {
      "name": "sentiment",
      "type": "string",
      "description": "Allowed values: 'positive', 'neutral', 'negative'"
    },
    {
      "name": "timestamp",
      "type": "date",
      "description": "ISO 8601 datetime representing start of call"
    },
    {
      "name": "summary",
      "type": "string",
      "description": "High-level summary of the entire artifact"
    }
  ],
  "instructions": "You are a helpful agent for call center logs. Summaries are available for each artifact."
}
```

*Note*: We store this JSON in `schemas/user_config.json` in Azure Storage. Then we define a Content Understanding analyzer from it, and instruct the agent about these fields.

---

### **4. Azure Functions Implementation (Python + azure-functions)**

#### **4.1 SetupAgent Function**

**Purpose**:

- `POST /api/setupAgent`
- Receives user config with fields, possible enumerations, etc.
- Stores them in Storage.
- Calls Content Understanding’s `PUT /analyzers/{analyzerId}?api-version=...` to create the analyzer.
- Calls Azure AI Agent Service to create/update the agent with instructions plus 2 tool definitions: Artifact & ArtifactChunk.

**Sample**:

```python
# setup_agent_function/__init__.py

import azure.functions as func
import os, json, logging
import requests
from azure.storage.blob import BlobServiceClient
from .agent_service_utils import create_or_update_agent
from .content_understanding_utils import create_or_update_analyzer

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Received request for /api/setupAgent")

    try:
        body = req.get_json()
        # body might have: { fields: [...], template: "callCenter", instructions: "..."}
        schema_data = {
            "fields": body["fields"],
            "name": body.get("name", "customSchema"),
            "instructions": body.get("instructions", "You are a helpful agent by default.")
        }
        
        # 1) store config in storage
        blob_conn_str = os.environ["STORAGE_CONNECTION_STRING"]
        blob_client = BlobServiceClient.from_connection_string(blob_conn_str)
        container = blob_client.get_container_client("schemas")
        container.upload_blob(
            "user_config.json",
            json.dumps(schema_data),
            overwrite=True
        )

        # 2) create or update analyzer in Azure AI Content Understanding
        create_or_update_analyzer(schema_data)

        # 3) create or update agent in Azure AI Agent Service
        create_or_update_agent(schema_data)

        return func.HttpResponse(
            json.dumps({"status": "success"}),
            status_code=200,
            mimetype="application/json"
        )
    except Exception as e:
        logging.error(f"Error in setupAgent: {e}")
        return func.HttpResponse(str(e), status_code=500)
```

**Key Helpers**:

- `content_understanding_utils.create_or_update_analyzer(schema_data)`: Builds the JSON body for `PUT /contentunderstanding/analyzers/{id}?api-version=....`  
- `agent_service_utils.create_or_update_agent(schema_data)`: Uses the `azure.ai.projects` Python library (or raw REST calls) to define the agent + tools.

---

#### **4.2 File Upload Function**

**Purpose**:

- `POST /api/uploadFile`
- Receives a file from the front end, saves to Storage container “files/”.
- The blob trigger will handle ingestion.

```python
# upload_file_function/__init__.py

import azure.functions as func
import os
from azure.storage.blob import BlobServiceClient
import uuid

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        file = req.files.get("file")
        if not file:
            return func.HttpResponse("No file attached.", status_code=400)

        file_content = file.read()
        file_id = str(uuid.uuid4())
        file_name = f"{file_id}_{file.filename}"

        blob_conn_str = os.environ["STORAGE_CONNECTION_STRING"]
        blob_client = BlobServiceClient.from_connection_string(blob_conn_str)
        container = blob_client.get_container_client("files")
        container.upload_blob(file_name, file_content, overwrite=True)

        return func.HttpResponse(
            json.dumps({"fileId": file_id, "originalName": file.filename}),
            status_code=200,
            mimetype="application/json"
        )
    except Exception as e:
        return func.HttpResponse(str(e), status_code=500)
```

---

#### **4.3 Blob Trigger: Ingestion Function**

**Purpose**:

- Triggered whenever a new file is placed in `files/` container.
- Reads `schemas/user_config.json`.
- Calls Azure AI Content Understanding to analyze the new file.
- Extracts data from the result, merges or chunk them.
- Upserts the chunk(s) into **Azure AI Search** with `timestamp` field, user-defined fields, and summary.

```python
# ingestion_function/__init__.py
import os
import json
import logging
import azure.functions as func
from azure.storage.blob import BlobServiceClient
from .content_understanding_utils import analyze_file
from .search_utils import upsert_chunks_into_search

def main(myblob: func.InputStream):
    logging.info(f"Processing new blob: {myblob.name}, size: {myblob.length}")
    blob_name = myblob.name.split("/")[-1]  # e.g. <guid>_<filename>
    content = myblob.read()

    # 1) load user config
    blob_conn_str = os.environ["STORAGE_CONNECTION_STRING"]
    blob_client = BlobServiceClient.from_connection_string(blob_conn_str)
    container_client = blob_client.get_container_client("schemas")
    config_blob = container_client.get_blob_client("user_config.json")
    schema_json = json.loads(config_blob.download_blob().readall())

    # 2) call content understanding
    analyzer_id = schema_json.get("name", "customAnalyzer")
    analyze_result = analyze_file(analyzer_id, content)

    # 3) chunk data based on file type and user fields
    # e.g. parse out a summary, text blocks, timestamp, sentiment
    chunks = do_chunking(analyze_result, schema_json["fields"])

    # 4) upsert chunks to AI Search
    upsert_chunks_into_search(chunks)

    logging.info(f"Ingestion completed for {blob_name}")
```

Where:

- `content_understanding_utils.analyze_file(...)` calls the `POST /contentunderstanding/analyzers/{analyzer_id}:analyze?...` endpoint with either `analyzeBinary` or a SAS URL.
- `do_chunking(...)` merges the raw data from the analyzer, extracting the user’s fields plus a summary. If the file is PDF, chunk by headings; if audio, chunk by time intervals; etc.
- `upsert_chunks_into_search(chunks)` transforms each chunk to a search document with an `id`, a `timestamp` (ISO 8601), the `summary` if relevant, user-chosen fields, and possibly a vector embedding. Then calls `search_client.upload_documents(...)`.

---

#### **4.4 Artifact & ArtifactChunk Functions (the Agent Tools)**

We rename from “DocSearch” & “ArtifactInfo” to “Artifact” and “ArtifactChunk” as requested.

- **Artifact Function**: For high-level queries across entire artifacts. Possibly uses `$filter` on the “summary” or the “fields” in the index with `top=5`, returning a “list of artifacts.”

```python
# artifact_function/__init__.py
import azure.functions as func
import os, json
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential

def main(req: func.HttpRequest) -> func.HttpResponse:
    # agent calls this with JSON payload:
    # {
    #   "payload": {
    #       "filter": "...",
    #       "searchText": "...",
    #       ...
    #   }
    # }
    try:
        body = req.get_json()
        payload = body.get("payload", {})
        search_text = payload.get("searchText", "*")
        filter_expr = payload.get("filter", None)  # e.g. "timestamp gt 2023-09-01T00:00:00Z"

        search_client = create_search_client()

        # high-level artifact filter, probably we only retrieve doc-level entries (like "summary" docs) or documents with docType=artifact
        results = search_client.search(
            search_text=search_text,
            filter=filter_expr,
            top=5,
            select="id,timestamp,summary,peopleMentioned,sentiment"  # or whatever fields
        )
        docs = []
        for r in results:
            docs.append({
                "id": r["id"],
                "timestamp": r.get("timestamp"),
                "summary": r.get("summary"),
                "peopleMentioned": r.get("peopleMentioned"),
                "sentiment": r.get("sentiment")
            })

        return func.HttpResponse(json.dumps({"results": docs}), status_code=200, mimetype="application/json")
    except Exception as e:
        return func.HttpResponse(str(e), status_code=500)

def create_search_client():
    endpoint = os.environ["SEARCH_ENDPOINT"]
    api_key = os.environ["SEARCH_ADMIN_KEY"]  # or use DefaultAzureCredential if RBAC
    index_name = os.environ["SEARCH_INDEX_NAME"]  # e.g. "artifact-index"
    return SearchClient(endpoint, index_name, AzureKeyCredential(api_key))
```

- **ArtifactChunk Function**: For more granular chunk-level queries. This function can do question rewriting, use vector search with the `contentVector`, or standard text queries, and include `$filter` for timestamps or user fields.

```python
# artifactchunk_function/__init__.py
import azure.functions as func
import os, json
from azure.search.documents import SearchClient
from azure.search.documents.models import QueryType
from azure.core.credentials import AzureKeyCredential

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json()
        payload = body.get("payload", {})
        search_text = payload.get("searchText", "*")
        filter_expr = payload.get("filter", None)
        top_k = payload.get("topK", 5)
        questionRewriting = payload.get("questionRewriting", False)
        semanticRanking = payload.get("semanticRanking", False)

        client = create_search_client()
        # Potentially do advanced approach:
        # query rewriting -> multi-vector approach -> semantic ranking
        # For brevity, let's do a basic approach

        if semanticRanking:
            results = client.search(
                search_text=search_text,
                filter=filter_expr,
                top=top_k,
                query_type=QueryType.SEMANTIC,
                semantic_configuration_name="my-semantic-config"
            )
        else:
            results = client.search(
                search_text=search_text,
                filter=filter_expr,
                top=top_k
            )

        docs = []
        for r in results:
            docs.append({
                "id": r["id"],
                "timestamp": r.get("timestamp"),
                "chunkContent": r.get("content"),
                # any user fields
                "peopleMentioned": r.get("peopleMentioned"),
                "sentiment": r.get("sentiment"),
                # ...
                "@score": r["@search.score"]
            })

        return func.HttpResponse(json.dumps({"chunks": docs}), status_code=200, mimetype="application/json")
    except Exception as e:
        return func.HttpResponse(str(e), status_code=500)

def create_search_client():
    endpoint = os.environ["SEARCH_ENDPOINT"]
    api_key = os.environ["SEARCH_ADMIN_KEY"]
    index_name = os.environ["SEARCH_INDEX_NAME"]
    return SearchClient(endpoint, index_name, AzureKeyCredential(api_key))
```

In the agent:

- “Artifact” function → for summary-level or top-level queries.
- “ArtifactChunk” function → for chunk-level detail or advanced question rewriting.

---

### **5. Azure AI Agent Service: Tools Definition**

We define two tools, “Artifact” & “ArtifactChunk,” each with a single “payload” parameter that includes “searchText,” “filter,” “topK,” etc. The user can specify “timestamp” filters or enumerations in the “filter” property (like `"sentiment eq 'negative' and timestamp ge 2023-01-01T00:00:00Z"`).

**Example** `parameters` definition:

```json
{
  "type": "object",
  "properties": {
    "payload": {
      "type": "object",
      "properties": {
        "searchText": { "type": "string" },
        "filter": { "type": "string", "description": "OData filter expr. e.g. timestamp ge '2023-09-01T00:00:00Z' and sentiment eq 'negative'" },
        "topK": { "type": "number", "description": "Max number of docs" },
        "questionRewriting": { "type": "boolean" },
        "semanticRanking": { "type": "boolean" }
      },
      "required": ["searchText"]
    }
  },
  "required": ["payload"]
}
```

---

### **6. Front-End (FluentUI + Static Web Apps)**

**Key Components**:

- **Setup** (templates + custom fields). On “Save,” calls `/api/setupAgent`.  
- **FileUpload** to `/api/uploadFile`.  
- **Chat**:
  - For each user message, we call the Azure AI Agent Service to post a new user message in the thread.
  - The agent might call “Artifact” or “ArtifactChunk” internally if it needs data.
  - The final agent reply is displayed.

**One-Click**:

We can have a “Deploy to Azure” button referencing an ARM or Bicep template that sets up each resource:

- Azure Static Web App
- Azure Function App
- Azure Storage
- Azure AI Search
- Azure AI Agent Service (and content understanding)

Then the user only has to open the front end, pick a template, done.

---

### **7. Example Content Understanding Snippet**

`content_understanding_utils.py`:

```python
import os, json, requests

def create_or_update_analyzer(schema_data):
    analyzer_id = schema_data["name"]
    # Build a JSON body for the analyzer
    body = {
        "description": f"Analyzer for {analyzer_id}",
        "scenario": "document",  # or "audio" if needed
        "fieldSchema": {
            "fields": {}
        },
        "config": {
            "returnDetails": True
        }
    }

    # populate fieldSchema from schema_data["fields"]
    for f in schema_data["fields"]:
        field_name = f["name"]
        field_type = f.get("type","string")
        method = "extract"
        # you could do special mapping if it's "generate" or "classify"
        body["fieldSchema"]["fields"][field_name] = {
            "type": field_type,
            "method": method,
            "description": f.get("description","")
        }

    endpoint = os.environ["AI_ENDPOINT"]
    key = os.environ["AI_KEY"]
    api_version = "2024-12-01-preview"
    url = f"{endpoint}/contentunderstanding/analyzers/{analyzer_id}?api-version={api_version}"

    headers = {
        "Ocp-Apim-Subscription-Key": key,
        "Content-Type": "application/json"
    }

    resp = requests.put(url, headers=headers, data=json.dumps(body))
    resp.raise_for_status()

def analyze_file(analyzer_id, file_content):
    endpoint = os.environ["AI_ENDPOINT"]
    key = os.environ["AI_KEY"]
    api_version = "2024-12-01-preview"
    # We'll do analyzeBinary
    url = f"{endpoint}/contentunderstanding/analyzers/{analyzer_id}:analyze?_overload=analyzeBinary&api-version={api_version}"
    headers = {
        "Ocp-Apim-Subscription-Key": key,
        "Content-Type": "application/octet-stream"
    }
    resp = requests.post(url, headers=headers, data=file_content)
    resp.raise_for_status()
    return resp.json()
```

---

### **8. Summary**

**Implementation Steps**:

1. **Deploy** via ARM or Bicep template.  
2. **User** visits front end, picks or edits a template’s fields (like “timestamp,” “sentiment,” “peopleMentioned,” etc.).  
3. **Front end** calls `/api/setupAgent` → we create Content Understanding analyzer + Agent with “Artifact” & “ArtifactChunk” tools.  
4. **User** uploads files → triggers ingestion → calls Content Understanding → chunks → store in Azure AI Search.  
5. **User** chats → Agent calls “Artifact” or “ArtifactChunk” function with `$filter` or `searchText` to get results → final answer is displayed.

In this architecture, the user can set **timestamp** or **sentiment** filters, or any enumerations. The agent is aware of possible fields from the instructions or schema description. The **two** functions handle searching at different granularities, referencing the same or distinct indexes as you choose.

**Further Enhancements**:

- Vector embeddings for chunk text and a real multi-vector approach.
- Additional “summary” usage in the “Artifact” function to give high-level results.
- More advanced question rewriting at the “ArtifactChunk” function level.

This design meets the requirement of building an **Agentic RAG** accelerator in Python + Azure Functions, with:

- Content Understanding for ingestion  
- Azure AI Search for retrieval  
- Azure AI Agent with two function-based tools  
- User custom fields for schema  
- Timestamp (ISO 8601) for filtering in `$filter`.

---

# 2. **Refinements & Updates (Merged)**

Below are **added details** that expand the original doc, preserving its content while clarifying and providing extra code samples or usage notes:

---

## **A. More About Creating the Azure AI Search Index**

In section **2 (High-Level Diagram)** and **4 (Functions)**, we reference storing chunk-level or artifact-level data in **Azure AI Search**. Here’s a more thorough example of creating that index with code:

```python
# create_ai_search_index.py
import os
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField, SearchFieldDataType,
    SearchableField, SearchField,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile
)

def main():
    endpoint = os.getenv("SEARCH_ENDPOINT")
    admin_key = os.getenv("SEARCH_ADMIN_KEY")
    index_name = os.getenv("SEARCH_INDEX_NAME", "artifact-index")

    index_client = SearchIndexClient(endpoint, credential=AzureKeyCredential(admin_key))

    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SearchableField(name="content", type=SearchFieldDataType.String),
        SimpleField(name="timestamp", type=SearchFieldDataType.DateTimeOffset, filterable=True),
        SimpleField(name="sentiment", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="peopleMentioned", type=SearchFieldDataType.Collection(SearchFieldDataType.String), filterable=True),
        SearchField(name="contentVector", type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    searchable=True, vector_search_dimensions=1536,
                    vector_search_profile_name="myHnswProfile"),
    ]

    vector_search = VectorSearch(
        algorithms=[HnswAlgorithmConfiguration(name="myHnsw")],
        profiles=[VectorSearchProfile(name="myHnswProfile", algorithm_configuration_name="myHnsw")]
    )

    index = SearchIndex(
        name=index_name,
        fields=fields,
        vector_search=vector_search
    )

    result = index_client.create_or_update_index(index)
    print(f"Index {result.name} created or updated.")

if __name__ == "__main__":
    main()
```

You would run this script to initialize your Search index with a vector field plus standard fields like `timestamp`, `sentiment`, etc.

---

## **B. Additional Front-End Examples**

### B.1 Audio Playback

If your agent or chunk-level data references an audio URL plus a “startTime,” you can let users jump to that offset:

```tsx
// AudioPlayer.tsx
import React, { useRef } from 'react';
import { PrimaryButton } from '@fluentui/react';

interface AudioPlayerProps {
  audioUrl: string;
  jumpTime?: number;
}

export const AudioPlayer: React.FC<AudioPlayerProps> = ({ audioUrl, jumpTime }) => {
  const audioRef = useRef<HTMLAudioElement>(null);

  const handleJumpClick = () => {
    if (audioRef.current && jumpTime !== undefined) {
      audioRef.current.currentTime = jumpTime;
    }
  }

  return (
    <div>
      <audio ref={audioRef} controls style={{ width: '100%' }}>
        <source src={audioUrl} type="audio/mpeg" />
        Your browser does not support the audio element.
      </audio>
      {jumpTime !== undefined && (
        <PrimaryButton text="Jump to Segment" onClick={handleJumpClick} />
      )}
    </div>
  );
};
```

Then in your “Chat” component, if the agent returns something like:

```json
{
  "fileUrl": "https://myblob.../file.mp3",
  "jumpTime": 30
}
```

You can do:

```tsx
<AudioPlayer audioUrl={fileUrl} jumpTime={jumpTime} />
```

---

### B.2 File Upload UI

Here’s a minimal React snippet for uploading a file using a `<input type="file" />` and a FluentUI button:

```tsx
import React, { useState } from 'react';
import { PrimaryButton } from '@fluentui/react';

export const FileUploadComponent: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
    }
  };

  const onUploadClick = async () => {
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch('/api/uploadFile', {
      method: 'POST',
      body: formData
    });
    const data = await response.json();
    console.log("File uploaded result:", data);
  };

  return (
    <div>
      <input type="file" onChange={onFileChange} />
      <PrimaryButton text="Upload" onClick={onUploadClick} disabled={!file} />
    </div>
  );
};
```

---

## **C. More on Query Rewriting in ArtifactChunk**

We included a boolean param `questionRewriting` for advanced rewriting. If you want to do, for example, an LLM-based approach inside the function:

```python
if questionRewriting:
    # call an LLM to rewrite the user query
    search_text = do_llm_rewriting(search_text)
```

Or rely on the agent itself to do rewriting before it calls the function. This is optional but can significantly improve search recall.

---

## **D. Summaries vs. Chunk-Level Data**

The design suggests you might store a single “artifact” doc for the entire summary (with docType=artifact), and multiple “chunk” docs for detailed segments. Then:

- The **Artifact** function can filter where `docType = 'artifact'` for that top-level summary.  
- The **ArtifactChunk** function can filter where `docType = 'chunk'`, retrieving paragraph/time-slice data.  

One approach is to store them in the **same** index with a `docType` field.

---

## **E. Deployment Considerations**

- Provide a single “Deploy to Azure” button in the README that references your template (ARM or Bicep).  
- Ensure you define environment variables in the Function App for `STORAGE_CONNECTION_STRING`, `SEARCH_ENDPOINT`, `SEARCH_ADMIN_KEY`, `CU_ENDPOINT`, `CU_KEY`, etc.  
- The front end (Azure Static Web Apps) can be built with `npm run build` or similar, and automatically connected to your Functions app.
