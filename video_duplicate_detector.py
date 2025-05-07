import cv2
import numpy as np
import imagehash
from PIL import Image
import os
import shutil
from tqdm import tqdm
import argparse
from pathlib import Path
from typing import List, Dict, Tuple
import logging
from datetime import datetime

class VideoSignature:
    def __init__(self, filepath: str, sample_rate: int = 1):
        self.filepath = filepath
        self.sample_rate = sample_rate
        self.frame_hashes = []
        self._generate_signature()
    
    def _generate_signature(self):
        """Generate a signature for the video by hashing sampled frames."""
        cap = cv2.VideoCapture(self.filepath)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # Calculate frames to sample
        sample_interval = int(fps * self.sample_rate)
        
        for frame_idx in range(0, frame_count, sample_interval):
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if ret:
                # Convert BGR to RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                # Convert to PIL Image
                pil_image = Image.fromarray(frame_rgb)
                # Calculate perceptual hash
                frame_hash = str(imagehash.average_hash(pil_image))
                self.frame_hashes.append(frame_hash)
        
        cap.release()

    def compare_with(self, other: 'VideoSignature', threshold: float = 0.95) -> float:
        """Compare this video signature with another one."""
        if not self.frame_hashes or not other.frame_hashes:
            return 0.0
        
        # Compare frame hashes
        min_len = min(len(self.frame_hashes), len(other.frame_hashes))
        matches = sum(1 for i in range(min_len) 
                     if self.frame_hashes[i] == other.frame_hashes[i])
        
        return matches / min_len

class VideoDuplicateDetector:
    def __init__(self, input_dir: str, output_dir: str, threshold: float = 0.95, 
                 sample_rate: int = 1):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.threshold = threshold
        self.sample_rate = sample_rate
        self.video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv'}
        
        # Setup logging
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup logging configuration."""
        log_file = self.output_dir / f'duplicate_detection_{datetime.now():%Y%m%d_%H%M%S}.log'
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
    
    def _get_video_files(self) -> List[Path]:
        """Get all video files from the input directory."""
        video_files = []
        for ext in self.video_extensions:
            video_files.extend(self.input_dir.glob(f'**/*{ext}'))
        return video_files
    
    def _archive_duplicate(self, duplicate_file: Path, original_file: Path):
        """Archive a duplicate video file."""
        archive_path = self.output_dir / 'duplicates' / duplicate_file.relative_to(self.input_dir)
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Move the file to archive
        shutil.move(str(duplicate_file), str(archive_path))
        
        # Create a text file with original file information
        info_file = archive_path.with_suffix('.txt')
        with open(info_file, 'w') as f:
            f.write(f'Original file: {original_file}\n')
            f.write(f'Archived on: {datetime.now():%Y-%m-%d %H:%M:%S}\n')
    
    def detect_and_archive(self):
        """Main method to detect and archive duplicate videos."""
        video_files = self._get_video_files()
        if not video_files:
            logging.warning("No video files found in the input directory!")
            return
        
        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate signatures for all videos
        signatures: Dict[Path, VideoSignature] = {}
        logging.info("Generating video signatures...")
        for video_file in tqdm(video_files, desc="Processing videos"):
            try:
                signatures[video_file] = VideoSignature(str(video_file), self.sample_rate)
            except Exception as e:
                logging.error(f"Error processing {video_file}: {str(e)}")
        
        # Find and process duplicates
        duplicates_found = False
        processed_files = set()
        
        logging.info("Comparing videos for duplicates...")
        for file1 in tqdm(video_files, desc="Comparing videos"):
            if file1 in processed_files:
                continue
                
            for file2 in video_files:
                if file1 == file2 or file2 in processed_files:
                    continue
                
                similarity = signatures[file1].compare_with(signatures[file2], self.threshold)
                
                if similarity >= self.threshold:
                    duplicates_found = True
                    processed_files.add(file2)
                    
                    # Keep the older file as original
                    original = file1 if file1.stat().st_mtime < file2.stat().st_mtime else file2
                    duplicate = file2 if original == file1 else file1
                    
                    logging.info(f"Found duplicate:\nOriginal: {original}\nDuplicate: {duplicate}")
                    self._archive_duplicate(duplicate, original)
        
        if not duplicates_found:
            logging.info("No duplicates found!")
        else:
            logging.info("Duplicate detection and archiving completed!")

def main():
    parser = argparse.ArgumentParser(description='Detect and archive duplicate videos')
    parser.add_argument('--input_dir', required=True, help='Input directory containing videos')
    parser.add_argument('--output_dir', required=True, help='Output directory for archived duplicates')
    parser.add_argument('--threshold', type=float, default=0.95, 
                       help='Similarity threshold (0.0 to 1.0)')
    parser.add_argument('--sample_rate', type=int, default=1,
                       help='Frame sampling rate in seconds')
    
    args = parser.parse_args()
    
    detector = VideoDuplicateDetector(
        args.input_dir,
        args.output_dir,
        args.threshold,
        args.sample_rate
    )
    
    detector.detect_and_archive()

if __name__ == '__main__':
    main() 