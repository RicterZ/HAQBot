import os
import subprocess
import uuid
from typing import Optional

from meteion.utils.logger import logger


def download_video_stream(url: str, output_path: Optional[str] = None, duration: int = 60) -> Optional[str]:
    """
    Download video stream using ffmpeg and save to a file
    
    Args:
        url: Video stream URL
        output_path: Optional output file path. If not provided, will save to /data/napcat/videos/
        duration: Duration in seconds to record (default: 60 seconds)
        
    Returns:
        Path to the downloaded video file, or None if failed
    """
    if output_path is None:
        output_dir = '/data/napcat/videos'
        os.makedirs(output_dir, exist_ok=True)
        filename = f"video_{uuid.uuid4().hex[:8]}.mp4"
        output_path = os.path.join(output_dir, filename)
    
    try:
        cmd = [
            'ffmpeg',
            '-extension_picky', '0',
            '-allowed_extensions', 'ALL',
            '-i', url,
            '-t', str(duration),
            '-c', 'copy',
            '-f', 'mp4',
            '-y',
            output_path
        ]
        
        logger.info(f"Command: {' '.join(cmd)}")
        logger.info(f"Downloading video stream from {url} using ffmpeg (max duration: {duration}s)...")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=duration + 30  # Add 30 seconds buffer
        )
        
        file_exists = os.path.exists(output_path) and os.path.getsize(output_path) > 0
        
        if result.returncode != 0:
            if file_exists:
                logger.info(f"ffmpeg exited with code {result.returncode}, but file was created successfully")
            else:
                logger.error(f"ffmpeg exited with code {result.returncode}")
                logger.error(f"ffmpeg stderr:\n{result.stderr}")
                logger.error(f"ffmpeg stdout:\n{result.stdout}")
                if os.path.exists(output_path):
                    os.remove(output_path)
                return None
        
        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            logger.error("Downloaded file is empty or does not exist")
            if os.path.exists(output_path):
                os.remove(output_path)
            return None
        
        file_size = os.path.getsize(output_path)
        logger.info(f"Successfully downloaded video stream to {output_path} ({file_size} bytes)")
        return output_path
        
    except subprocess.TimeoutExpired:
        logger.error(f"ffmpeg timeout while downloading video stream")
        if os.path.exists(output_path):
            os.remove(output_path)
        return None
    except FileNotFoundError:
        logger.error("ffmpeg not found. Please install ffmpeg.")
        return None
    except Exception as e:
        logger.error(f"Error downloading video stream: {e}")
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except:
                pass
        return None


async def download_video_stream_async(url: str, output_path: Optional[str] = None, duration: int = 60) -> Optional[str]:
    """
    Async version of download_video_stream
    
    Args:
        url: Video stream URL
        output_path: Optional output file path. If not provided, will save to /data/napcat/videos/
        duration: Duration in seconds to record (default: 60 seconds)
        
    Returns:
        Path to the downloaded video file, or None if failed
    """
    import asyncio
    
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, download_video_stream, url, output_path, duration)

