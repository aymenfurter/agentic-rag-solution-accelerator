# /shared/chunking/markdown_chunker.py
import re
from typing import List, Dict, Any
from datetime import datetime

def format_datetime(dt):
    """Format datetime in ISO 8601 format with Z suffix"""
    return dt.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

class MarkdownChunker:
    """Markdown document chunker with header preservation"""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 100):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def create_chunks(
        self,
        content: str,
        metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Chunk markdown content preserving header structure
        """
        chunks = []
        lines = content.split("\n")
        
        current_chunk = []
        current_headers = {}
        chunk_number = 0
        current_code_block = False
        code_fence = ""
        
        for line in lines:
            # Handle code blocks
            if line.strip().startswith("```"):
                if not current_code_block:
                    current_code_block = True
                    code_fence = "```"
                elif code_fence == "```":
                    current_code_block = False
                    code_fence = ""
            elif line.strip().startswith("~~~"):
                if not current_code_block:
                    current_code_block = True
                    code_fence = "~~~"
                elif code_fence == "~~~":
                    current_code_block = False
                    code_fence = ""

            # If in code block, keep adding lines
            if current_code_block:
                current_chunk.append(line)
                continue

            # Check for headers
            header_match = re.match(r"^(#{1,6})\s+(.+)$", line)
            if header_match:
                # If we have content, create a chunk before starting new section
                if current_chunk:
                    chunk_id = f"{metadata['artifactId']}_chunk_{chunk_number}"
                    chunk_content = "\n".join(current_chunk)
                    chunk_data = self._create_chunk(chunk_id, chunk_content, metadata)
                    chunk_data.update({"headers": current_headers.copy()})
                    chunks.append(chunk_data)
                    chunk_number += 1
                    current_chunk = []

                # Update current headers
                level = len(header_match.group(1))
                header_text = header_match.group(2)
                current_headers[f"h{level}"] = header_text
                # Clear any lower-level headers
                current_headers = {k:v for k,v in current_headers.items() if int(k[1]) <= level}
                
            # Add line to current chunk
            current_chunk.append(line)
            
            # Check if current chunk is too large
            if len("\n".join(current_chunk)) >= self.chunk_size:
                chunk_id = f"{metadata['artifactId']}_chunk_{chunk_number}"
                chunk_content = "\n".join(current_chunk)
                chunk_data = self._create_chunk(chunk_id, chunk_content, metadata)
                chunk_data.update({"headers": current_headers.copy()})
                chunks.append(chunk_data)
                chunk_number += 1
                # Keep overlap portion
                overlap_lines = current_chunk[-self.chunk_overlap:]
                current_chunk = overlap_lines

        # Add final chunk if any content remains
        if current_chunk:
            chunk_id = f"{metadata['artifactId']}_chunk_{chunk_number}"
            chunk_content = "\n".join(current_chunk)
            chunk_data = self._create_chunk(chunk_id, chunk_content, metadata)
            chunk_data.update({"headers": current_headers.copy()})
            chunks.append(chunk_data)

        return chunks

    def _create_chunk(
        self,
        chunk_id: str,
        content: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create chunk document with common fields"""
        # Ensure timestamp is properly formatted
        chunk_metadata = {
            k: format_datetime(v) if k == 'timestamp' else v 
            for k, v in metadata.items()
        }
        
        return {
            "id": chunk_id,
            "content": content,
            "docType": "chunk",
            "artifactId": chunk_metadata.get("artifactId"),
            "fileName": chunk_metadata.get("fileName"),
            "timestamp": chunk_metadata.get("timestamp"),
            **{k:v for k,v in chunk_metadata.items() 
               if k not in ["artifactId", "fileName", "timestamp"]}
        }