"""
MultiModal Video Analysis Backend.

A smart video analysis system that can:
- Extract transcripts from YouTube videos
- Answer questions about video content using AI
- Provide summaries and insights
"""

# Make processors easily available
from . import processors
from . import utils
from . import api

__version__ = "2.0.0"
__all__ = ["processors", "utils", "api"]