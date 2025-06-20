# models.py - Data models for API requests and responses
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Union

# Request Models
class VideoRequest(BaseModel):
    """Request to process a YouTube video"""
    url: str

class QuestionRequest(BaseModel):
    """Request to ask a question about a video"""
    url: str
    question: str
    use_cached_transcript: Optional[bool] = False

# Data Structure Models
class TranscriptSegment(BaseModel):
    """Individual transcript segment with timing information"""
    text: str
    start: float
    end: float
    start_formatted: str
    end_formatted: str

class StructuredTranscript(BaseModel):
    """Complete transcript data with timestamps"""
    transcript_text: str
    structured_data: List[TranscriptSegment]
    has_timestamps: bool
    total_segments: int

# Response Models
class VideoResponse(BaseModel):
    """Response from video processing"""
    success: bool
    video_title: Optional[str] = None
    transcript: Optional[Union[str, Dict[str, Any]]] = None  # Can be string or structured data
    method_used: Optional[str] = None
    message: str
    error: Optional[str] = None

class QuestionResponse(BaseModel):
    """Response from AI question answering"""
    success: bool
    question: str
    answer: Optional[str] = None
    video_title: Optional[str] = None
    method_used: Optional[str] = None
    message: str
    error: Optional[str] = None
    timestamps: Optional[List[Dict]] = None
    has_timestamps: Optional[bool] = None