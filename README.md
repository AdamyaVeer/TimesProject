# Video Duplicate Detector and Archiver

This tool helps identify duplicate videos by comparing their actual content and provides options to archive them for memory optimization. It includes both a command-line interface and a modern web interface.

## Features

- Identifies duplicate videos using perceptual hashing
- Compares video content frame by frame
- Archives duplicate videos to save space
- Generates report of duplicate videos found
- Modern web interface with drag-and-drop upload
- Real-time progress tracking
- Downloadable results

## Installation

1. Clone this repository
2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```
3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Web Interface

1. Set up environment variables (copy .env.example to .env and modify as needed)
2. Run the Flask application:
```bash
# Development
flask run

# Production
gunicorn app:app
```
3. Open your browser and navigate to http://localhost:5000

### Command Line Interface

Run the main script:
```bash
python video_duplicate_detector.py --input_dir /path/to/videos --output_dir /path/to/archive
```

### Arguments
- `--input_dir`: Directory containing videos to analyze
- `--output_dir`: Directory where duplicates will be archived
- `--threshold`: Similarity threshold (default: 0.95)
- `--sample_rate`: Frame sampling rate (default: 1 frame per second)

## How it works

1. The tool extracts frames from videos at regular intervals
2. Generates perceptual hashes for each frame
3. Compares video signatures to identify duplicates
4. Archives duplicate videos while keeping originals intact

## Deployment

### Environment Variables

Create a `.env` file with the following variables:
```
FLASK_ENV=production
FLASK_APP=app.py
SECRET_KEY=your-secret-key-here
UPLOAD_FOLDER=uploads
ARCHIVE_FOLDER=archive
MAX_CONTENT_LENGTH=1073741824
```

### Deploying to Production

The application is configured for deployment on platforms like Render.com:

1. Push your code to a Git repository
2. Create a new Web Service on your hosting platform
3. Set the following:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
   - Environment Variables: Copy from your `.env` file

## Supported Video Formats

- MP4 (.mp4)
- AVI (.avi)
- MOV (.mov)
- MKV (.mkv)
- FLV (.flv)
- WMV (.wmv)

## License

This project is licensed under the MIT License - see the LICENSE file for details. 