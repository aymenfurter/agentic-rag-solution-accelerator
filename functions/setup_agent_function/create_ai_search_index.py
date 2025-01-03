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

def create_base_fields(prefix=""):
    """Create base fields common to both indexes"""
    return [
        SimpleField(name=f"{prefix}id", type=SearchFieldDataType.String, key=True),
        SearchableField(name=f"{prefix}content", type=SearchFieldDataType.String, analyzer_name="standard.lucene"),
        SimpleField(name=f"{prefix}docType", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name=f"{prefix}timestamp", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
        SimpleField(name=f"{prefix}fileName", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name=f"{prefix}segmentStartTime", type=SearchFieldDataType.Int64, filterable=True),
        SimpleField(name=f"{prefix}segmentEndTime", type=SearchFieldDataType.Int64, filterable=True),
        SearchField(
            name=f"{prefix}contentVector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=1536,
            vector_search_profile_name="myHnswProfile"
        ),
    ]

def create_search_indexes(fields_config=None):
    """Create or update Azure AI Search indexes for artifacts and chunks"""
    endpoint = os.getenv("SEARCH_ENDPOINT")
    admin_key = os.getenv("SEARCH_ADMIN_KEY")
    
    if not endpoint or not admin_key:
        raise ValueError("Missing required environment variables")

    index_client = SearchIndexClient(endpoint, credential=AzureKeyCredential(admin_key))

    # Create artifact index with user-defined fields
    artifact_fields = create_base_fields()
    if fields_config:
        for field in fields_config:
            field_name = field["name"]
            field_type = field["type"]
            
            if field_type == "string":
                artifact_fields.append(
                    SimpleField(
                        name=field_name,
                        type=SearchFieldDataType.String,
                        filterable=True,
                        facetable=True,
                        nullable=True  # Make string fields nullable
                    )
                )
            elif field_type == "array":
                artifact_fields.append(
                    SimpleField(
                        name=field_name,
                        type=SearchFieldDataType.Collection(SearchFieldDataType.String),
                        filterable=True,
                        facetable=True,
                        nullable=True  # Make array fields nullable
                    )
                )
            elif field_type == "table":
                # Handle table fields as nested structures
                for subfield in field.get("fields", []):
                    artifact_fields.append(
                        SimpleField(
                            name=f"{field_name}_{subfield['name']}",
                            type=SearchFieldDataType.String,
                            filterable=True
                        )
                    )

    # Create chunk index with chunk-prefixed fields
    chunk_fields = create_base_fields("chunk_")

    # Common vector and semantic configurations
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

    # Update semantic configurations to use correct field names
    artifact_semantic_config = SemanticConfiguration(
        name="default",
        prioritized_fields=SemanticPrioritizedFields(
            content_fields=[SemanticField(field_name="content")],
            keywords_fields=[SemanticField(field_name="fileName")]
        )
    )

    chunk_semantic_config = SemanticConfiguration(
        name="default",
        prioritized_fields=SemanticPrioritizedFields(
            content_fields=[SemanticField(field_name="chunk_content")],
            keywords_fields=[SemanticField(field_name="chunk_fileName")]
        )
    )

    semantic_search_artifact = SemanticSearch(configurations=[artifact_semantic_config])
    semantic_search_chunk = SemanticSearch(configurations=[chunk_semantic_config])

    # Create both indexes with their respective semantic configurations
    artifact_index = SearchIndex(
        name="artifacts",
        fields=artifact_fields,
        vector_search=vector_search,
        semantic_search=semantic_search_artifact
    )

    chunk_index = SearchIndex(
        name="chunks",
        fields=chunk_fields,
        vector_search=vector_search,
        semantic_search=semantic_search_chunk
    )

    try:
        index_client.create_or_update_index(artifact_index)
        index_client.create_or_update_index(chunk_index)
        return {
            "artifacts_index": artifact_index.name,
            "chunks_index": chunk_index.name
        }
    except Exception as e:
        print(f"Error creating/updating indexes: {str(e)}")
        raise