# main.py - FastAPI server setup
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from .endpoints import router

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handle server startup and shutdown events
    Shows helpful messages when server starts and stops
    """
    # Server startup
    print("Video Analysis server starting...")
    print("API docs available at: http://localhost:8000/docs")
    
    yield
    
    # Server shutdown
    print("Server shutting down...")

# Create the main FastAPI application
app = FastAPI(
    title="Video Analysis API", 
    description="Analyze YouTube videos with AI - extract transcripts and ask questions",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Allow frontend to connect to our API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",    # React development server
        "http://127.0.0.1:3000",   # Alternative localhost format
        "http://localhost:3001",   # Alternative React port
    ],
    allow_credentials=True,
    allow_methods=["*"],           # Allow all HTTP methods
    allow_headers=["*"],           # Allow all headers
)

# Connect all our API routes
app.include_router(router)

@app.get("/ping")
async def ping():
    """
    Simple ping endpoint to check if server is running
    Returns basic status message
    """
    return {
        "status": "pong", 
        "message": "Server is running!"
    }

# Run the server when this file is executed directly
if __name__ == "__main__":
    import uvicorn
    
    print("Starting Video Analysis server...")
    
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )