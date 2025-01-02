# /shared/chunking/audio_chunker.py
from typing import List, NamedTuple, Dict, Any
import re
from datetime import datetime
import logging

class Segment(NamedTuple):
    """Represents a segment of transcribed audio"""
    content: str
    timestamp: str
    full_segment: str
    plain_segment: str

class AudioTranscriptChunker:
    """Chunks audio transcripts while preserving timestamp information"""
    
    def __init__(self, overlap: int = 20, chunk_size: int = 60):
        """
        Initialize the transcript chunker
        
        Args:
            overlap: Number of overlapping phrases between chunks
            chunk_size: Number of phrases per chunk
        """
        if overlap > chunk_size:
            raise ValueError("Overlap cannot exceed chunk size.")
        self.overlap = overlap
        self.chunk_size = chunk_size

    def create_chunks(
        self,
        text_data: str,
        metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Create chunks from timestamped transcript
        
        Args:
            text_data: Timestamped transcript text
            metadata: Document metadata
            
        Returns:
            List of chunk documents for search indexing
        """
        logging.info(f"Creating chunks from text data of length: {len(text_data)}")
        logging.info(f"First 200 chars of text: {text_data[:200]}")
        logging.info(f"Metadata received: {metadata}")
        
        segments = self.split_transcript(text_data)
        logging.info(f"Created {len(segments)} segments")
        
        chunks = []
        
        for i, segment in enumerate(segments):
            chunk_id = f"{metadata['artifactId']}_chunk_{i}"
            logging.info(f"Processing segment {i} with timestamp: {segment.timestamp}")
            
            # Create chunk document
            chunk = {
                "id": chunk_id,
                "content": segment.content,
                "docType": "chunk",
                "artifactId": metadata.get("artifactId"),
                "fileName": metadata.get("fileName"),
                "timestamp": metadata.get("timestamp", datetime.utcnow().isoformat()),
                "segmentTimestamp": segment.timestamp,
                "fullSegment": segment.full_segment,
                "plainSegment": segment.plain_segment,
                **{k:v for k,v in metadata.items() if k not in ["artifactId", "fileName", "timestamp"]}
            }
            
            chunks.append(chunk)
            
        logging.info(f"Returning {len(chunks)} chunks")
        return chunks

    def split_transcript(self, text_data: str) -> List[Segment]:
        """
        Split transcript into segments
        
        Args:
            text_data: Timestamped transcript text
            
        Returns:
            List of Segment objects
        """
        logging.info("Splitting transcript into segments")
        phrases = self._parse_phrases(text_data)
        logging.info(f"Found {len(phrases)} phrases")
        
        if len(phrases) == 0:
            logging.warning("No phrases found in transcript")
            return []
            
        # If total phrases less than chunk size, return single segment
        if len(phrases) < self.chunk_size:
            logging.info(f"Phrases count ({len(phrases)}) less than chunk size ({self.chunk_size}), creating single segment")
            return [self._create_segment(phrases)]
            
        # Calculate stride for overlapping chunks
        stride = self.chunk_size - self.overlap
        
        # Create overlapping segments
        return [
            self._create_segment(phrases[i:i + self.chunk_size])
            for i in range(0, len(phrases) - self.chunk_size + 1, stride)
        ]

    def _create_segment(self, phrases: List[tuple]) -> Segment:
        """
        Create a segment from a list of timestamped phrases
        
        Args:
            phrases: List of (timestamp, text) tuples
            
        Returns:
            Segment object
        """
        if not phrases:
            logging.warning("Attempting to create segment from empty phrases list")
            return Segment("", "00:00:00", "", "")
            
        logging.info(f"Creating segment from {len(phrases)} phrases")
        logging.info(f"First phrase: {phrases[0]}")
        
        timestamp = phrases[0][0]
        content = ' '.join(p[1] for p in phrases)
        full_segment = ' '.join(f'[{t}] {s}' for t, s in phrases)
        plain_segment = ' '.join(s for _, s in phrases)
        
        return Segment(content, timestamp, full_segment, plain_segment)

    def _parse_phrases(self, transcript: str) -> List[tuple]:
        """
        Parse timestamped phrases from transcript
        
        Args:
            transcript: Timestamped transcript text
            
        Returns:
            List of (timestamp, text) tuples
        """
        logging.info("Parsing phrases from transcript")
        phrases = re.findall(
            r'\[(\d{2}:\d{2}:\d{2})\]\s(.+?)(?=\s\[\d{2}:\d{2}:\d{2}\]|\Z)',
            transcript
        )
        logging.info(f"Found {len(phrases)} phrases using regex")
        if len(phrases) == 0:
            logging.warning("Regex pattern found no matches in transcript")
            logging.info(f"Transcript sample: {transcript[:200]}")
        return phrases