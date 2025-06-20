// App.js - Video Analysis Frontend
import React, { useState, useRef, useEffect } from 'react';
import './App.css';

const API_BASE_URL = 'http://localhost:8000';

function App() {
  // State management
  const [videoUrl, setVideoUrl] = useState('');
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [videoId, setVideoId] = useState('');
  const [videoTitle, setVideoTitle] = useState('');
  const [timestamps, setTimestamps] = useState([]);
  const [error, setError] = useState('');
  const [notifications, setNotifications] = useState([]);
  
  const chatRef = useRef(null);

  // Auto-scroll chat when new messages arrive
  useEffect(() => {
    if (chatRef.current) {
      chatRef.current.scrollTop = chatRef.current.scrollHeight;
    }
  }, [messages]);

  // Notification system
  const showNotification = (message, type = 'info', persistent = false) => {
    const id = Date.now();
    const newNotification = { id, message, type, persistent };
    setNotifications(prev => [...prev, newNotification]);
    
    if (!persistent) {
      setTimeout(() => {
        setNotifications(prev => prev.filter(n => n.id !== id));
      }, 4000);
    }
    
    return id;
  };

  const removeNotification = (id) => {
    setNotifications(prev => prev.filter(n => n.id !== id));
  };

  // Extract YouTube video ID from URL
  const getVideoId = (url) => {
    const patterns = [
      /youtube\.com\/watch\?v=([^&\n?#]+)/,
      /youtu\.be\/([^&\n?#]+)/,
      /youtube\.com\/embed\/([^&\n?#]+)/
    ];
    
    for (let pattern of patterns) {
      const match = url.match(pattern);
      if (match) return match[1];
    }
    return null;
  };

  // Parse time string to seconds
  const parseTimeToSeconds = (timeStr) => {
    const parts = timeStr.split(':').map(Number);
    if (parts.length === 3) {
      // HH:MM:SS format
      return parts[0] * 3600 + parts[1] * 60 + parts[2];
    } else if (parts.length === 2) {
      // MM:SS format
      return parts[0] * 60 + parts[1];
    }
    return 0;
  };

  // Format seconds to HH:MM:SS
  const formatTime = (seconds) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  // Generate timestamps from structured transcript data
  const createTimestampsFromTranscript = (structuredData) => {
    const timestampLoadingId = showNotification('Creating chapters from transcript...', 'loading', true);
    
    try {
      const chapters = [];
      const totalSegments = structuredData.length;
      const segmentsPerChapter = Math.max(50, Math.floor(totalSegments / 15));
      
      for (let i = 0; i < totalSegments; i += segmentsPerChapter) {
        const segment = structuredData[i];
        
        if (segment?.text && segment?.start_formatted) {
          // Create chapter title from content
          let title = segment.text.trim()
            .replace(/^(welcome to|hello|hi there|today we|in this)/i, '')
            .replace(/^(fact|number|tip)( \d+)?:?/i, '');
          
          const words = title.split(' ').filter(word => 
            word.length > 2 && 
            !['the', 'and', 'but', 'for', 'are', 'will', 'can', 'you', 'your'].includes(word.toLowerCase())
          );
          
          const chapterTitle = words.slice(0, 3).join(' ');
          
          if (chapterTitle.length > 3) {
            const totalSeconds = parseTimeToSeconds(segment.start_formatted);
            
            chapters.push({
              time: segment.start_formatted,
              title: chapterTitle.length > 30 ? chapterTitle.substring(0, 27) + '...' : chapterTitle,
              seconds: totalSeconds
            });
          }
        }
      }
      
      // Add conclusion chapter
      if (structuredData.length > 0) {
        const lastSegment = structuredData[structuredData.length - 1];
        if (lastSegment?.end_formatted) {
          const totalSeconds = parseTimeToSeconds(lastSegment.end_formatted);
          chapters.push({
            time: lastSegment.end_formatted,
            title: 'Conclusion',
            seconds: totalSeconds
          });
        }
      }
      
      setTimestamps(chapters);
      removeNotification(timestampLoadingId);
      showNotification('Chapters created successfully!', 'success');
      
    } catch (error) {
      removeNotification(timestampLoadingId);
      showNotification('Using AI to generate chapters...', 'info');
      generateAITimestamps(videoUrl);
    }
  };

  // Generate timestamps using AI
  const generateAITimestamps = async (url) => {
    const timestampLoadingId = showNotification('Generating timestamps...', 'loading', true);
    
    try {
      const response = await fetch(`${API_BASE_URL}/smart-question`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: url,
          question: "Create video chapters with short titles. Format: '0:00:00 - Introduction', '0:02:30 - Main Topic', etc. Keep titles under 5 words."
        })
      });

      const data = await response.json();

      if (data.success) {
        if (data.video_title && !videoTitle) {
          setVideoTitle(data.video_title);
        }
        
        const lines = data.answer.split('\n');
        const newTimestamps = [];
        
        lines.forEach(line => {
          const match = line.match(/(\d{1,2}):(\d{2}):(\d{2})\s*[-–]\s*(.+)/);
          if (match) {
            const hours = parseInt(match[1]);
            const minutes = parseInt(match[2]);
            const seconds = parseInt(match[3]);
            const title = match[4].trim().replace(/\*\*/g, '');
            
            const displayTime = `${hours}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
            
            newTimestamps.push({
              time: displayTime,
              title: title.length > 40 ? title.substring(0, 37) + '...' : title,
              seconds: hours * 3600 + minutes * 60 + seconds
            });
          }
        });
        
        setTimestamps(newTimestamps);
        removeNotification(timestampLoadingId);
        showNotification('Timestamps generated!', 'success');
      } else {
        removeNotification(timestampLoadingId);
        showNotification('Could not generate timestamps', 'error');
      }
    } catch (error) {
      removeNotification(timestampLoadingId);
      showNotification('Failed to generate timestamps', 'error');
    }
  };

  // Load video and extract transcript
  const loadVideo = async () => {
    const id = getVideoId(videoUrl);
    if (!id) {
      setError('Please enter a valid YouTube URL');
      return;
    }

    // Reset state
    setVideoId(id);
    setMessages([]);
    setTimestamps([]);
    setError('');
    
    const videoLoadingId = showNotification('Loading video and extracting transcript', 'loading', true);
    
    try {
      const response = await fetch(`${API_BASE_URL}/process-youtube`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: videoUrl })
      });

      const data = await response.json();

      if (!data.success) {
        removeNotification(videoLoadingId);
        showNotification('Failed to process video: ' + data.error, 'error');
        setError('Could not extract transcript from this video');
        return;
      }

      removeNotification(videoLoadingId);
      showNotification('Video transcript extracted successfully!', 'success');
      
      setVideoTitle(data.video_title || 'Unknown Video');
      
      setMessages([{
        type: 'system',
        content: `Video loaded! Ask questions about "${data.video_title || 'this video'}".`,
        time: new Date().toLocaleTimeString()
      }]);

      // Just use AI-generated timestamps since it was working better
      await generateAITimestamps(videoUrl);
      
    } catch (error) {
      removeNotification(videoLoadingId);
      showNotification('Connection error: ' + error.message, 'error');
      setError('Failed to connect to server');
    }
  };

  // Ask question about video
  const askQuestion = async () => {
    if (!question.trim()) {
      setError('Please enter a question');
      return;
    }
    if (!videoUrl.trim()) {
      setError('Please load a video first');
      return;
    }

    setLoading(true);
    setError('');

    const userMessage = {
      type: 'user',
      content: question
    };
    setMessages(prev => [...prev, userMessage]);

    try {
      const response = await fetch(`${API_BASE_URL}/smart-question`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: videoUrl,
          question: question + " Please include specific timestamps in your response using format (0:02:30) without extra words like 'around' or 'at'."
        })
      });

      const data = await response.json();

      if (data.success) {
        const aiMessage = {
          type: 'ai',
          content: data.answer,
          method: data.method_used
        };
        setMessages(prev => [...prev, aiMessage]);
      } else {
        setError(`Failed: ${data.error}`);
      }
    } catch (error) {
      setError(`Connection error: ${error.message}`);
    } finally {
      setLoading(false);
      setQuestion('');
    }
  };

  // Handle Enter key press
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !loading) {
      askQuestion();
    }
  };

  // Jump to specific time in video
  const jumpToTime = (seconds) => {
    const iframe = document.getElementById('youtube-player');
    if (iframe) {
      const baseUrl = iframe.src.split('?')[0];
      iframe.src = `${baseUrl}?start=${seconds}&autoplay=1`;
    }
  };

  // Format text with clickable timestamps
  const formatText = (text) => {
    if (typeof text !== 'string') return text;
    
    let formattedText = text
      .replace(/\*\*([^*]+)\*\*/g, '<strong class="bold-text">$1</strong>')
      .replace(/\*([^*]+)\*/g, '<em class="italic-text">$1</em>')
      .replace(/\((\d{1,2}):(\d{2}):(\d{2})\)/g, '<span class="timestamp-placeholder">$1:$2:$3</span>');
    
    const parts = formattedText.split(/<span class="timestamp-placeholder">(\d{1,2}:\d{2}:\d{2})<\/span>/);
    const result = [];
    
    for (let i = 0; i < parts.length; i++) {
      if (i % 2 === 0) {
        if (parts[i]) {
          result.push(
            <span 
              key={i} 
              dangerouslySetInnerHTML={{ __html: parts[i] }}
            />
          );
        }
      } else {
        const totalSeconds = parseTimeToSeconds(parts[i]);
        
        result.push(
          <button
            key={i}
            className="timestamp-link"
            onClick={() => jumpToTime(totalSeconds)}
          >
            {parts[i]}
          </button>
        );
      }
    }
    
    return result.length > 0 ? result : text;
  };

  return (
    <div className="App">
      {/* Notifications */}
      <div className="notifications">
        {notifications.map(notification => (
          <div key={notification.id} className={`notification ${notification.type}`}>
            {notification.message}
          </div>
        ))}
      </div>

      {/* Header */}
      <header className="header">
        <h1>VizzAI</h1>
        <p>Ask questions about any YouTube video!</p>
      </header>

      {/* Main Content */}
      <div className="main-content">
        
        {/* Video Section */}
        <div className="video-section">
          <div className="url-input">
            <h3>Load YouTube Video</h3>
            <div className="input-group">
              <input
                type="text"
                placeholder="Paste YouTube URL here..."
                value={videoUrl}
                onChange={(e) => setVideoUrl(e.target.value)}
                className="url-field"
              />
              <button onClick={loadVideo} className="load-btn">
                Load Video
              </button>
            </div>
          </div>

          {/* YouTube Player */}
          {videoId && (
            <div className="video-player">
              <iframe
                id="youtube-player"
                src={`https://www.youtube.com/embed/${videoId}`}
                title="YouTube video player"
                frameBorder="0"
                allowFullScreen
              ></iframe>
            </div>
          )}

          {/* Video Chapters */}
          {timestamps.length > 0 && (
            <div className="timestamps-section">
              <h4>Video Chapters</h4>
              <p>Click any timestamp to jump to that moment</p>
              <div className="timestamps-list">
                {timestamps.map((item, index) => (
                  <div
                    key={index}
                    className="timestamp-item"
                    onClick={() => jumpToTime(item.seconds)}
                  >
                    <span className="time">{item.time}</span>
                    <span className="title">{item.title}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Chat Section */}
        <div className="chat-section">
          <div className="chat-header">
            <h3>Ask Questions</h3>
            {videoTitle && <div className="video-title">{videoTitle}</div>}
          </div>
          
          <div className="chat-messages" ref={chatRef}>
            {messages.length === 0 && (
              <div className="welcome">
                <h4>Welcome!</h4>
                <p>Load a video above and start asking questions</p>
                <div className="examples">
                  <div className="example">"What is this video about?"</div>
                  <div className="example">"What color is the car?"</div>
                  <div className="example">"Summarize the main points"</div>
                </div>
              </div>
            )}

            {messages.map((message, index) => (
              <div key={index} className={`message ${message.type}`}>
                
                {message.type === 'system' && (
                  <div className="system-msg">
                    <span>{message.content}</span>
                  </div>
                )}

                {message.type === 'user' && (
                  <div className="user-msg">
                    <div className="avatar">You</div>
                    <div className="content">
                      <div className="text">{message.content}</div>
                    </div>
                  </div>
                )}

                {message.type === 'ai' && (
                  <div className="ai-msg">
                    <div className="avatar">AI</div>
                    <div className="content">
                      <div className="badge">
                        {message.method === 'Visual Analysis' ? 'Visual' : 'Text'}
                      </div>
                      <div className="text">
                        {formatText(message.content)}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ))}

            {loading && (
              <div className="message ai">
                <div className="ai-msg">
                  <div className="avatar">AI</div>
                  <div className="content">
                    <div className="loading">Analyzing video</div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {error && (
            <div className="error">
              {error}
              <button onClick={() => setError('')}>×</button>
            </div>
          )}

          <div className="question-input">
            <div className="input-group">
              <input
                type="text"
                placeholder="Ask any question about the video..."
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyPress={handleKeyPress}
                disabled={loading}
                className="question-field"
              />
              <button 
                onClick={askQuestion}
                disabled={loading || !question.trim() || !videoId}
                className="ask-btn"
              >
                {loading ? 'Loading...' : 'Ask'}
              </button>
            </div>
            
            {videoId && (
              <div className="hint">
                Ask about content, visuals, or request summaries!
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="footer">
        <p>Made by Raahim Khan</p>
      </footer>
    </div>
  );
}

export default App;