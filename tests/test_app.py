import json
import socket
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
import app as module
from egress import public_addresses


@pytest.fixture
def client():
    module.RATE.clear()
    with TestClient(module.app) as client:
        yield client


@pytest.mark.parametrize('url', ['http://facebook.com/reel/1', 'https://localhost/x', 'https://127.0.0.1/', 'https://facebook.com.evil.test/', 'https://user@facebook.com/', 'https://facebook.com:8443/', 'file:///etc/passwd'])
def test_invalid_urls(url):
    with pytest.raises(HTTPException):
        module.validate_url(url)


@pytest.mark.parametrize('address', ['127.0.0.1', '10.0.0.1', '169.254.169.254', '::1', '100.64.0.1'])
def test_private_destinations_blocked(monkeypatch, address):
    monkeypatch.setattr(socket, 'getaddrinfo', lambda *a, **kw: [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (address, 443))])
    with pytest.raises(ValueError):
        public_addresses('redirect.example', 443)


def test_proxy_blocks_actual_connect(client):
    with socket.create_connection(module.app.state.proxy.server_address) as connection:
        connection.sendall(b'CONNECT 127.0.0.1:443 HTTP/1.1\r\n\r\n')
        assert b'403 Forbidden' in connection.recv(1024)


def test_home_and_validation(client):
    response = client.get('/')
    assert response.status_code == 200
    assert 'ReelSave' in response.text
    assert 'frame-ancestors' in response.headers['content-security-policy']
    assert client.post('/api/inspect', json={'url':'https://localhost/'}).status_code == 422
    assert client.post('/api/download', json={'url':'https://www.facebook.com/reel/1'}).status_code == 422
    assert client.get('/api/files/unknown').status_code == 404


def test_inspect(client, monkeypatch):
    runner = AsyncMock(return_value=json.dumps({'title':'My Reel', 'duration':12, 'thumbnail':'https://example.com/image.jpg', 'formats':[{'height':720, 'ext':'mp4'}, {'height':1080, 'ext':'mp4'}, {'height':2160, 'ext':'mp4'}]}).encode())
    monkeypatch.setattr(module, 'run_ytdlp', runner)
    data = client.post('/api/inspect', json={'url':'https://www.facebook.com/reel/1'}).json()
    assert data['title'] == 'My Reel'
    assert data['qualities'] == [720, 1080]


def test_download_pipeline(client, monkeypatch):
    async def fake_download(url, extra, directory, timeout=180):
        (directory / 'video.mp4').write_bytes(b'test fixture')
        return b''
    monkeypatch.setattr(module, 'run_ytdlp', fake_download)
    response = client.post('/api/download', json={'url':'https://www.facebook.com/reel/1', 'authorized':True})
    assert response.status_code == 202
    key = response.json()['id']
    import time
    for _ in range(50):
        status = client.get('/api/jobs/' + key).json()['status']
        if status != 'working':
            break
        time.sleep(0.01)
    assert status == 'ready'
    response = client.get('/api/files/' + key)
    assert response.content == b'test fixture'
    assert response.headers['content-type'] == 'video/mp4'


def test_platform_error(client, monkeypatch):
    monkeypatch.setattr(module, 'run_ytdlp', AsyncMock(side_effect=RuntimeError('Platform restricted')))
    response = client.post('/api/inspect', json={'url':'https://www.instagram.com/reel/1'})
    assert response.status_code == 502
    assert response.json()['detail'] == 'Platform restricted'


def test_rate_limit(client):
    for _ in range(90):
        assert client.get('/api/jobs/unknown').status_code == 404
    assert client.get('/api/jobs/unknown').status_code == 429


def test_chunked_body_limit(client):
    def chunks():
        yield b'{"url":"'
        yield b'x' * 9000
        yield b'"}'
    assert client.post('/api/inspect', content=chunks(), headers={'Content-Type':'application/json'}).status_code == 413


@pytest.mark.parametrize(('stderr', 'expected'), [
    (b'ERROR: Tunnel connection failed: 403 Forbidden https://user:secret@example.com/', 'CONNECT 403'),
    (b'ERROR: ffmpeg is not installed', 'FFmpeg'),
    (b'ERROR: Requested format is not available', 'MP4'),
    (b'ERROR: Login required', 'เข้าสู่ระบบ'),
    (b'Unexpected provider response secret', 'ไม่สามารถเข้าถึงวิดีโอได้'),
])
def test_downloader_errors_are_actionable_and_sanitized(stderr, expected):
    message = module.downloader_error(stderr)
    assert expected in message
    assert 'secret' not in message
    assert 'example.com' not in message


def test_proxy_denial_from_real_runner_reaches_api(client, monkeypatch):
    class FailedProcess:
        returncode = 1
    async def collected(*args):
        return b'', b'ERROR: Tunnel connection failed: 403 Forbidden'
    monkeypatch.setattr(module.asyncio, 'create_subprocess_exec', AsyncMock(return_value=FailedProcess()))
    monkeypatch.setattr(module, 'collect_output', collected)
    response = client.post('/api/inspect', json={'url': 'https://www.facebook.com/reel/3922253057922307'})
    assert response.status_code == 502
    assert 'CONNECT 403' in response.json()['detail']


def test_portrait_quality_uses_short_edge():
    assert module.quality_options([
        {'width':720, 'height':1280, 'ext':'mp4', 'vcodec':'av1'},
        {'width':1080, 'height':1920, 'ext':'mp4', 'vcodec':'av1'},
        {'width':1440, 'height':2560, 'ext':'mp4', 'vcodec':'av1'},
        {'height':None, 'ext':'mp4'},
        {'width':720, 'height':1280, 'ext':'webm'},
    ]) == [720,1080]


def test_selector_picks_portrait_and_audio():
    from yt_dlp import YoutubeDL
    formats = [
        {'format_id':'audio', 'url':'https://example.com/a', 'ext':'m4a', 'vcodec':'none', 'acodec':'aac'},
        {'format_id':'720', 'url':'https://example.com/v', 'ext':'mp4', 'width':720, 'height':1280, 'vcodec':'av1', 'acodec':'none'},
        {'format_id':'1080', 'url':'https://example.com/h', 'ext':'mp4', 'width':1080, 'height':1920, 'vcodec':'av1', 'acodec':'none'},
    ]
    with YoutubeDL({'quiet':True}) as downloader:
        selector = downloader.build_format_selector(module.format_selector(720))
        selected = list(selector({'formats':formats, 'incomplete_formats':False}))
    assert len(selected) == 1
    assert selected[0]['format_id'] == '720+audio'


def test_runner_keeps_tls_verification_and_uses_system_trust(client, monkeypatch):
    class Success:
        returncode = 0
    create = AsyncMock(return_value=Success())
    monkeypatch.setattr(module.asyncio, 'create_subprocess_exec', create)
    monkeypatch.setattr(module, 'collect_output', AsyncMock(return_value=(b'{"title":"Trust","formats":[]}', b'')))
    response = client.post('/api/inspect', json={'url':'https://www.facebook.com/reel/1'})
    assert response.status_code == 200
    args = create.call_args.args
    assert '--no-check-certificates' not in args
    index = args.index('--compat-options')
    assert args[index + 1] == 'no-certifi'
