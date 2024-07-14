import os
import yt_dlp
import instaloader
import requests
from django.shortcuts import render
from django.http import HttpResponse
from .forms import VideoDownloadForm
from pathlib import Path

DOWNLOAD_FOLDER = str(Path.home() / "Downloads")

import os
import re
import yt_dlp

def get_video_title(url):
    ydl_opts = {
        'quiet': True,
        'skip_download': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=False)
        title = info_dict.get('title', 'unknown_video')
    return title

def sanitize_filename(filename):
    return re.sub(r'[<>:"/\\|?*]', '_', filename)

def download_youtube_video(url, download_folder):
    unique_filename = get_video_title(url)
    sanitized_filename = sanitize_filename(unique_filename)
    ydl_opts = {
         # Specify the format ID to download
        'outtmpl': os.path.join(download_folder, f'{sanitized_filename}.%(ext)s'),
        'noplaylist': True,
        'nocache': True,  # Ensures no cache is used
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            duration = info_dict.get('duration', 0)
            if duration < 5 or duration > 120:
                return None, f"Video duration is {duration} seconds, which is outside the allowed range."
            ydl.download([url])
            video_path = os.path.join(download_folder, f'{sanitized_filename}.mp4')
            return video_path, None
    except Exception as e:
        return None, f"Failed to download YouTube video: {e}"


def download_other_video(url, download_folder):
    unique_filename = get_video_title(url)
    ydl_opts = {
        'format': 'best',
        'outtmpl': os.path.join(download_folder, f'{unique_filename}.%(ext)s'),
        'noplaylist': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            duration = info_dict.get('duration', 0)
            if duration < 5 or duration > 120:
                return None, f"Video duration is {duration} seconds, which is outside the allowed range."
            info_dict = ydl.extract_info(url, download=True)
            video_path = ydl.prepare_filename(info_dict)
            base, ext = os.path.splitext(video_path)
            if ext != '.mp4':
                video_path = base + '.mp4'
            return video_path, None
    except Exception as e:
        return None, str(e)


def download_instagram_reel(reel_url, download_folder):
    try:
        L = instaloader.Instaloader()
        if not os.path.exists(download_folder):
            os.makedirs(download_folder)
        shortcode = reel_url.split("/")[-2]
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        video_url = post.video_url
        unique_filename = sanitize_filename(post.title if post.title else shortcode)
        if video_url:
            response = requests.get(video_url, stream=True)
            video_path = os.path.join(download_folder, f"{unique_filename}.mp4")
            with open(video_path, 'wb') as video_file:
                for chunk in response.iter_content(chunk_size=8192):
                    video_file.write(chunk)
            return video_path, None
        else:
            return None, "No video found in the post."
    except Exception as e:
        return None, str(e)
    
    
def download_video(request):
    if request.method == 'POST':
        form = VideoDownloadForm(request.POST)
        if form.is_valid():
            video_type = form.cleaned_data['video_type']
            url = form.cleaned_data['url']
            download_folder = DOWNLOAD_FOLDER

            if video_type == '1':
                video_path, error = download_youtube_video(url, download_folder)
            elif video_type == '2':
                video_path, error = download_instagram_reel(url, download_folder)
            elif video_type == '3':
                video_path, error = download_other_video(url, download_folder)
            else:
                error = "Invalid video type selected."

            if video_path:
                with open(video_path, 'rb') as video_file:
                    response = HttpResponse(video_file.read(), content_type='video/mp4')
                    response['Content-Disposition'] = f'attachment; filename={os.path.basename(video_path)}'
                    return response
            else:
                return render(request, 'downloader/index.html', {'form': form, 'error': error})
    else:
        form = VideoDownloadForm()
    return render(request, 'downloader/index.html', {'form': form})
