# video_analysis_coordinator.py - Clean video analysis coordination
from .visual_processor import VisualProcessor
from .ai_processor import AIProcessor  
from .youtube_processor import YouTubeProcessor
from api.cache import (
    get_cached_transcript, cache_transcript, 
    get_cached_frames, cache_frames, 
    is_cached, get_cache_stats
)
from typing import Dict

class VideoAnalysisCoordinator:
    """
    Main coordinator that connects all video analysis components
    Handles transcripts, visual analysis, and smart caching
    """
    
    def __init__(self):
        """
        Initialize all processors and set up the analysis pipeline
        Creates transcript, visual, and AI processors
        """
        # Initialize all processors
        self.transcript_processor = YouTubeProcessor()
        self.visual_processor = VisualProcessor()
        self.ai_processor = AIProcessor()
    
    def analyze_video_question(self, youtube_url: str, question: str) -> Dict:
        """
        Main function: Analyze any question about a YouTube video
        Automatically handles text-only and visual questions
        Uses smart caching to avoid re-processing same videos
        """
        try:
            # Step 1: Check what's already cached
            cache_status = is_cached(youtube_url)
            
            # Step 2: Get transcript (from cache or fresh)
            transcript_data = self._get_transcript(youtube_url, cache_status)
            if not transcript_data:
                return {
                    "success": False,
                    "error": "Could not get video transcript",
                    "question": question
                }
            
            # Step 3: Check if question needs visual analysis
            detection = self.ai_processor.check_needs_visual_analysis(question)
            
            # Step 4: Route to appropriate analysis
            if detection["type"] == "transcript":
                # Text-only analysis
                return self._analyze_text_question(question, transcript_data)
            else:
                # Visual analysis needed
                return self._analyze_visual_question(question, transcript_data, youtube_url, cache_status)
                
        except Exception as error:
            return {
                "success": False,
                "error": str(error),
                "question": question
            }
    
    def _get_transcript(self, youtube_url: str, cache_status: Dict) -> Dict:
        """
        Get video transcript from cache or extract fresh
        Caches new transcripts for future use
        """
        if cache_status["has_transcript"]:
            return get_cached_transcript(youtube_url)
        else:
            result = self.transcript_processor.process_youtube_video(youtube_url)
            
            if result["success"]:
                # Cache the transcript
                cache_transcript(
                    url=youtube_url,
                    video_title=result["video_title"],
                    transcript=result["transcript"], 
                    method_used=result["method_used"]
                )
                
                return {
                    "video_title": result["video_title"],
                    "transcript": result["transcript"],
                    "method_used": result["method_used"]
                }
            else:
                return None
    
    def _get_frames(self, youtube_url: str, cache_status: Dict) -> Dict:
        """
        Get video frames from cache or extract fresh
        Caches new frames for future visual questions
        """
        if cache_status["has_frames"]:
            return get_cached_frames(youtube_url)
        else:
            result = self.visual_processor.extract_frames_from_youtube(youtube_url)
            
            if result["success"]:
                # Cache the frames
                cache_frames(youtube_url, result)
                
                return {
                    "frames": result["frames"],
                    "video_title": result["video_title"],
                    "frames_count": result["frames_count"],
                    "video_duration": result["video_duration"]
                }
            else:
                return None
    
    def _analyze_text_question(self, question: str, transcript_data: Dict) -> Dict:
        """
        Analyze questions that only need transcript text
        Uses AI to answer based on what people said in video
        """
        result = self.ai_processor.ask_question(
            question=question,
            transcript=transcript_data["transcript"],
            video_title=transcript_data["video_title"]
        )
        
        if result["success"]:
            result["analysis_type"] = "transcript_only"
            
        return result
    
    def _analyze_visual_question(self, question: str, transcript_data: Dict, 
                               youtube_url: str, cache_status: Dict) -> Dict:
        """
        Analyze questions that need to see the video
        Uses both video frames and transcript for complete analysis
        """
        # Get frames (from cache or fresh extraction)
        frames_data = self._get_frames(youtube_url, cache_status)
        
        if not frames_data:
            return {
                "success": False,
                "error": "Could not get video frames for visual analysis",
                "question": question
            }
        
        # Perform visual analysis using frames + transcript
        result = self.ai_processor.analyze_visual_question(
            question=question,
            transcript=transcript_data["transcript"],
            frames=frames_data["frames"],
            video_title=frames_data["video_title"]
        )
        
        if result["success"]:
            result["analysis_type"] = "visual"
            result["frames_count"] = frames_data["frames_count"]
            result["cache_used"] = cache_status["has_frames"]
            
        return result
    
    def get_analysis_stats(self) -> Dict:
        """
        Get current system status and cache statistics
        Shows what's cached and system capabilities
        """
        cache_stats = get_cache_stats()
        
        return {
            "coordinator_status": "ready",
            "processors_loaded": {
                "transcript": True,
                "visual": True, 
                "ai": True
            },
            "cache_stats": cache_stats,
            "capabilities": [
                "YouTube transcript extraction",
                "Video frame extraction", 
                "Smart question routing",
                "Visual + text analysis",
                "Intelligent caching"
            ]
        }