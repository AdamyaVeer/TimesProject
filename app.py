from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from video_duplicate_detector import VideoDuplicateDetector
import json
from pathlib import Path
import logging
import shutil
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO if os.getenv('FLASK_ENV') == 'production' else logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', os.urandom(24))
app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads'))
app.config['ARCHIVE_FOLDER'] = os.getenv('ARCHIVE_FOLDER', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'archive'))
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_CONTENT_LENGTH', 1024 * 1024 * 1024))  # 1GB max file size

# Clean up and create fresh directories
def setup_directories():
    # Clean up existing directories
    if os.path.exists(app.config['UPLOAD_FOLDER']):
        shutil.rmtree(app.config['UPLOAD_FOLDER'])
    if os.path.exists(app.config['ARCHIVE_FOLDER']):
        shutil.rmtree(app.config['ARCHIVE_FOLDER'])
    
    # Create fresh directories
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['ARCHIVE_FOLDER'], exist_ok=True)
    os.makedirs(os.path.join(app.config['ARCHIVE_FOLDER'], 'duplicates'), exist_ok=True)
    
    logger.info(f"Directories setup complete. Upload folder: {app.config['UPLOAD_FOLDER']}")

setup_directories()

ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'flv', 'wmv'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    # Clean up directories on page load
    setup_directories()
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'video' not in request.files:
        logger.error('No video file in request')
        return jsonify({'error': 'No video file provided'}), 400
    
    file = request.files['video']
    if file.filename == '':
        logger.error('Empty filename provided')
        return jsonify({'error': 'No selected file'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        if os.path.exists(filepath):
            file_size = os.path.getsize(filepath)
            logger.info(f'Successfully uploaded file: {filename} (Size: {file_size} bytes)')
            return jsonify({
                'message': 'File uploaded successfully',
                'filename': filename,
                'size': file_size
            })
        else:
            logger.error(f'File not found after upload: {filepath}')
            return jsonify({'error': 'File upload failed'}), 500
    
    logger.error(f'Invalid file type: {file.filename}')
    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/detect', methods=['POST'])
def detect_duplicates():
    try:
        threshold = float(request.form.get('threshold', 0.95))
        sample_rate = int(request.form.get('sample_rate', 1))
        
        logger.info(f'Starting detection with threshold={threshold}, sample_rate={sample_rate}')
        logger.info(f'Upload directory contents: {os.listdir(app.config["UPLOAD_FOLDER"])}')
        
        # Check if there are any videos in the upload folder
        upload_dir = Path(app.config['UPLOAD_FOLDER'])
        video_files = [f for f in upload_dir.glob('*') if f.suffix.lower()[1:] in ALLOWED_EXTENSIONS]
        
        if not video_files:
            logger.warning('No video files found in upload directory')
            return jsonify({'error': 'No videos found for analysis'}), 400
        
        logger.info(f'Found {len(video_files)} videos to analyze: {[f.name for f in video_files]}')
        
        detector = VideoDuplicateDetector(
            str(app.config['UPLOAD_FOLDER']),
            str(app.config['ARCHIVE_FOLDER']),
            threshold,
            sample_rate
        )
        
        detector.detect_and_archive()
        logger.info('Detection completed successfully')
        return jsonify({
            'message': 'Analysis complete',
            'files_processed': len(video_files),
            'processed_files': [f.name for f in video_files]
        })
    except Exception as e:
        logger.error(f'Error during detection: {str(e)}', exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/results')
def get_results():
    try:
        archive_path = Path(app.config['ARCHIVE_FOLDER']) / 'duplicates'
        results = []
        
        logger.info(f'Checking for results in {archive_path}')
        
        if archive_path.exists():
            txt_files = list(archive_path.glob('*.txt'))
            logger.info(f'Found {len(txt_files)} result files')
            
            for txt_file in txt_files:
                try:
                    with open(txt_file, 'r') as f:
                        info = f.read().splitlines()
                        video_file = txt_file.with_suffix('.mp4')
                        if video_file.exists():
                            results.append({
                                'duplicate': video_file.name,
                                'original': info[0].replace('Original file: ', ''),
                                'archived_date': info[1].replace('Archived on: ', '')
                            })
                except Exception as e:
                    logger.error(f'Error processing result file {txt_file}: {str(e)}')
        else:
            logger.info('No results directory found')
        
        logger.info(f'Returning {len(results)} results')
        return jsonify(results)
    except Exception as e:
        logger.error(f'Error getting results: {str(e)}', exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/download/<path:filename>')
def download_file(filename):
    try:
        return send_from_directory(
            os.path.join(app.config['ARCHIVE_FOLDER'], 'duplicates'),
            filename,
            as_attachment=True
        )
    except Exception as e:
        logger.error(f'Error downloading file {filename}: {str(e)}')
        return jsonify({'error': 'File not found'}), 404

if __name__ == '__main__':
    app.run(debug=True) 