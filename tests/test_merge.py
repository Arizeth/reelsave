"""Offline integration: real yt-dlp merger and FFmpeg, no platform access."""
import json
import subprocess

from yt_dlp import YoutubeDL
from yt_dlp.postprocessor.ffmpeg import FFmpegMergerPP


def test_real_mp4_merge(tmp_path):
    video, audio, output = [tmp_path / name for name in ('silent.mp4', 'audio.m4a', 'merged.mp4')]
    subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'color=c=teal:s=160x90:d=1', '-an', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(video)], check=True, timeout=20)
    subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=1', '-vn', '-c:a', 'aac', str(audio)], check=True, timeout=20)
    with YoutubeDL({'quiet': True}) as downloader:
        FFmpegMergerPP(downloader).run({'filepath':str(output), 'ext':'mp4', '__files_to_merge':[str(video), str(audio)], 'requested_formats':[
            {'filepath':str(video), 'vcodec':'h264', 'acodec':'none', 'protocol':'https'},
            {'filepath':str(audio), 'vcodec':'none', 'acodec':'aac', 'protocol':'https'},
        ]})
    result = subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-of', 'json', str(output)], capture_output=True, check=True, timeout=10)
    streams = json.loads(result.stdout)['streams']
    assert {stream['codec_type'] for stream in streams} == {'video', 'audio'}
    assert output.stat().st_size > 0
