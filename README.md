# Agentic RAG on Azure (Early Development)

We’re living in a time when ingesting unstructured content—audio, documents, images, or even videos—no longer has to mean wrestling with half a dozen separate frameworks or writing a labyrinth of custom LLM prompts. **Azure AI Content Understanding** and **Azure AI Agent Service**, both fresh from Microsoft Ignite 2024, simplify this entire process significantly. 

I’ve been working on a **“Agentic RAG Solution Accelerator”** to illustrate how you can combine these services (with **Azure Functions** and **Azure AI Search** in tow) to build flexible, robust retrieval experiences. This accelerator is **still in development**—it’s fully end-to-end, but I plan to keep iterating on indexing performance, chunking, query rewriting, vector search. Nevertheless, it already stands up a working pipeline with minimal code, letting the AI decide how best to query your data.

---

## 1. Why Agentic? A Quick Overview

“Agentic” means that the AI can decide, in real time, which filters to apply or which search function to call—no elaborate prompt engineering or manually gluing together calls. You define tools (like your search function), and **Azure AI Agent Service** can use them automatically. Meanwhile, **Azure AI Content Understanding** spares you from writing custom LLM logic for extracting structured fields from your data.

If you’ve ever tried to unify call center audio or PDF-based invoice data into a single retrieval flow, you’ll know the frustration: speech-to-text plus sentiment plus summarization plus indexing plus… it grows quickly. My accelerator aims to unify these tasks into one cohesive RAG approach, with the agent orchestrating queries on the fly.

---

## 2. Azure AI Content Understanding and Azure AI Agent Service at a Glance

- **Azure AI Content Understanding**  
  Think of this as your “one-stop analyzer” for diverse data (audio, PDFs, images, videos). You specify the fields you want—maybe “sentiment,” “summary,” or “vendor name”—and Content Understanding delivers them in structured form. For PDFs, you typically get “extract-only,” whereas for audio, you might do more advanced generative tasks.  

- **Azure AI Agent Service**  
  Built on top of OpenAI’s assistant model, but with extra superpowers: it can “call” Azure Functions directly. So if a user query suggests searching for negative calls, the agent can pass `filter = "sentiment eq 'negative'"` to your function, then merge the results. No more trying to coerce the LLM with a massive system prompt. Just define your tool, and the service handles the rest. This reduces the overhead in building retrieval-augmented solutions, especially when you don’t want to craft a your own prompts or manually orchestrate function calls.

Azure AI Agent Service comes in two SKUs: Basic and Standard. With Basic, the dependent resources of the AI Foundry service are managed by Microsoft, while with Standard, you need to create and manage those resources yourself. Note that Azure Function integration for AI Agents is only available with the Standard SKU. 
---

## 3. A Sample Schema for Invoices

Before we jump into the call center scenario, let’s look at another example to highlight how **Content Understanding** can parse structured fields. For instance, analyzing invoices might mean extracting vendor names, line items, and amounts. Below is a simplified JSON schema:

```json
{
  "description": "Sample invoice analyzer",
  "scenario": "document",
  "config": {
    "returnDetails": true
  },
  "fieldSchema": {
    "fields": {
      "VendorName": {
        "type": "string",
        "method": "extract",
        "description": "Vendor issuing the invoice"
      },
      "Items": {
        "type": "array",
        "method": "extract",
        "items": {
          "type": "object",
          "properties": {
            "Description": {
              "type": "string",
              "method": "extract",
              "description": "Description of the item"
            },
            "Amount": {
              "type": "number",
              "method": "extract",
              "description": "Amount of the item"
            }
          }
        }
      }
    }
  }
}
```

This analyzer looks for a `VendorName`, then parses an `Items` array. Each item has a `Description` and an `Amount`. Once processed, you can feed this structure into your indexing or automation flows without hand-writing custom LLM prompts for each field. It’s all declared right here in the schema, letting Content Understanding handle the grunt work.

---

## 4. Tying Ingestion & Indexing Together with Azure Functions & Azure AI Search

After defining your analyzer (be it for invoices, call center audio, or something else), you can upload files to Blob Storage. A **blob-triggered Azure Function** fires each time a new file lands, calls `analyze_file(...)` with your chosen analyzer, then indexes the results in **Azure AI Search**.

Here’s a simplified ingestion snippet:

```python
import azure.functions as func
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential

def main(myblob: func.InputStream):
    try:
        content = myblob.read()
        blob_name = myblob.name.split("/")[-1]

        # e.g. read user_config to get the active analyzer name
        analyzer_id = "callcenter-review-agent"

        analyze_result = analyze_file(analyzer_id, content)
        # parse the contents, create artifact_doc, chunk_docs, etc.
        ...

        # Index them in Azure AI Search
        search_endpoint = os.environ["SEARCH_ENDPOINT"]
        search_key = os.environ["SEARCH_ADMIN_KEY"]
        artifact_client = SearchClient(search_endpoint, "artifacts", AzureKeyCredential(search_key))
        chunk_client = SearchClient(search_endpoint, "chunks", AzureKeyCredential(search_key))

        artifact_client.upload_documents([artifact_doc])
        chunk_client.upload_documents(chunk_docs)

    except Exception as e:
        # Log error, handle gracefully
        pass
```

Because **Content Understanding** can handle multiple data types, you can mix and match “extract” or “generate” depending on your scenario. For PDFs or Word docs, “extract” is typical (like the invoice example). For audio, you might do “generate” to get a summary or sentiment. All of it ends up in your AI Search index, ready for queries.

---

## 5. Defining an Agent in Azure AI Agent Service

Now that your content is parsed and indexed, how do we let users query it? Enter **Azure AI Agent Service**. It’s a *managed LLM orchestration* layer where you register “tools.” In this accelerator, your “Artifact” or “ArtifactChunk” functions become those tools. The agent can decide on its own if it should call them, and merges the retrieved info into its final answer.

A snippet for creating the agent:

```python
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import AzureFunctionStorageQueue, AzureFunctionTool
from azure.identity import DefaultAzureCredential
import os

def create_or_update_agent(schema_data):
    credential = DefaultAzureCredential()
    project_client = AIProjectClient.from_connection_string(
        credential=credential,
        conn_str=os.environ["AI_PROJECT_CONNECTION_STRING"]
    )

    agent_name = schema_data["name"]
    
    artifact_tool = AzureFunctionTool(
        name="Artifact",
        description="High-level semantic search on artifacts",
        parameters={
            "type": "object",
            "properties": {
                "searchText": {"type": "string"},
                "filter": {"type": "string"},
                "outputqueueuri": {"type": "string"}
            }
        },
        input_queue=AzureFunctionStorageQueue(
            queue_name="artifact-input",
            storage_service_endpoint=f"https://{os.environ['STORAGE_ACCOUNT_NAME']}.queue.core.windows.net"
        ),
        output_queue=AzureFunctionStorageQueue(
            queue_name="artifact-output",
            storage_service_endpoint=f"https://{os.environ['STORAGE_ACCOUNT_NAME']}.queue.core.windows.net"
        )
    )

    instructions = (
        f"You are an AI agent with access to the following fields: "
        f"{[f['name'] for f in schema_data['fields']]}\n"
        "You can call 'Artifact' or 'ArtifactChunk' to retrieve data.\n"
        f"Scenario instructions: {schema_data['instructions']}"
    )

    agent = project_client.agents.create_agent(
        model=os.environ["GPT_DEPLOYMENT_NAME"],
        name=agent_name,
        instructions=instructions,
        tools=artifact_tool.definitions
    )
    return agent
```

Once set up, the agent can autonomously decide if a user query requires a filter (e.g., `category eq 'invoice'`) or a semantic search. You just define the search function. The agent does the rest.

---

## 6. Bringing It All Together with a Chat Endpoint

The final piece is a user-facing “chat” endpoint, typically an **HTTP-triggered Azure Function**. When a user sends “Find me calls about shipping delays,” the function:

1. Posts that message to the agent’s thread.  
2. Creates a “run,” letting the agent handle the new question.  
3. The agent might call your Artifact function to do a search.  
4. The agent returns the final answer (and you can optionally log the tool calls for debugging).

Here’s a sample:

```python
import azure.functions as func
import logging
import json
import time
from .initialize_client import initialize_client  # your code to get project_client & agent_id

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Starting chat request processing')
    
    try:
        req_body = req.get_json()
        prompt = req_body.get('prompt')
        thread_id = req_body.get('threadId')
        
        logging.info(f'Received request - Thread ID: {thread_id}, Prompt: {prompt}')
        
        # Initialize client & agent info
        project_client, agent_id = initialize_client()
        
        # If no threadId, create a new thread
        if not thread_id:
            logging.info('No thread ID provided, creating new thread')
            thread = project_client.agents.create_thread()
            return func.HttpResponse(
                json.dumps({"threadId": thread.id}),
                mimetype="application/json",
                status_code=200
            )
            
        if not prompt:
            logging.warning('No prompt provided')
            return func.HttpResponse("Missing prompt", status_code=400)
            
        # Attempt to retrieve the existing thread, or create a new one if not found
        try:
            logging.info(f'Retrieving thread {thread_id}')
            thread = project_client.agents.get_thread(thread_id)
        except Exception as e:
            logging.warning(f'Failed to get thread, creating new one: {str(e)}')
            thread = project_client.agents.create_thread()
            thread_id = thread.id
        
        # Post the user’s message
        message = project_client.agents.create_message(
            thread_id=thread_id,
            role="user",
            content=prompt,
        )
        
        # Create a run so the agent processes this message
        run = project_client.agents.create_run(
            thread_id=thread_id,
            assistant_id=agent_id
        )
        
        # Poll until run completes or time out
        start_time = time.time()
        timeout = 60
        while run.status in ["queued", "in_progress", "requires_action"]:
            if time.time() - start_time > timeout:
                project_client.agents.cancel_run(thread_id=thread.id, run_id=run.id)
                raise Exception("Run timed out after 60 seconds")
            time.sleep(1)
            run = project_client.agents.get_run(thread_id=thread_id, run_id=run.id)
        
        if run.status == "failed":
            raise Exception(f"Run failed: {run.last_error}")

        # Retrieve messages and locate the final assistant response
        messages = project_client.agents.list_messages(thread_id=thread_id)
        assistant_messages = [m for m in messages.data if m.role == "assistant"]
        if not assistant_messages:
            raise Exception("No response received from assistant")
        
        last_msg = assistant_messages[0]
        
        # (Optional) fetch run steps to see tool calls
        steps = project_client.agents.list_run_steps(thread_id=thread_id, run_id=run.id)
        steps_data = [json.loads(json.dumps(vars(step), default=str)) for step in steps.data]

        response = {
            "role": "assistant",
            "content": last_msg.content[0].text.value if last_msg.content else "",
            "timestamp": last_msg.created_at.isoformat(),
            "steps": steps_data
        }
        
        return func.HttpResponse(
            json.dumps(response),
            mimetype="application/json",
            status_code=200
        )
        
    except Exception as e:
        error_msg = f"Chat function error: {str(e)}"
        logging.error(error_msg)
        return func.HttpResponse(json.dumps({"error": error_msg}), status_code=500)
```

### How It All Works

1. **User** sends a `POST` with `prompt` and optionally a `threadId`.  
2. If there’s no `threadId`, we create a new conversation thread.  
3. The user message is posted to that thread.  
4. We create a “run” with the agent, which triggers the orchestration.  
5. The agent might call your search function to retrieve data or might respond directly if it has everything it needs.  
6. We wait for the run to finish, then return the final assistant response.  

---

## 7. Current Status and What’s Next

Right now, this **Agentic RAG Solution Accelerator** already demonstrates:

- **Template-based ingestion**: You pick or customize a scenario (invoice docs, call center audio, etc.).  
- **Automated indexing**: A blob-triggered Azure Function calls Content Understanding for each file, then loads the structured data into AI Search.  
- **Agent**-driven retrieval: The agent automatically calls your search function when user queries require more data.

However, this is **still a work in progress**. I plan to improve:

1. **Indexing performance** for large volumes or big files.  
2. **Chunking** for more granular retrieval.  
3. **Vector-based approaches** to enable semantic or hybrid search.  
4. **Query rewriting** so the agent can refine user queries more elegantly.

Despite being in early development, it’s already remarkable how well these Azure services fit together without needing layers of custom code or elaborate prompt engineering. 

---

## Conclusion

By defining simple (or elaborate) schemas, **Azure AI Content Understanding** can parse audio, PDF, or other data with minimal fuss, returning exactly the fields you need. Storing those fields in **Azure AI Search** and hooking them up to **Azure AI Agent Service** means your AI can dynamically decide which queries to run, giving you a fully agentic retrieval experience. 

Yes, there’s more to do—improved chunking, vector indexing, advanced ranking—but even at this stage, the synergy is clear: you configure a few templates and tasks, and the AI takes care of the rest. I’m excited to keep refining this accelerator. Hopefully, it inspires you to explore how Azure’s new generation of AI services can simplify your RAG workflows!
