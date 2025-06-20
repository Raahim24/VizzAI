# youtube_processor.py - YouTube transcript extraction with 3 fallback methods
import os
import yt_dlp
import whisper
from youtube_transcript_api import YouTubeTranscriptApi
from pathlib import Path
import re

class YouTubeProcessor:
    """
    Extract transcripts from YouTube videos using 3 methods:
    1. YouTube API (fastest) 2. yt-dlp captions 3. Whisper AI (most reliable)
    All methods now return structured data with timestamps when available
    """
    
    def __init__(self):
        # Load Whisper model for audio transcription
        self.whisper_model = whisper.load_model("base")
        
        # Create downloads folder for temporary files
        backend_dir = Path(__file__).parent.parent  
        self.downloads_folder = backend_dir / "downloads"
        self.downloads_folder.mkdir(exist_ok=True)
    
    def get_video_id(self, youtube_url):
        """Extract video ID from any YouTube URL format"""
        patterns = [
            r'youtube\.com/watch\?v=([^&\n?#]+)',
            r'youtu\.be/([^&\n?#]+)',
            r'youtube\.com/embed/([^&\n?#]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, youtube_url)
            if match:
                return match.group(1)
        
        raise ValueError("Could not find video ID in URL")
    
    def get_transcript_from_youtube_api(self, youtube_url):
        """
        Method 1: Get transcript from YouTube's official API
        Returns structured data with timestamps or None if not available
        """
        try:
            video_id = self.get_video_id(youtube_url)
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            
            # Find the best English transcript available
            best_transcript = self._find_best_english_transcript(transcript_list)
            
            if best_transcript:
                captions = best_transcript.fetch()
                return self._format_youtube_transcript_data(captions)
            
            return None
                
        except Exception:
            return None

    def _find_best_english_transcript(self, transcript_list):
        """Find the best available English transcript (manual preferred over auto-generated)"""
        best_transcript = None
        
        for transcript in transcript_list:
            lang_code = transcript.language_code.lower()
            lang_name = transcript.language.lower()
            
            # Prioritize manual English transcripts
            if not transcript.is_generated and lang_code.startswith('en'):
                return transcript  # Return immediately for manual transcripts
            
            # Accept auto-generated English if no manual found
            elif transcript.is_generated and lang_code.startswith('en') and not best_transcript:
                best_transcript = transcript
            
            # Also check by language name
            elif 'english' in lang_name and not best_transcript:
                best_transcript = transcript
        
        return best_transcript

    def _format_youtube_transcript_data(self, captions):
        """Convert YouTube API captions to our structured format"""
        structured_transcript = []
        plain_text_parts = []
        
        for caption in captions:
            start_time = caption['start']
            duration = caption['duration']
            end_time = start_time + duration
            text = caption['text'].strip()
            
            if text:
                structured_transcript.append({
                    'text': text,
                    'start': round(start_time, 2),
                    'end': round(end_time, 2),
                    'start_formatted': self._seconds_to_timestamp(start_time),
                    'end_formatted': self._seconds_to_timestamp(end_time)
                })
                plain_text_parts.append(text)
        
        return {
            'transcript_text': ' '.join(plain_text_parts),
            'structured_data': structured_transcript,
            'has_timestamps': True,
            'total_segments': len(structured_transcript)
        }

    def _seconds_to_timestamp(self, seconds):
        """Convert seconds to HH:MM:SS format"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    
    def get_transcript_from_captions(self, youtube_url):
        """
        Method 2: Extract captions using yt-dlp
        Returns structured data with timestamps or plain text fallback
        """
        try:
            settings = {
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': ['en'],
                'skip_download': True,
                'outtmpl': str(self.downloads_folder / '%(title)s'),
                'quiet': True
            }
            
            with yt_dlp.YoutubeDL(settings) as downloader:
                downloader.download([youtube_url])
            
            # Process downloaded VTT files
            return self._process_vtt_files()
            
        except Exception:
            return None
    
    def _process_vtt_files(self):
        """Process all VTT files in downloads folder"""
        for file in self.downloads_folder.glob("*.vtt"):
            with open(file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Try structured parsing first
            structured_data = self._parse_vtt_file(content)
            
            if structured_data:
                os.remove(file)
                return {
                    'transcript_text': ' '.join([seg['text'] for seg in structured_data]),
                    'structured_data': structured_data,
                    'has_timestamps': True,
                    'total_segments': len(structured_data)
                }
            else:
                # Fallback to plain text
                plain_text = self._extract_plain_text_from_vtt(content)
                os.remove(file)
                
                if plain_text.strip():
                    return plain_text.strip()
        
        return None
    
    def _parse_vtt_file(self, content):
        """Parse VTT file to extract timestamps and text"""
        try:
            lines = content.split('\n')
            structured_segments = []
            
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                
                # Look for VTT timestamp lines
                if '-->' in line:
                    timestamp_match = re.match(r'(\d{2}:\d{2}:\d{2}\.\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}\.\d{3})', line)
                    
                    if timestamp_match:
                        start_seconds = self._vtt_time_to_seconds(timestamp_match.group(1))
                        end_seconds = self._vtt_time_to_seconds(timestamp_match.group(2))
                        
                        # Get text from following lines
                        i += 1
                        text_lines = []
                        
                        while i < len(lines):
                            text_line = lines[i].strip()
                            
                            if not text_line or '-->' in text_line:
                                break
                            
                            clean_text = self._clean_vtt_text(text_line)
                            if clean_text:
                                text_lines.append(clean_text)
                            
                            i += 1
                        
                        if text_lines:
                            combined_text = ' '.join(text_lines)
                            structured_segments.append({
                                'text': combined_text,
                                'start': start_seconds,
                                'end': end_seconds,
                                'start_formatted': self._seconds_to_timestamp(start_seconds),
                                'end_formatted': self._seconds_to_timestamp(end_seconds)
                            })
                        
                        continue
                
                i += 1
            
            return structured_segments if structured_segments else None
            
        except Exception:
            return None
    
    def _clean_vtt_text(self, text):
        """Remove VTT formatting and embedded timestamps"""
        # Remove embedded timestamps
        text = re.sub(r'<\d{2}:\d{2}:\d{2}\.\d{3}>', '', text)
        # Remove VTT tags
        text = re.sub(r'<[^>]+>', '', text)
        # Clean up spaces
        text = ' '.join(text.split())
        return text.strip()
    
    def _vtt_time_to_seconds(self, time_str):
        """Convert VTT time format to seconds"""
        try:
            parts = time_str.split(':')
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds_part = parts[2].split('.')
            seconds = int(seconds_part[0])
            milliseconds = int(seconds_part[1]) if len(seconds_part) > 1 else 0
            
            total_seconds = hours * 3600 + minutes * 60 + seconds + milliseconds / 1000.0
            return round(total_seconds, 2)
        except:
            return 0.0
    
    def _extract_plain_text_from_vtt(self, content):
        """Extract plain text from VTT if structured parsing fails"""
        lines = content.split('\n')
        clean_lines = []
        
        for line in lines:
            if (not line.startswith('WEBVTT') and 
                not '-->' in line and 
                not line.strip().isdigit() and 
                line.strip()):
                
                clean_text = self._clean_vtt_text(line.strip())
                if clean_text:
                    clean_lines.append(clean_text)
        
        return " ".join(clean_lines)
    
    def get_transcript_from_audio(self, youtube_url):
        """
        Method 3: Use Whisper AI to transcribe audio with timestamps
        Now returns structured data with timestamps like other methods
        """
        audio_file = None
        
        try:
            # Download audio
            audio_file = self._download_audio(youtube_url)
            if not audio_file:
                return None
            
            # Transcribe with Whisper and get segments with timestamps
            result = self.whisper_model.transcribe(str(audio_file))
            
            # Clean up audio file
            os.remove(audio_file)
            
            # Format Whisper result to match our structure
            return self._format_whisper_transcript_data(result)
            
        except Exception:
            if audio_file and os.path.exists(audio_file):
                os.remove(audio_file)
            return None

    def _download_audio(self, youtube_url):
        """Download audio file for Whisper transcription"""
        try:
            settings = {
                'format': 'bestaudio',
                'outtmpl': str(self.downloads_folder / '%(title)s.%(ext)s'),
                'noplaylist': True,
                'quiet': True
            }
            
            with yt_dlp.YoutubeDL(settings) as downloader:
                downloader.download([youtube_url])
            
            # Find downloaded audio file
            audio_extensions = ['.m4a', '.mp3', '.webm', '.opus', '.mp4']
            for file in self.downloads_folder.glob("*"):
                if file.is_file() and any(file.suffix.lower() == ext for ext in audio_extensions):
                    return file
            
            return None
        except Exception:
            return None

    def _format_whisper_transcript_data(self, whisper_result):
        """Convert Whisper result to our structured format with timestamps"""
        if 'segments' not in whisper_result:
            # Fallback to plain text if no segments
            return whisper_result.get('text', '').strip()
        
        structured_transcript = []
        plain_text_parts = []
        
        for segment in whisper_result['segments']:
            text = segment['text'].strip()
            start_time = segment['start']
            end_time = segment['end']
            
            if text:
                structured_transcript.append({
                    'text': text,
                    'start': round(start_time, 2),
                    'end': round(end_time, 2),
                    'start_formatted': self._seconds_to_timestamp(start_time),
                    'end_formatted': self._seconds_to_timestamp(end_time)
                })
                plain_text_parts.append(text)
        
        return {
            'transcript_text': ' '.join(plain_text_parts),
            'structured_data': structured_transcript,
            'has_timestamps': True,
            'total_segments': len(structured_transcript)
        }
    
    def process_youtube_video(self, youtube_url):
        """
        Main function: Try all 3 methods until one works
        Returns structured data with timestamps when available
        """
        try:
            # Get video title
            video_title = self._get_video_title(youtube_url)
            
            # Try Method 1: YouTube API
            result = self.get_transcript_from_youtube_api(youtube_url)
            if result:
                return {
                    "success": True,
                    "video_title": video_title,
                    "transcript": result,
                    "method_used": "YouTube API",
                    "message": f"Got transcript with {result['total_segments']} timestamped segments"
                }
            
            # Try Method 2: yt-dlp captions
            result = self.get_transcript_from_captions(youtube_url)
            if result:
                if isinstance(result, dict):
                    return {
                        "success": True,
                        "video_title": video_title,
                        "transcript": result,
                        "method_used": "yt-dlp captions",
                        "message": f"Got transcript with {result['total_segments']} timestamped segments"
                    }
                else:
                    return {
                        "success": True,
                        "video_title": video_title,
                        "transcript": result,
                        "method_used": "yt-dlp captions",
                        "message": "Got transcript from yt-dlp (plain text)"
                    }
            
            # Try Method 3: Whisper AI
            result = self.get_transcript_from_audio(youtube_url)
            if result:
                if isinstance(result, dict):
                    return {
                        "success": True,
                        "video_title": video_title,
                        "transcript": result,
                        "method_used": "Whisper AI",
                        "message": f"Got transcript with {result['total_segments']} timestamped segments"
                    }
                else:
                    return {
                        "success": True,
                        "video_title": video_title,
                        "transcript": result,
                        "method_used": "Whisper AI",
                        "message": "Got transcript from Whisper AI"
                    }
            
            # All methods failed
            return {
                "success": False,
                "video_title": video_title,
                "error": "All 3 methods failed to get transcript",
                "message": "Could not extract transcript from this video"
            }
            
        except Exception as error:
            return {
                "success": False,
                "error": str(error),
                "message": "Something went wrong"
            }

    def _get_video_title(self, youtube_url):
        """Get video title safely"""
        try:
            with yt_dlp.YoutubeDL({'quiet': True}) as downloader:
                info = downloader.extract_info(youtube_url, download=False)
                return info.get('title', 'Unknown Video')
        except:
            return "Unknown Video"