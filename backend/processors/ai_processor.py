# ai_processor.py - Clean Gemini AI integration
import os
import google.generativeai as genai
from dotenv import load_dotenv
from typing import Dict, Optional
import re
from pathlib import Path

class AIProcessor:
    """
    AI processor for video question answering using Gemini
    Handles both text-only and visual analysis automatically
    """
    
    def __init__(self):
        """
        Initialize AI processor with Gemini API
        Loads API key from .env file and sets up the model
        """
        # Load API key from .env file
        backend_dir = Path(__file__).parent.parent
        env_path = backend_dir / ".env"
        load_dotenv(env_path)
        
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in .env file!")
        
        # Configure and initialize Gemini
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("models/gemini-2.0-flash")
    
    def ask_question(self, question: str, transcript: str, video_title: str = "Unknown Video") -> Dict:
        """
        Ask a text-based question about video transcript
        Uses transcript content only - no visual analysis
        Returns AI answer based on what people said in the video
        """
        try:
            # 🎯 MUCH BETTER PROMPT: Professional video analyst persona
            prompt = f"""You are a professional video analyst who has just finished watching and analyzing "{video_title}". You have extensive experience in content analysis, media studies, and extracting key insights from video content.

    QUESTION TO ANSWER: {question}

    VIDEO TRANSCRIPT (Complete Content):
    {transcript}

    ANALYSIS INSTRUCTIONS:
    • Answer as a knowledgeable expert who fully understands this video's content, themes, and context
    • Provide specific, detailed answers based on what was actually discussed
    • Be conversational but authoritative - like explaining to a colleague who hasn't seen the video
    • If the question asks about something not covered in the video, clearly state that
    • Focus on providing actionable insights and clear explanations
    • Reference specific moments naturally without forcing timestamp formats
    IMPORTANT : GIVE IN HH:MM:SS format timestamps 
    Your expert analysis:"""

            response = self.model.generate_content(prompt)
            
            if not response or not response.text:
                return {
                    "success": False,
                    "error": "AI didn't provide a response",
                    "answer": None
                }
            
            answer = response.text.strip()
            
            # Extract timestamps from the response
            timestamps = self._extract_timestamps(answer)
            
            return {
                "success": True,
                "answer": answer,
                "video_title": video_title,
                "question": question,
                "method": "Text Analysis",
                "timestamps": timestamps,
                "has_timestamps": len(timestamps) > 0
            }
            
        except Exception as error:
            return {
                "success": False,
                "error": str(error),
                "answer": None
            }
    
    def check_needs_visual_analysis(self, question: str) -> Dict:
        """
        Analyze if a question needs visual analysis or just text
        Returns whether question needs to 'see' the video or just hear transcript
        """
        try:
            prompt = f"""I need to determine if this question requires looking at video images or can be answered from the transcript alone.

Question: "{question}"

TRANSCRIPT questions (audio/speech content only):
- What people said, discussed, topics
- Example: "What did he say about exercise?"

VISUAL questions (need to see video frames):
- Colors, objects, people's appearance, actions
- Counting things, describing what's visible
- Example: "What color is the car?" or "How many people?"

If the question asks about COLORS, APPEARANCE, COUNTING, or OBJECTS - it needs VISUAL analysis.

Answer format:
TYPE: [transcript/visual]
CONFIDENCE: [0.1-1.0] 
REASONING: [brief explanation]"""

            response = self.model.generate_content(prompt)
            result_text = response.text.strip()
            
            # Parse the response
            type_match = re.search(r'TYPE:\s*(transcript|visual)', result_text, re.IGNORECASE)
            detected_type = type_match.group(1).lower() if type_match else "transcript"
            
            conf_match = re.search(r'CONFIDENCE:\s*([\d.]+)', result_text)
            confidence = float(conf_match.group(1)) if conf_match else 0.7
            
            reason_match = re.search(r'REASONING:\s*(.+)', result_text, re.IGNORECASE)
            reasoning = reason_match.group(1).strip() if reason_match else "Analysis completed"
            
            return {
                "success": True,
                "type": detected_type,
                "confidence": confidence,
                "reasoning": reasoning,
                "needs_visual": detected_type == "visual",
                "question": question
            }
            
        except Exception as error:
            # Fallback to transcript analysis if detection fails
            return {
                "success": True,
                "type": "transcript",
                "confidence": 0.5,
                "reasoning": "Detection failed, using transcript analysis",
                "needs_visual": False,
                "question": question
            }
    
    def analyze_visual_question(self, question: str, transcript: str, frames: list, video_title: str = "Unknown Video") -> Dict:
        """
        Analyze visual questions using both video frames and transcript
        Combines what can be seen in frames with transcript context
        Returns AI answer based on visual + audio content
        """
        try:
            # 🎯 MUCH BETTER PROMPT: Professional visual analyst persona
            prompt = f"""You are a professional video analyst specializing in multimodal content analysis. You have just completed a comprehensive review of "{video_title}" using both audio transcription and visual frame analysis.

    ANALYSIS REQUEST: {question}

    AUDIO TRANSCRIPT (What was said):
    {transcript}

    VISUAL FRAMES: You are now viewing key frames extracted from this video that show the visual elements, actions, objects, people, text, colors, settings, and movements throughout the content.

    EXPERT ANALYSIS GUIDELINES:
    • Combine both audio and visual information to provide a complete
    • Describe what you observe in the frames that relates to the question
    • Explain how the visual elements connect to or enhance what was discussed in the audio
    • Be specific about visual details: colors, objects, people, text, actions, settings, expressions
    • Reference both what you see AND what you hear to give the most accurate answer
    • If asked about something visual that's not clearly shown in the frames, acknowledge this limitation
    • Provide insights that only come from seeing the actual video content
    • Be conversational yet authoritative - like a colleague who has expertly analyzed this content

    VISUAL EXPERTISE: Focus on details that can only be determined by actually watching the video - things like facial expressions, body language, visual demonstrations, on-screen text, colors, objects, environments, and visual storytelling elements.
    IMPORTANT : GIVE IN HH:MM:SS format timestamps
    Your comprehensive multimodal analysis:"""

            # Prepare content (text + images)
            content = [prompt]
            
            # Add frames (limit to 15 for efficiency)
            frames_to_use = frames[:15] if len(frames) > 15 else frames
            
            for frame in frames_to_use:
                content.append({
                    "mime_type": "image/jpeg",
                    "data": frame["data"]  # base64 encoded image
                })
            
            # Send to Gemini Vision
            response = self.model.generate_content(content)
            
            if not response or not response.text:
                return {
                    "success": False,
                    "error": "Visual analysis failed",
                    "answer": None
                }
            
            answer = response.text.strip()
            
            # Extract timestamps from the response
            timestamps = self._extract_timestamps(answer)
            
            return {
                "success": True,
                "answer": answer,
                "video_title": video_title,
                "question": question,
                "method": "Visual Analysis",
                "frames_analyzed": len(frames_to_use),
                "timestamps": timestamps,
                "has_timestamps": len(timestamps) > 0
            }
            
        except Exception as error:
            return {
                "success": False,
                "error": str(error),
                "answer": None
            }
        
    def smart_question_analysis(self, question: str, transcript: str = None, 
                               video_title: str = None, frames: list = None) -> Dict:
        """
        Main function: Intelligently route questions to text or visual analysis
        Automatically detects what type of analysis is needed
        Returns appropriate AI response based on question type
        """
        try:
            # Step 1: Detect question type
            detection = self.check_needs_visual_analysis(question)
            
            if not detection["success"]:
                return detection
            
            # Step 2: Route to appropriate analysis
            if detection["type"] == "transcript":
                # Text-only analysis
                return self.ask_question(question, transcript, video_title)
            
            else:
                # Visual analysis needed
                if frames:
                    return self.analyze_visual_question(question, transcript, frames, video_title)
                else:
                    return {
                        "success": False,
                        "error": "Visual analysis required but no frames provided",
                        "message": "This question needs video frames",
                        "needs_frames": True,
                        "question": question
                    }
            
        except Exception as error:
            return {
                "success": False,
                "error": str(error),
                "message": "Analysis failed"
            }
    
    def analyze_complete_video(self, transcript: str, video_title: str = "Unknown Video") -> Dict:
        """
        Create a complete video analysis with chapters, main points, and summary
        Returns structured breakdown of entire video content
        Perfect for video overview and navigation
        """
        try:
            # 🎯 MUCH BETTER PROMPT: Professional content strategist persona
            prompt = f"""You are a professional content strategist and video analyst who specializes in creating comprehensive video breakdowns for audiences who want to understand content structure and key insights.

    VIDEO TITLE: "{video_title}"

    COMPLETE TRANSCRIPT:
    {transcript}

    ANALYSIS TASK: Create a professional video breakdown that helps viewers understand the content structure and navigate to key sections.

    EXPERT ANALYSIS REQUIREMENTS:

    CONTENT STRUCTURE:
    • Identify the main themes and topics discussed throughout the video
    • Recognize natural transitions and topic changes
    • Note key insights, important quotes, or standout moments
    • Identify the overall narrative flow and content progression

     KEY INSIGHTS:
    • Extract the most valuable takeaways and main points
    • Highlight actionable information or important concepts
    • Note any conclusions, recommendations, or calls-to-action
    • Identify unique or particularly interesting content

    CONTENT SUMMARY:
    • Provide a comprehensive overview that captures the essence of the video
    • Explain what viewers will learn or gain from watching
    • Describe the overall tone, style, and approach of the content
    • Mention target audience and content value proposition

    TOPICAL BREAKDOWN:
    • Create a logical flow of the main topics covered
    • Group related concepts and discussions together
    • Show how different sections build upon each other
    • Identify any recurring themes or concepts

    DELIVERABLE FORMAT:
    Present your analysis in a clear, structured format that helps viewers understand what this video offers and how the content is organized. Focus on being informative and useful for someone deciding whether to watch or looking for specific information.
    
    Your professional content analysis:"""

            response = self.model.generate_content(prompt)
            
            if not response or not response.text:
                return {
                    "success": False,
                    "error": "Could not generate video analysis",
                    "analysis": None
                }
            
            # Clean up the response (remove markdown formatting)
            analysis = response.text.strip()
            analysis = analysis.replace("**", "")  # Remove markdown bold
            analysis = analysis.replace("*", "")   # Remove markdown italic
            
            # Extract timestamps for navigation (if any naturally occur)
            timestamps = self._extract_timestamps(analysis)
            
            return {
                "success": True,
                "analysis": analysis,
                "video_title": video_title,
                "timestamps": timestamps,
                "has_timestamps": len(timestamps) > 0,
                "method": "Complete Video Analysis"
            }
        
        except Exception as error:
            return {
                "success": False,
                "error": str(error),
                "analysis": None
            }
    
    def _extract_timestamps(self, text: str) -> list:
        """Extract timestamps in HH:MM:SS format from AI responses"""
        timestamps = []
        
        # Pattern for HH:MM:SS format in parentheses (0:05:30) or (1:23:45)
        pattern = r'\((\d{1,2}):([0-5]\d):([0-5]\d)\)'
        for match in re.finditer(pattern, text):
            hours = int(match.group(1))
            minutes = int(match.group(2))
            seconds = int(match.group(3))
            
            if hours < 24:
                total_seconds = hours * 3600 + minutes * 60 + seconds
                timestamps.append({
                    "display": f"{hours}:{minutes:02d}:{seconds:02d}",
                    "seconds": total_seconds,
                    "timestamp_text": match.group(0)
                })
        
        # Remove duplicates and sort
        seen = set()
        unique_timestamps = []
        for ts in timestamps:
            if ts["seconds"] not in seen:
                seen.add(ts["seconds"])
                unique_timestamps.append(ts)
        
        return sorted(unique_timestamps, key=lambda x: x["seconds"])