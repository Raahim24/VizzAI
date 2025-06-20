# endpoints.py - Simple API routes for video analysis
from fastapi import APIRouter, HTTPException
from .models import VideoRequest, QuestionRequest, VideoResponse, QuestionResponse
from .cache import get_cached_transcript, cache_transcript, is_cached, clear_cache, get_cache_stats
from processors.video_analysis_coordinator import VideoAnalysisCoordinator
from processors.youtube_processor import YouTubeProcessor

# Create router for all API endpoints
router = APIRouter()

# Set up the main coordinator that handles everything
coordinator = VideoAnalysisCoordinator()

def validate_youtube_url(url: str) -> None:
    """
    Check if YouTube URL is valid and raise error if not
    Saves us from repeating this code in multiple functions
    """
    if not url or not url.strip():
        raise HTTPException(status_code=400, detail="Please provide a YouTube URL")
    
    if "youtube.com" not in url and "youtu.be" not in url:
        raise HTTPException(status_code=400, detail="Please provide a valid YouTube URL")

@router.get("/")
async def welcome():
    """
    Welcome page that shows what this API can do
    Lists all available endpoints and features
    """
    return {
        "message": "Welcome to the Video Analysis API!",
        "features": [
            "Extract transcripts from YouTube videos",
            "Ask questions about video content",
            "Visual analysis - Ask about what you see in videos",
            "Smart caching for faster responses"
        ],
        "endpoints": {
            "smart_question": "POST /smart-question - Ask any question about a video",
            "ask_question": "POST /ask-question - Ask AI about video content",
            "process_video": "POST /process-youtube - Extract transcript only",
            "summarize_video": "POST /summarize-video - Get video summary",
            "health": "GET /health - Check if server is working",
            "cache_stats": "GET /cache-stats - View cache information",
            "clear_cache": "GET /clear-cache - Clear cached data"
        }
    }

@router.get("/health")
async def health_check():
    """
    Check if the server and all components are working properly
    Returns status of processors and capabilities
    """
    try:
        stats = coordinator.get_analysis_stats()
        
        return {
            "status": "Server is running!",
            "processors": stats["processors_loaded"],
            "capabilities": stats["capabilities"],
            "cache_stats": stats["cache_stats"],
            "ready": True
        }
    except Exception as error:
        return {
            "status": "Server running but some issues detected",
            "error": str(error),
            "ready": False
        }

@router.post("/smart-question", response_model=QuestionResponse)
async def smart_question_analysis(request: QuestionRequest):
    """
    Main endpoint: Ask any question about a YouTube video
    Automatically detects if question needs visual analysis
    Uses smart caching for faster responses on repeat questions
    """
    try:
        # Check if URL and question are valid
        validate_youtube_url(request.url)
        
        if not request.question or not request.question.strip():
            raise HTTPException(status_code=400, detail="Please provide a question to ask")
        
        # Use the coordinator to analyze the question
        result = coordinator.analyze_video_question(
            youtube_url=request.url,
            question=request.question
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail=f"Analysis failed: {result['error']}"
            )
        
        # Return the response
        return QuestionResponse(
            success=True,
            question=request.question,
            answer=result["answer"],
            video_title=result.get("video_title", "Unknown Video"),
            method_used=result.get("method", "Smart Analysis"),
            message="Analysis complete!",
            timestamps=result.get("timestamps", []),
            has_timestamps=result.get("has_timestamps", False)
        )
        
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {error}"
        )

@router.post("/ask-question", response_model=QuestionResponse) 
async def ask_question_about_video(request: QuestionRequest):
    """
    Ask a question about a video (routes to smart analysis)
    Kept for compatibility with existing code
    """
    return await smart_question_analysis(request)

@router.post("/process-youtube", response_model=VideoResponse)
async def extract_transcript(request: VideoRequest):
    """
    Extract transcript from a YouTube video
    Returns just the transcript text without AI analysis
    """
    try:
        validate_youtube_url(request.url)
        
        # Check if we already have this transcript cached
        cache_status = is_cached(request.url)
        
        if cache_status["has_transcript"]:
            cached = get_cached_transcript(request.url)
            return VideoResponse(
                success=True,
                video_title=cached["video_title"],
                transcript=cached["transcript"],
                method_used=f"{cached['method_used']} (cached)",
                message="Retrieved from cache"
            )
        
        # Extract transcript using YouTube processor
        youtube_processor = YouTubeProcessor()
        result = youtube_processor.process_youtube_video(request.url)
        
        # Cache the result for future use
        if result["success"]:
            cache_transcript(
                url=request.url,
                video_title=result.get("video_title"),
                transcript=result.get("transcript"),
                method_used=result.get("method_used")
            )
        
        
        # Return the transcript
        return VideoResponse(
            success=result["success"],
            video_title=result.get("video_title"),
            transcript=result.get("transcript"),
            method_used=result.get("method_used"),
            message=result["message"],
            error=result.get("error")
        )
        
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Something went wrong: {error}")

@router.post("/summarize-video")
async def summarize_video(request: VideoRequest):
    """
    Get an AI summary of a YouTube video
    Creates a summary question and uses smart analysis
    """
    try:
        # Create a question request for getting a summary
        summary_request = QuestionRequest(
            url=request.url,
            question="Please provide a summary of this video"
        )
        
        # Use smart analysis to get the summary
        return await smart_question_analysis(summary_request)
        
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Summary failed: {error}")

@router.get("/cache-stats")
async def get_cache_statistics():
    """
    Get information about what's currently cached
    Shows how many videos, transcripts, and frames are stored
    """
    try:
        stats = coordinator.get_analysis_stats()
        
        return {
            "cache_info": "Current cache statistics",
            "coordinator_status": stats["coordinator_status"],
            "processors": stats["processors_loaded"],
            "cache_details": stats["cache_stats"],
            "capabilities": stats["capabilities"]
        }
    except Exception as error:
        return {
            "error": "Could not get cache stats",
            "details": str(error)
        }

@router.get("/clear-cache")
async def clear_transcript_cache():
    """
    Clear all cached data to free up memory
    Removes all stored transcripts and video frames
    """
    return clear_cache()