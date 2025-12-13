import os
import subprocess
import tempfile
from typing import Optional

from meteion.utils.logger import logger


def download_video_stream(url: str, output_path: Optional[str] = None, duration: int = 60) -> Optional[str]:
    """
    Download video stream using ffmpeg and save to a file
    
    Args:
        url: Video stream URL
        output_path: Optional output file path. If not provided, a temporary file will be created
        duration: Duration in seconds to record (default: 60 seconds)
        
    Returns:
        Path to the downloaded video file, or None if failed
    """
    if output_path is None:
        # Create a temporary file
        temp_fd, output_path = tempfile.mkstemp(suffix='.mp4', prefix='video_')
        os.close(temp_fd)
    
    try:
        # Use ffmpeg to download and convert the video stream
        # -allowed_extensions ALL: allow all HLS segment extensions (needed for some streams)
        # -t: duration in seconds
        # -c copy: copy codec (faster, but may not work for all streams)
        # -y: overwrite output file
        cmd = [
            'ffmpeg',
            '-allowed_extensions', 'ALL',
            '-i', url,
            '-t', str(duration),
            '-c', 'copy',
            '-y',
            output_path
        ]
        
        logger.info(f"Downloading video stream from {url} using ffmpeg (max duration: {duration}s)...")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=duration + 30  # Add 30 seconds buffer
        )
        
        # Check if output file exists and has content, even if returncode is non-zero
        # ffmpeg may exit with non-zero code for various reasons (stream end, etc.) but still produce valid output
        file_exists = os.path.exists(output_path) and os.path.getsize(output_path) > 0
        
        if result.returncode != 0 and not file_exists:
            logger.error(f"ffmpeg exited with code {result.returncode}")
            logger.error(f"ffmpeg stderr:\n{result.stderr}")
            logger.error(f"ffmpeg stdout:\n{result.stdout}")
            # Try with re-encoding if copy failed
            logger.info("Retrying with re-encoding...")
            cmd_reencode = [
                'ffmpeg',
                '-allowed_extensions', 'ALL',
                '-i', url,
                '-t', str(duration),
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-y',
                output_path
            ]
            result = subprocess.run(
                cmd_reencode,
                capture_output=True,
                text=True,
                timeout=duration + 60  # More time for re-encoding
            )
            
            # Check again if file exists after re-encoding
            file_exists = os.path.exists(output_path) and os.path.getsize(output_path) > 0
            
            if result.returncode != 0 and not file_exists:
                logger.error(f"ffmpeg re-encoding also failed with code {result.returncode}")
                logger.error(f"ffmpeg stderr:\n{result.stderr}")
                logger.error(f"ffmpeg stdout:\n{result.stdout}")
                if os.path.exists(output_path):
                    os.remove(output_path)
                return None
            elif file_exists:
                logger.info("Re-encoding succeeded, file created successfully")
        elif file_exists:
            # File exists, even if returncode is non-zero, it might be valid
            # (e.g., stream ended early, which is normal)
            if result.returncode != 0:
                logger.info(f"Video stream ended early or ffmpeg exited with code {result.returncode}, but file was created successfully")
        
        # Final check: ensure file exists and has content
        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            logger.error("Downloaded file is empty or does not exist")
            if os.path.exists(output_path):
                os.remove(output_path)
            return None
        
        file_size = os.path.getsize(output_path)
        # Try to get actual video duration if possible (optional info)
        actual_duration = None
        try:
            duration_check = subprocess.run(
                ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', output_path],
                capture_output=True,
                text=True,
                timeout=5
            )
            if duration_check.returncode == 0 and duration_check.stdout.strip():
                actual_duration = float(duration_check.stdout.strip())
                logger.info(f"Video duration: {actual_duration:.2f}s (requested: {duration}s)")
        except Exception:
            pass  # ffprobe not available or failed, not critical
        
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
        output_path: Optional output file path. If not provided, a temporary file will be created
        duration: Duration in seconds to record (default: 60 seconds)
        
    Returns:
        Path to the downloaded video file, or None if failed
    """
    import asyncio
    
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, download_video_stream, url, output_path, duration)

