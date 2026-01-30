"""URL download utilities for webhook multimodal messages"""
import os
import subprocess
import uuid
from typing import Optional, Literal
from urllib.parse import urlparse

import httpx
from maid.utils.logger import logger


def detect_url_type(url: str) -> Literal["video", "image", "file"]:
    """
    Detect URL type based on protocol and file extension

    Args:
        url: URL to detect

    Returns:
        "video", "image", or "file"
    """
    url_lower = url.lower()
    parsed = urlparse(url)

    # Check protocol
    if parsed.scheme in ("rtsp", "rtmp", "rtspt", "rtmpt"):
        return "video"

    # Check file extension
    path = parsed.path.lower()

    # Video formats
    video_extensions = (
        ".mp4", ".avi", ".mov", ".mkv", ".flv", ".webm", ".m4v", ".3gp",
        ".m3u8", ".ts", ".mpeg", ".mpg", ".wmv", ".asf", ".rm", ".rmvb"
    )
    if any(path.endswith(ext) for ext in video_extensions):
        return "video"

    # Check for m3u8 in path (HLS stream)
    if ".m3u8" in path or "m3u8" in url_lower:
        return "video"

    # Image formats
    image_extensions = (
        ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg",
        ".ico", ".tiff", ".tif", ".heic", ".heif"
    )
    if any(path.endswith(ext) for ext in image_extensions):
        return "image"

    # Default to file
    return "file"


async def download_file_async(
    url: str,
    output_path: Optional[str] = None,
    output_dir: Optional[str] = None,
    timeout: int = 30
) -> Optional[str]:
    """
    Download a file from URL asynchronously

    Args:
        url: URL to download
        output_path: Optional output file path
        output_dir: Optional output directory (if output_path not provided)
        timeout: Request timeout in seconds

    Returns:
        Path to the downloaded file, or None if failed
    """
    if output_path is None:
        if output_dir is None:
            output_dir = '/data/napcat/videos'
        os.makedirs(output_dir, exist_ok=True)

        # Extract extension from URL or use default
        parsed = urlparse(url)
        ext = os.path.splitext(parsed.path)[1] or '.bin'
        filename = f"download_{uuid.uuid4().hex[:8]}{ext}"
        output_path = os.path.join(output_dir, filename)

    try:
        logger.info(f"Downloading file from {url} to {output_path}...")

        async with httpx.AsyncClient(timeout=httpx.Timeout(timeout), follow_redirects=True) as client:
            async with client.stream("GET", url) as response:
                response.raise_for_status()

                with open(output_path, "wb") as f:
                    async for chunk in response.aiter_bytes():
                        f.write(chunk)

        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            logger.error("Downloaded file is empty or does not exist")
            if os.path.exists(output_path):
                os.remove(output_path)
            return None

        file_size = os.path.getsize(output_path)
        logger.info(f"Successfully downloaded file to {output_path} ({file_size} bytes)")
        return output_path

    except httpx.TimeoutException:
        logger.error(f"Timeout while downloading file from {url}")
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except:
                pass
        return None
    except Exception as e:
        logger.error(f"Error downloading file from {url}: {e}")
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except:
                pass
        return None


async def download_image_async(
    url: str,
    output_path: Optional[str] = None,
    timeout: int = 30
) -> Optional[str]:
    """
    Download an image from URL asynchronously

    Args:
        url: Image URL to download
        output_path: Optional output file path
        timeout: Request timeout in seconds

    Returns:
        Path to the downloaded image file, or None if failed
    """
    if output_path is None:
        output_dir = '/data/napcat/videos'
        os.makedirs(output_dir, exist_ok=True)

        # Extract extension from URL or use .jpg as default
        parsed = urlparse(url)
        ext = os.path.splitext(parsed.path)[1] or '.jpg'
        filename = f"image_{uuid.uuid4().hex[:8]}{ext}"
        output_path = os.path.join(output_dir, filename)

    return await download_file_async(url, output_path, timeout=timeout)


def download_video_stream(url: str, output_path: Optional[str] = None, duration: int = 60) -> Optional[str]:
    """
    Download video stream using ffmpeg and save to a file
    Supports RTSP, HLS (m3u8), and other video formats

    Args:
        url: Video stream URL (rtsp://, http:// with m3u8, or direct video file URL)
        output_path: Optional output file path. If not provided, will save to /data/napcat/videos/
        duration: Duration in seconds to record (default: 60 seconds, only for streams)

    Returns:
        Path to the downloaded video file, or None if failed
    """
    if output_path is None:
        output_dir = '/data/napcat/videos'
        os.makedirs(output_dir, exist_ok=True)

        # Extract extension from URL or use .mp4 as default
        parsed = urlparse(url)
        ext = os.path.splitext(parsed.path)[1]
        if not ext or ext == '.m3u8':
            ext = '.mp4'
        filename = f"video_{uuid.uuid4().hex[:8]}{ext}"
        output_path = os.path.join(output_dir, filename)

    try:
        # Check if it's a stream (rtsp, m3u8) or a direct video file
        url_lower = url.lower()
        is_stream = (
            url.startswith(('rtsp://', 'rtmp://', 'rtspt://', 'rtmpt://')) or
            '.m3u8' in url_lower
        )

        if is_stream:
            # For streams, use duration limit
            cmd = [
                'ffmpeg',
                '-extension_picky', '0',
                '-allowed_extensions', 'ALL',

                '-i', url,
                '-t', str(duration),

                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-f', 'mp4',
                '-y',
                output_path
            ]
            timeout = duration + 30  # Add 30 seconds buffer
        else:
            # For direct video files, just download/convert
            cmd = [
                'ffmpeg',
                '-extension_picky', '0',
                '-allowed_extensions', 'ALL',

                '-i', url,
                '-c', 'copy',
                '-t', '10',
                output_path
            ]
            timeout = 300  # 5 minutes for large files

        logger.info(f"Command: {' '.join(cmd)}")
        logger.info(f"Downloading video from {url} using ffmpeg...")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
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
        logger.info(f"Successfully downloaded video to {output_path} ({file_size} bytes)")
        return output_path

    except subprocess.TimeoutExpired:
        logger.error(f"ffmpeg timeout while downloading video")
        if os.path.exists(output_path):
            os.remove(output_path)
        return None
    except FileNotFoundError:
        logger.error("ffmpeg not found. Please install ffmpeg.")
        return None
    except Exception as e:
        logger.error(f"Error downloading video: {e}")
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except:
                pass
        return None


async def download_video_stream_async(
    url: str,
    output_path: Optional[str] = None,
    duration: int = 60
) -> Optional[str]:
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
