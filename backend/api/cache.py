# cache.py - Simple video data caching
from typing import Dict, Optional

# Store all video data in memory
video_cache = {}

def get_cached_transcript(url: str) -> Optional[Dict]:
    """
    Get previously saved transcript for a YouTube video
    Returns transcript data or None if not found
    """
    cached_data = video_cache.get(url)
    if cached_data and "transcript" in cached_data:
        return {
            "video_title": cached_data["video_title"],
            "transcript": cached_data["transcript"],
            "method_used": cached_data["transcript_method"]
        }
    return None

def cache_transcript(url: str, video_title: str, transcript: str, method_used: str) -> None:
    """
    Save transcript data to cache for faster future access
    Creates new cache entry if video not cached yet
    """
    if url not in video_cache:
        video_cache[url] = {}
    
    video_cache[url].update({
        "video_title": video_title,
        "transcript": transcript,
        "transcript_method": method_used
    })

def get_cached_frames(url: str) -> Optional[Dict]:
    """
    Get previously saved video frames for a YouTube video
    Returns frame data or None if not found
    """
    cached_data = video_cache.get(url)
    if cached_data and "frames" in cached_data:
        return {
            "frames": cached_data["frames"],
            "video_title": cached_data["video_title"],
            "frames_count": cached_data["frames_count"]
        }
    return None

def cache_frames(url: str, frame_info: Dict) -> None:
    """
    Save video frames to cache for faster visual analysis
    Creates new cache entry if video not cached yet
    """
    if url not in video_cache:
        video_cache[url] = {}
    
    video_cache[url].update({
        "frames": frame_info["frames"],
        "video_title": frame_info["video_title"],
        "frames_count": frame_info["frames_count"]
    })

def is_cached(url: str) -> Dict:
    """
    Check what data is already saved for a video
    Returns status of transcript and frames availability
    """
    cached_data = video_cache.get(url, {})
    return {
        "has_transcript": "transcript" in cached_data,
        "has_frames": "frames" in cached_data,
        "video_title": cached_data.get("video_title", "Unknown"),
        "frames_count": cached_data.get("frames_count", 0)
    }

def clear_cache() -> Dict:
    """
    Delete all cached data to free up memory
    Returns confirmation with count of removed videos
    """
    global video_cache
    removed_count = len(video_cache)
    video_cache.clear()
    return {"message": f"Cache cleared! Removed {removed_count} videos."}

def get_cache_stats() -> Dict:
    """
    Get current cache usage statistics
    Shows total videos and what data is cached
    """
    if not video_cache:
        return {
            "total_videos": 0, 
            "videos_with_transcripts": 0, 
            "videos_with_frames": 0
        }
    
    transcript_count = sum(1 for data in video_cache.values() if "transcript" in data)
    frames_count = sum(1 for data in video_cache.values() if "frames" in data)
    
    return {
        "total_videos": len(video_cache),
        "videos_with_transcripts": transcript_count,
        "videos_with_frames": frames_count
    }