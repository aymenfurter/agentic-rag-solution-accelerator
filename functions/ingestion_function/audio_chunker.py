from typing import List, Dict, Any
import re
from datetime import datetime
import logging

class AudioTranscriptChunker:
    """Chunks audio transcripts from WEBVTT format while preserving timestamp information"""
    
    def __init__(self, chunk_size: int = 10, overlap: int = 2):
        """Initialize with number of segments per chunk"""
        self.chunk_size = chunk_size
        self.overlap = overlap

    def parse_webvtt(self, markdown_content: str) -> List[Dict[str, Any]]:
        """Parse WEBVTT format from markdown code block"""
        if not isinstance(markdown_content, str):
            logging.warning("Markdown content is not a string")
            return []
            
        logging.info(f"Parsing WEBVTT content: {markdown_content[:200]}...")
        
        # Match timestamps and text with or without speaker tags
        pattern = r'(\d{2}:\d{2}\.\d{3}) --> (\d{2}:\d{2}\.\d{3})\n(?:<v ([^>]+)>)?([^\n]+)'
        matches = re.finditer(pattern, markdown_content, re.MULTILINE)
        
        segments = []
        for match in matches:
            start_time, end_time, speaker, text = match.groups()
            
            # Handle cases where speaker tag might be missing
            if not speaker:
                speaker = "Speaker"
            
            # Convert time to milliseconds
            start_ms = self.timestamp_to_ms(start_time)
            end_ms = self.timestamp_to_ms(end_time)
            
            segments.append({
                "startTimeMs": start_ms,
                "endTimeMs": end_ms,
                "speaker": speaker.strip(),
                "text": text.strip()
            })
            
        logging.info(f"Found {len(segments)} segments")
        return segments

    def timestamp_to_ms(self, timestamp: str) -> int:
        """Convert WEBVTT timestamp to milliseconds"""
        try:
            minutes, seconds = timestamp.split(':')
            total_seconds = int(minutes) * 60 + float(seconds)
            return int(total_seconds * 1000)
        except Exception as e:
            logging.error(f"Error converting timestamp {timestamp}: {str(e)}")
            return 0

    def create_chunks(
        self,
        content: str,
        metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Create overlapping chunks from WEBVTT content"""
        segments = self.parse_webvtt(content)
        chunks = []
        
        # Process segments in overlapping windows
        for i in range(0, len(segments), self.chunk_size - self.overlap):
            window = segments[i:i + self.chunk_size]
            if not window:
                continue
            
            # Get time range
            start_time = window[0]["startTimeMs"]
            end_time = window[-1]["endTimeMs"]
            
            # Combine text with speaker attribution
            chunk_content = "\n".join(
                f"[{s['speaker']}] {s['text']}"
                for s in window
            )
            
            # Use chunk_ prefix for all fields in chunks
            chunk = {
                "chunk_id": f"{metadata['id']}_chunk_{i//self.chunk_size}",  # Use chunk_id for chunks
                "chunk_content": chunk_content,
                "chunk_docType": "chunk",
                "chunk_fileName": metadata["fileName"],
                "chunk_timestamp": metadata["timestamp"],
                "chunk_segmentStartTime": start_time,
                "chunk_segmentEndTime": end_time
            }
            
            # Add metadata fields with chunk_ prefix
            for k, v in metadata.items():
                if k not in ["id", "fileName", "timestamp", "docType"]:
                    chunk[f"chunk_{k}"] = v
            
            chunks.append(chunk)
            
        return chunks