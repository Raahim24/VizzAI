"""
Video processing modules for MultiModal Video Analysis.
"""

# Import all processors so they can be imported easily
from .youtube_processor import YouTubeProcessor
from .ai_processor import AIProcessor
from .visual_processor import VisualProcessor
from .video_analysis_coordinator import VideoAnalysisCoordinator

# Make them available when someone imports processors
__all__ = ["YouTubeProcessor", "AIProcessor", "VisualProcessor", "VideoAnalysisCoordinator"]