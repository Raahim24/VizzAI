# visual_processor.py - Simple video frame extraction
import os
import cv2
import yt_dlp
from pathlib import Path
import base64

class VisualProcessor:
    """
    Simple processor that extracts frames from YouTube videos
    Takes video frames so AI can see what's happening in the video
    """
    
    def __init__(self):
        """
        Set up the visual processor with folders and settings
        Creates temp folders and sets frame extraction rules
        """
        # Create folders for storing temporary files
        backend_dir = Path(__file__).parent.parent
        self.temp_folder = backend_dir / "temp_videos"
        self.temp_folder.mkdir(exist_ok=True)
        
        # Settings for frame extraction
        self.FRAME_INTERVAL = 5      # Extract 1 frame every 5 seconds
        self.MAX_FRAMES = 200        # Don't extract more than 200 frames
        self.JPEG_QUALITY = 70       # Good quality but not too large files
    
    def extract_frames_from_youtube(self, youtube_url: str) -> dict:
        """
        Main function: Extract frames from a YouTube video for AI analysis
        Downloads video, extracts key frames, converts to base64 for AI
        Returns dict with frames data or error if something goes wrong
        """
        video_file = None
        
        try:
            # Step 1: Get basic video info
            video_info = self._get_video_info(youtube_url)
            if not video_info["success"]:
                return video_info
            
            duration = video_info["duration"]
            title = video_info["title"]
            
            # Step 2: Calculate how many frames to extract
            extraction_plan = self._calculate_extraction_plan(duration)
            
            # Step 3: Download the video temporarily
            video_file = self._download_video_temp(youtube_url)
            if not video_file:
                return {
                    "success": False,
                    "error": "Could not download video",
                    "frames": []
                }
            
            # Step 4: Extract frames from the video
            frames_data = self._extract_frames_from_video(video_file, extraction_plan)
            if not frames_data["success"]:
                return frames_data
            
            # Step 5: Return the results
            return {
                "success": True,
                "frames": frames_data["frames"],
                "video_title": title,
                "video_duration": duration,
                "frames_count": len(frames_data["frames"]),
                "extraction_interval": extraction_plan["interval"],
                "message": f"Extracted {len(frames_data['frames'])} frames from video"
            }
            
        except Exception as error:
            return {
                "success": False,
                "error": str(error),
                "frames": []
            }
        
        finally:
            # Always clean up the temporary video file
            if video_file and os.path.exists(video_file):
                os.remove(video_file)
    
    def _get_video_info(self, youtube_url: str) -> dict:
        """
        Get basic info about the video without downloading it
        Returns video duration and title for planning frame extraction
        """
        try:
            with yt_dlp.YoutubeDL({'quiet': True}) as downloader:
                info = downloader.extract_info(youtube_url, download=False)
                
                duration = info.get('duration', 0)
                title = info.get('title', 'Unknown Video')
                
                if duration <= 0:
                    return {
                        "success": False,
                        "error": "Could not get video duration"
                    }
                
                return {
                    "success": True,
                    "duration": duration,
                    "title": title
                }
                
        except Exception as error:
            return {
                "success": False,
                "error": f"Could not access video: {error}"
            }
    
    def _calculate_extraction_plan(self, video_duration: float) -> dict:
        """
        Figure out how many frames to extract based on video length
        Shorter videos: 1 frame every 5 seconds
        Longer videos: spread frames evenly, max 200 total
        """
        # Calculate ideal number of frames (1 every 5 seconds)
        ideal_frames = int(video_duration / self.FRAME_INTERVAL)
        
        if ideal_frames <= self.MAX_FRAMES:
            # Video is short enough - use normal interval
            return {
                "interval": self.FRAME_INTERVAL,
                "total_frames": ideal_frames
            }
        else:
            # Video is too long - spread frames across whole video
            adjusted_interval = video_duration / self.MAX_FRAMES
            return {
                "interval": adjusted_interval,
                "total_frames": self.MAX_FRAMES
            }
    
    def _download_video_temp(self, youtube_url: str) -> str:
        """
        Download video to temporary folder for frame extraction
        Uses lower quality to save time and space
        Returns path to downloaded video file
        """
        try:
            temp_path = self.temp_folder / "temp_video"
            
            # Settings for downloading video
            settings = {
                'format': 'best[height<=720]',  # Lower quality = faster download
                'outtmpl': str(temp_path) + '.%(ext)s',
                'noplaylist': True,
                'quiet': True
            }
            
            # Download the video
            with yt_dlp.YoutubeDL(settings) as downloader:
                downloader.download([youtube_url])
            
            # Find the downloaded file
            video_extensions = ['.mp4', '.webm', '.mkv', '.avi']
            for ext in video_extensions:
                video_file = str(temp_path) + ext
                if os.path.exists(video_file):
                    return video_file
            
            return None
            
        except Exception:
            return None
    
    def _extract_frames_from_video(self, video_file: str, extraction_plan: dict) -> dict:
        """
        Extract frames from downloaded video file using OpenCV
        Takes frames at calculated intervals and converts to base64
        Returns list of frame data for AI analysis
        """
        try:
            # Open video file
            cap = cv2.VideoCapture(video_file)
            
            if not cap.isOpened():
                return {
                    "success": False,
                    "error": "Could not open video file",
                    "frames": []
                }
            
            # Get video properties
            video_fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames_in_video = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # Calculate which frames to extract
            frame_interval = int(video_fps * extraction_plan["interval"]) if video_fps > 0 else 1
            target_frames = extraction_plan["total_frames"]
            
            frames = []
            frame_count = 0
            extracted_count = 0
            
            # Loop through video and extract frames
            while extracted_count < target_frames:
                ret, frame = cap.read()
                
                if not ret:  # End of video
                    break
                
                # Check if this frame should be extracted
                if frame_count % frame_interval == 0:
                    # Convert frame to base64 for AI
                    frame_data = self._frame_to_base64(frame)
                    timestamp = frame_count / video_fps if video_fps > 0 else 0
                    
                    frames.append({
                        "frame_number": extracted_count,
                        "timestamp": round(timestamp, 2),
                        "data": frame_data
                    })
                    
                    extracted_count += 1
                
                frame_count += 1
            
            cap.release()
            
            return {
                "success": True,
                "frames": frames,
                "extracted_frames": len(frames)
            }
            
        except Exception as error:
            return {
                "success": False,
                "error": f"Frame extraction failed: {error}",
                "frames": []
            }
    
    def _frame_to_base64(self, frame) -> str:
        """
        Convert a video frame to base64 text format
        This format is needed for sending images to Gemini AI
        Returns base64 string that represents the image
        """
        try:
            # Convert frame to JPEG format
            encode_params = [cv2.IMWRITE_JPEG_QUALITY, self.JPEG_QUALITY]
            _, buffer = cv2.imencode('.jpg', frame, encode_params)
            
            # Convert to base64 text
            frame_base64 = base64.b64encode(buffer).decode('utf-8')
            return frame_base64
            
        except Exception:
            return ""
    
    def cleanup_temp_files(self):
        """
        Clean up temporary video files to free up disk space
        Removes all files in the temp folder
        """
        try:
            if self.temp_folder.exists():
                import shutil
                shutil.rmtree(self.temp_folder)
                self.temp_folder.mkdir(exist_ok=True)
        except Exception:
            pass  # Ignore cleanup errors