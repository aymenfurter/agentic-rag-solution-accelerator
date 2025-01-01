# /shared/create_ai_search_index.py
import os
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchFieldDataType,
    SearchableField,
    SearchField,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
    SemanticConfiguration,
    SemanticPrioritizedFields,
    SemanticField,
    SemanticSearch
)

def create_search_index(fields_config=None):
    """
    Create or update an Azure AI Search index with vector search capabilities
    and semantic search configuration.
    
    Args:
        fields_config (dict, optional): User-defined fields configuration
    """
    endpoint = os.getenv("SEARCH_ENDPOINT")
    admin_key = os.getenv("SEARCH_ADMIN_KEY")
    index_name = os.getenv("SEARCH_INDEX_NAME", "artifact-index")

    if not endpoint or not admin_key:
        raise ValueError("Missing required environment variables SEARCH_ENDPOINT or SEARCH_ADMIN_KEY")

    index_client = SearchIndexClient(endpoint, credential=AzureKeyCredential(admin_key))

    # Base fields that are always present
    base_fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SearchableField(name="content", type=SearchFieldDataType.String, analyzer_name="standard.lucene"),
        SimpleField(name="docType", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="timestamp", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
        SimpleField(name="artifactId", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="fileName", type=SearchFieldDataType.String, filterable=True),
        SearchableField(name="summary", type=SearchFieldDataType.String),
        SearchField(
            name="contentVector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=1536,
            vector_search_profile_name="myHnswProfile"
        ),
    ]

    # Add user-defined fields if provided
    fields = base_fields.copy()
    if fields_config:
        for field in fields_config:
            field_name = field["name"]
            field_type = field["type"]
            
            if field_type == "string":
                fields.append(
                    SimpleField(
                        name=field_name,
                        type=SearchFieldDataType.String,
                        filterable=True
                    )
                )
            elif field_type == "array":
                fields.append(
                    SimpleField(
                        name=field_name,
                        type=SearchFieldDataType.Collection(SearchFieldDataType.String),
                        filterable=True
                    )
                )
            elif field_type == "date":
                fields.append(
                    SimpleField(
                        name=field_name,
                        type=SearchFieldDataType.DateTimeOffset,
                        filterable=True,
                        sortable=True
                    )
                )

    # Vector search configuration
    vector_search = VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(
                name="myHnsw",
                parameters={
                    "m": 4,
                    "efConstruction": 400,
                    "efSearch": 500,
                    "metric": "cosine"
                }
            )
        ],
        profiles=[
            VectorSearchProfile(
                name="myHnswProfile",
                algorithm_configuration_name="myHnsw"
            )
        ]
    )

    # Updated semantic configuration
    semantic_config = SemanticConfiguration(
        name="default",
        prioritized_fields=SemanticPrioritizedFields(
            content_fields=[SemanticField(field_name="content")],
            keywords_fields=[SemanticField(field_name="summary")]
        )
    )

    # Create the semantic settings with the configuration
    semantic_search = SemanticSearch(configurations=[semantic_config])

    # Create the index
    index = SearchIndex(
        name=index_name,
        fields=fields,
        vector_search=vector_search,
        semantic_search=semantic_search
    )

    try:
        result = index_client.create_or_update_index(index)
        print(f"Index {result.name} created or updated successfully")
        return result
    except Exception as e:
        print(f"Error creating/updating index: {str(e)}")
        raise