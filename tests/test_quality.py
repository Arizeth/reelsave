import asyncio
import json
from pathlib import Path
import subprocess
import sys

import pytest
from yt_dlp import YoutubeDL
import app as module


def formats():
    return [
        {'format_id':'audio', 'url':'https://example.com/a', 'ext':'m4a', 'vcodec':'none', 'acodec':'aac'},
        *[{'format_id':str(q), 'url':'https://example.com/v', 'ext':'mp4', 'width':q, 'height':q*16//9, 'vcodec':'av1', 'acodec':'none'} for q in (720,1080,1440)],
    ]


def test_quality_table_distinguishes_source_from_downscales():
    rows = module.quality_rows(formats())
    assert rows == [
        {'quality':1440,'kind':'merge'}, {'quality':1080,'kind':'merge'},
        {'quality':720,'kind':'merge'}, {'quality':640,'kind':'render'},
        {'quality':540,'kind':'render'}, {'quality':480,'kind':'render'},
        {'quality':360,'kind':'render'},
    ]
    assert module.source_quality(formats(),480) == (720,True)
    assert module.source_quality(formats(),1440) == (1440,False)
    with pytest.raises(RuntimeError):
        module.source_quality(formats(),2160)


def test_no_generated_upscale_or_fabricated_source():
    source = [{'width':480,'height':854,'ext':'mp4','vcodec':'h264','acodec':'aac'}]
    assert module.quality_rows(source) == [{'quality':480,'kind':'direct'},{'quality':360,'kind':'render'}]
    assert module.quality_rows([{'ext':'mp4','height':None}]) == []
    with pytest.raises(RuntimeError):
        module.source_quality(source,720)


def test_direct_file_selected_when_available():
    source = formats() + [{'format_id':'combined','url':'https://example.com/c','ext':'mp4','width':720,'height':1280,'vcodec':'h264','acodec':'aac'}]
    assert next(row for row in module.quality_rows(source) if row['quality']==720)['kind']=='direct'
    with YoutubeDL({'quiet':True}) as downloader:
        select = downloader.build_format_selector(module.format_selector(720))
        selected = list(select({'formats':source,'incomplete_formats':False}))
    assert selected[0]['format_id'] == 'combined'


@pytest.fixture(params=[(1280,720),(720,1280)])
def source_video(tmp_path, request):
    width,height=request.param
    path=tmp_path/'video.mp4'
    subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i',f'color=c=teal:s={width}x{height}:d=1','-f','lavfi','-i','sine=frequency=440:duration=1','-shortest','-c:v','libx264','-threads','2','-c:a','aac','-pix_fmt','yuv420p',str(path)],check=True,timeout=30)
    return path,width,height


def test_real_downscale_keeps_audio_and_orientation(source_video):
    path,width,height=source_video
    asyncio.run(module.render_video(path,360,path.parent))
    probe=subprocess.run(['ffprobe','-v','error','-show_streams','-of','json',str(path)],capture_output=True,check=True,timeout=10)
    streams=json.loads(probe.stdout)['streams']
    video=next(s for s in streams if s['codec_type']=='video')
    assert (video['width'],video['height']) == ((640,360) if width>height else (360,640))
    assert video['codec_name']=='h264'
    assert any(s['codec_type']=='audio' and s['codec_name']=='aac' for s in streams)
    subprocess.run(['ffmpeg','-v','error','-i',str(path),'-f','null','-'],check=True,timeout=20)


def test_real_upscale_is_rejected(source_video):
    path,_,_=source_video
    original=path.read_bytes()
    with pytest.raises(RuntimeError,match='ไม่ขยายภาพ'):
        asyncio.run(module.render_video(path,1080,path.parent))
    assert path.read_bytes()==original


def test_timed_out_media_process_is_terminated(tmp_path,monkeypatch):
    processes=[]
    real_create=asyncio.create_subprocess_exec
    async def create(*args,**kwargs):
        process=await real_create(*args,**kwargs)
        processes.append(process)
        return process
    monkeypatch.setattr(module.asyncio,'create_subprocess_exec',create)
    with pytest.raises(asyncio.TimeoutError):
        asyncio.run(module.run_media_command([sys.executable,'-c','import time; time.sleep(10)'],tmp_path,0.1))
    assert len(processes)==1 and processes[0].returncode is not None
