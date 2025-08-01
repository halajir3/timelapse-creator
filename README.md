# 🎬 Timelapse Generator for TrueNAS Scale

A powerful, web-based timelapse generator application designed specifically for TrueNAS Scale. Create beautiful timelapse videos from image sequences with full control over video settings and resource management.

## ✨ Features

- **Web Interface**: Modern, responsive web UI with no CLI required
- **Flexible Input**: Browse and select input folders from mounted storage
- **Customizable Output**: Set output folder, format, resolution, and quality
- **Advanced Filtering**: Time range and filename pattern filtering
- **Resource Management**: CPU and memory limits controlled from UI
- **Progress Tracking**: Real-time progress updates and job history
- **Multiple Formats**: Support for MP4, WebM, AVI, and MOV
- **TrueNAS Integration**: Designed for TrueNAS Scale container orchestration

## 🚀 Quick Start

### Prerequisites

- TrueNAS Scale with Kubernetes enabled
- NFS or SMB share mounted for input/output storage
- Docker or container runtime

### Option 1: Direct Kubernetes Deployment

1. **Build the Docker image:**
   ```bash
   docker build -t timelapse-generator:latest .
   ```

2. **Deploy to TrueNAS Scale:**
   ```bash
   kubectl apply -f app.yaml
   ```

3. **Access the application:**
   - Navigate to `http://your-truenas-ip/timelapse-generator`
   - Or use the ingress host: `http://timelapse-generator.local`

### Option 2: Helm Chart Deployment

1. **Install using Helm:**
   ```bash
   helm install timelapse-generator ./helm-chart
   ```

2. **Customize deployment:**
   ```bash
   helm install timelapse-generator ./helm-chart \
     --set persistence.storageClass="your-storage-class" \
     --set ingress.hosts[0].host="your-domain.com"
   ```

## 📁 Directory Structure

```
timelapse-generator/
├── app.py                 # Main FastAPI application
├── requirements.txt       # Python dependencies
├── Dockerfile            # Container definition
├── app.yaml              # Kubernetes deployment
├── helm-chart/           # Helm chart for advanced deployment
│   ├── Chart.yaml
│   ├── values.yaml
│   └── templates/
├── static/
│   └── index.html        # Web interface
└── README.md
```

## 🔧 Configuration

### Storage Setup

The application expects a shared directory structure like:
```
/mnt/nfs_share/
├── 2024-01-15/           # Input folder with images
│   ├── image001.jpg
│   ├── image002.jpg
│   └── ...
├── 2024-01-16/
└── timelapses/           # Output folder
    └── timelapse_20240115_143022.mp4
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PYTHONUNBUFFERED` | `1` | Ensures Python output is not buffered |

### Resource Limits

The application supports dynamic resource management:

- **CPU Limit**: 1-100% (controlled via UI)
- **Memory Limit**: 64MB-8GB (controlled via UI)
- **Default Limits**: 1 CPU core, 2GB RAM

## 🎯 Usage

### Creating a Timelapse

1. **Input Settings:**
   - Set input folder path (e.g., `/mnt/nfs_share/2024-01-15`)
   - Set output folder path (e.g., `/mnt/nfs_share/timelapses`)

2. **Video Settings:**
   - **FPS**: 1-120 frames per second
   - **Resolution**: 480p to 4K options
   - **Format**: MP4, WebM, AVI, or MOV
   - **Quality**: Ultrafast to Very Slow compression

3. **Filter Settings (Optional):**
   - **Time Range**: Filter by start/end timestamps
   - **Filename Pattern**: Filter by filename content

4. **Resource Limits:**
   - Set CPU usage limit (1-100%)
   - Set memory limit (64MB-8GB)

5. **Submit Job:**
   - Click "Create Timelapse"
   - Monitor progress in real-time
   - Download completed video

### Supported Image Formats

- JPEG (.jpg, .jpeg)
- PNG (.png)
- BMP (.bmp)
- TIFF (.tiff, .tif)

### Video Output Formats

| Format | Codec | Best For |
|--------|-------|----------|
| MP4 | H.264 | General use, wide compatibility |
| WebM | VP9 | Web streaming, smaller files |
| AVI | Various | Legacy compatibility |
| MOV | H.264 | Apple ecosystem |

## 🔍 API Endpoints

### REST API

- `GET /` - Web interface
- `POST /api/timelapse` - Create new timelapse job
- `GET /api/job/{job_id}` - Get job status
- `GET /api/jobs` - List all jobs
- `GET /api/download/{job_id}` - Download completed video
- `GET /api/system/info` - System information

### Job Status Values

- `queued` - Job is waiting to start
- `processing` - Job is currently running
- `completed` - Job finished successfully
- `failed` - Job encountered an error

## 🛠️ Development

### Local Development

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run locally:**
   ```bash
   python app.py
   ```

3. **Access at:** `http://localhost:8000`

### Building for Production

1. **Build Docker image:**
   ```bash
   docker build -t timelapse-generator:latest .
   ```

2. **Test locally:**
   ```bash
   docker run -p 8000:8000 -v /path/to/shared:/mnt/nfs_share timelapse-generator:latest
   ```

## 🔒 Security Considerations

- The application runs with minimal privileges
- Input validation prevents path traversal attacks
- Resource limits prevent DoS attacks
- Temporary files are cleaned up automatically

## 📊 Monitoring

### Health Checks

The application includes built-in health checks:
- Liveness probe: `/api/system/info`
- Readiness probe: `/api/system/info`

### Logging

- Application logs are available via `kubectl logs`
- Job progress is tracked in real-time
- Error messages are displayed in the UI

## 🐛 Troubleshooting

### Common Issues

1. **"Input folder does not exist"**
   - Verify the folder path is correct
   - Ensure the folder is mounted and accessible

2. **"No image files found"**
   - Check that the folder contains supported image formats
   - Verify filename patterns if using filters

3. **"FFmpeg failed"**
   - Check system resources (CPU/memory)
   - Verify input images are not corrupted
   - Check available disk space

4. **"Permission denied"**
   - Ensure proper file permissions on input/output folders
   - Check Kubernetes security contexts

### Debug Mode

Enable debug logging by setting the environment variable:
```bash
export PYTHONUNBUFFERED=1
export LOG_LEVEL=DEBUG
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Built with FastAPI for high-performance web API
- Uses FFmpeg for video processing
- Designed for TrueNAS Scale integration
- Modern UI with vanilla HTML/CSS/JavaScript

## 📞 Support

For issues and questions:
- Create an issue on GitHub
- Check the troubleshooting section
- Review the API documentation

---

**Happy Timelapsing! 🎬** 