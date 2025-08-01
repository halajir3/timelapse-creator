import os
import shutil
import subprocess
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import psutil
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="Timelapse Generator", version="1.0.0")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Global state for job tracking
jobs: Dict[str, Dict] = {}
job_lock = threading.Lock()

# Resource limits
resource_limits = {
    "cpu_percent": 100,
    "memory_mb": 1024
}

class TimelapseRequest(BaseModel):
    input_folder: str
    output_folder: str
    fps: int = 30
    resolution: str = "1920x1080"
    output_format: str = "mp4"
    compression_quality: str = "medium"
    time_range_start: Optional[str] = None
    time_range_end: Optional[str] = None
    filename_pattern: Optional[str] = None
    cpu_limit: int = 100
    memory_limit_mb: int = 1024

class JobStatus(BaseModel):
    job_id: str
    status: str
    progress: float
    message: str
    output_file: Optional[str] = None

def validate_settings(request: TimelapseRequest) -> List[str]:
    """Validate user settings before processing starts"""
    errors = []
    
    # Validate input folder
    if not os.path.exists(request.input_folder):
        errors.append(f"Input folder does not exist: {request.input_folder}")
    
    # Validate output folder
    output_path = Path(request.output_folder)
    if not output_path.parent.exists():
        errors.append(f"Output folder parent does not exist: {request.output_folder}")
    
    # Validate FPS
    if request.fps < 1 or request.fps > 120:
        errors.append("FPS must be between 1 and 120")
    
    # Validate resolution
    try:
        width, height = map(int, request.resolution.split('x'))
        if width < 1 or height < 1:
            errors.append("Invalid resolution format")
    except:
        errors.append("Resolution must be in format WIDTHxHEIGHT (e.g., 1920x1080)")
    
    # Validate output format
    valid_formats = ['mp4', 'webm', 'avi', 'mov']
    if request.output_format not in valid_formats:
        errors.append(f"Output format must be one of: {', '.join(valid_formats)}")
    
    # Validate compression quality
    valid_qualities = ['ultrafast', 'superfast', 'veryfast', 'faster', 'fast', 'medium', 'slow', 'slower', 'veryslow']
    if request.compression_quality not in valid_qualities:
        errors.append(f"Compression quality must be one of: {', '.join(valid_qualities)}")
    
    # Validate resource limits
    if request.cpu_limit < 1 or request.cpu_limit > 100:
        errors.append("CPU limit must be between 1 and 100 percent")
    
    if request.memory_limit_mb < 64 or request.memory_limit_mb > 8192:
        errors.append("Memory limit must be between 64 and 8192 MB")
    
    return errors

def get_image_files(input_folder: str, pattern: Optional[str] = None, 
                   start_time: Optional[str] = None, end_time: Optional[str] = None) -> List[str]:
    """Get sorted list of image files from input folder"""
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'}
    files = []
    
    for file in os.listdir(input_folder):
        file_path = os.path.join(input_folder, file)
        if os.path.isfile(file_path):
            ext = Path(file).suffix.lower()
            if ext in image_extensions:
                # Apply filename pattern filter
                if pattern and pattern not in file:
                    continue
                
                # Apply time range filter if timestamps are in filename
                if start_time or end_time:
                    try:
                        # Try to extract timestamp from filename (assuming format like YYYY-MM-DD_HH-MM-SS)
                        timestamp_str = file.split('.')[0]
                        if len(timestamp_str) >= 19:  # YYYY-MM-DD_HH-MM-SS format
                            file_time = datetime.strptime(timestamp_str[:19], "%Y-%m-%d_%H-%M-%S")
                            
                            if start_time:
                                start_dt = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
                                if file_time < start_dt:
                                    continue
                            
                            if end_time:
                                end_dt = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
                                if file_time > end_dt:
                                    continue
                    except:
                        pass  # Skip time filtering if timestamp parsing fails
                
                files.append(file_path)
    
    return sorted(files)

def create_timelapse(job_id: str, request: TimelapseRequest):
    """Background task to create timelapse"""
    with job_lock:
        jobs[job_id] = {
            "status": "processing",
            "progress": 0.0,
            "message": "Starting timelapse generation...",
            "output_file": None
        }
    
    try:
        # Update resource limits
        global resource_limits
        resource_limits["cpu_percent"] = request.cpu_limit
        resource_limits["memory_mb"] = request.memory_limit_mb
        
        # Get image files
        with job_lock:
            jobs[job_id]["message"] = "Scanning input folder..."
        
        image_files = get_image_files(
            request.input_folder, 
            request.filename_pattern,
            request.time_range_start,
            request.time_range_end
        )
        
        if not image_files:
            with job_lock:
                jobs[job_id]["status"] = "failed"
                jobs[job_id]["message"] = "No image files found matching criteria"
            return
        
        with job_lock:
            jobs[job_id]["message"] = f"Found {len(image_files)} images, starting processing..."
        
        # Create output directory
        os.makedirs(request.output_folder, exist_ok=True)
        
        # Generate output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"timelapse_{timestamp}.{request.output_format}"
        output_path = os.path.join(request.output_folder, output_filename)
        
        # Create temporary file list for ffmpeg
        temp_list_file = f"/tmp/ffmpeg_list_{job_id}.txt"
        with open(temp_list_file, 'w') as f:
            for image_file in image_files:
                f.write(f"file '{image_file}'\n")
        
        # Build ffmpeg command
        ffmpeg_cmd = [
            "ffmpeg",
            "-f", "concat",
            "-safe", "0",
            "-i", temp_list_file,
            "-vf", f"fps={request.fps},scale={request.resolution}",
            "-c:v", "libx264" if request.output_format == "mp4" else "libvpx-vp9",
            "-preset", request.compression_quality,
            "-crf", "23",
            "-y",  # Overwrite output file
            output_path
        ]
        
        # Start ffmpeg process
        with job_lock:
            jobs[job_id]["message"] = "Running ffmpeg..."
        
        process = subprocess.Popen(
            ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        # Monitor process and update progress
        start_time = time.time()
        while process.poll() is None:
            # Check resource usage and limit if needed
            current_process = psutil.Process(process.pid)
            try:
                cpu_percent = current_process.cpu_percent()
                memory_mb = current_process.memory_info().rss / 1024 / 1024
                
                if cpu_percent > resource_limits["cpu_percent"]:
                    # Limit CPU usage by setting process priority
                    current_process.nice(10)
                
                if memory_mb > resource_limits["memory_mb"]:
                    # For memory, we can't easily limit it, but we can log it
                    pass
                    
            except psutil.NoSuchProcess:
                break
            
            # Estimate progress based on time (rough approximation)
            elapsed = time.time() - start_time
            estimated_total = len(image_files) / request.fps * 2  # Rough estimate
            progress = min(95.0, (elapsed / estimated_total) * 100) if estimated_total > 0 else 50.0
            
            with job_lock:
                jobs[job_id]["progress"] = progress
                jobs[job_id]["message"] = f"Processing... {progress:.1f}%"
            
            time.sleep(1)
        
        # Clean up temp file
        try:
            os.remove(temp_list_file)
        except:
            pass
        
        # Check if process completed successfully
        if process.returncode == 0 and os.path.exists(output_path):
            with job_lock:
                jobs[job_id]["status"] = "completed"
                jobs[job_id]["progress"] = 100.0
                jobs[job_id]["message"] = "Timelapse completed successfully!"
                jobs[job_id]["output_file"] = output_path
        else:
            stderr_output = process.stderr.read() if process.stderr else "Unknown error"
            with job_lock:
                jobs[job_id]["status"] = "failed"
                jobs[job_id]["message"] = f"FFmpeg failed: {stderr_output}"
                
    except Exception as e:
        with job_lock:
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["message"] = f"Error: {str(e)}"

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main web interface"""
    with open("static/index.html", "r") as f:
        return HTMLResponse(content=f.read())

@app.post("/api/timelapse", response_model=JobStatus)
async def create_timelapse_endpoint(request: TimelapseRequest, background_tasks: BackgroundTasks):
    """Create a new timelapse job"""
    # Validate settings
    errors = validate_settings(request)
    if errors:
        raise HTTPException(status_code=400, detail={"errors": errors})
    
    # Generate job ID
    job_id = str(uuid.uuid4())
    
    # Start background task
    background_tasks.add_task(create_timelapse, job_id, request)
    
    return JobStatus(
        job_id=job_id,
        status="queued",
        progress=0.0,
        message="Job queued successfully"
    )

@app.get("/api/job/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """Get status of a timelapse job"""
    with job_lock:
        if job_id not in jobs:
            raise HTTPException(status_code=404, detail="Job not found")
        
        job = jobs[job_id]
        return JobStatus(
            job_id=job_id,
            status=job["status"],
            progress=job["progress"],
            message=job["message"],
            output_file=job.get("output_file")
        )

@app.get("/api/jobs", response_model=List[JobStatus])
async def list_jobs():
    """List all jobs"""
    with job_lock:
        return [
            JobStatus(
                job_id=job_id,
                status=job["status"],
                progress=job["progress"],
                message=job["message"],
                output_file=job.get("output_file")
            )
            for job_id, job in jobs.items()
        ]

@app.get("/api/download/{job_id}")
async def download_timelapse(job_id: str):
    """Download completed timelapse"""
    with job_lock:
        if job_id not in jobs:
            raise HTTPException(status_code=404, detail="Job not found")
        
        job = jobs[job_id]
        if job["status"] != "completed" or not job.get("output_file"):
            raise HTTPException(status_code=400, detail="Timelapse not ready for download")
        
        if not os.path.exists(job["output_file"]):
            raise HTTPException(status_code=404, detail="Output file not found")
        
        filename = os.path.basename(job["output_file"])
        return FileResponse(
            path=job["output_file"],
            filename=filename,
            media_type="video/mp4"
        )

@app.get("/api/system/info")
async def get_system_info():
    """Get system information"""
    return {
        "cpu_count": psutil.cpu_count(),
        "memory_total_mb": psutil.virtual_memory().total / 1024 / 1024,
        "disk_usage": psutil.disk_usage('/')._asdict(),
        "current_resource_limits": resource_limits
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 