import asyncio
from collections import defaultdict, deque
from contextlib import asynccontextmanager
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
from urllib.parse import urlsplit
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from egress import start_proxy

ROOT = Path(__file__).parent
MAX_BYTES = 100 * 1024 * 1024
SLOTS = asyncio.Semaphore(2)
JOBS = {}
RATE = defaultdict(deque)
HOSTS = {'facebook.com', 'www.facebook.com', 'm.facebook.com', 'fb.watch', 'instagram.com', 'www.instagram.com', 'tiktok.com', 'www.tiktok.com', 'vm.tiktok.com', 'vt.tiktok.com'}


def validate_url(url):
    try:
        parsed = urlsplit(url)
        if parsed.scheme != 'https' or parsed.hostname not in HOSTS or parsed.username or parsed.password or parsed.port not in (None, 443):
            raise ValueError()
    except ValueError:
        raise HTTPException(422, 'ใช้ลิงก์ HTTPS จาก Facebook, Instagram หรือ TikTok เท่านั้น')
    return url


@asynccontextmanager
async def lifespan(app):
    app.state.proxy = start_proxy()
    app.state.directory = tempfile.mkdtemp(prefix='reelsave-')
    app.state.tasks = set()
    async def cleanup():
        while True:
            await asyncio.sleep(60)
            now = time.monotonic()
            for key, job in list(JOBS.items()):
                if job['status'] != 'working' and now - job['created'] > 1800:
                    shutil.rmtree(Path(app.state.directory) / key, ignore_errors=True)
                    JOBS.pop(key, None)
            for key in list(RATE):
                if not RATE[key] or now - RATE[key][-1] > 60:
                    RATE.pop(key, None)
    cleaner = asyncio.create_task(cleanup())
    yield
    cleaner.cancel()
    for task in app.state.tasks:
        task.cancel()
    await asyncio.gather(cleaner, *app.state.tasks, return_exceptions=True)
    app.state.proxy.shutdown()
    app.state.proxy.server_close()
    shutil.rmtree(app.state.directory, ignore_errors=True)
    JOBS.clear()


app = FastAPI(lifespan=lifespan)
app.mount('/static', StaticFiles(directory=ROOT / 'static'), name='static')


@app.middleware('http')
async def protections(request: Request, call_next):
    if request.url.path.startswith('/api/'):
        key = request.client.host if request.client else 'unknown'
        now = time.monotonic()
        queue = RATE[key]
        while queue and now - queue[0] > 60:
            queue.popleft()
        if len(queue) >= 90:
            from fastapi.responses import JSONResponse
            return JSONResponse({'detail': 'คำขอมากเกินไป กรุณารอสักครู่'}, status_code=429)
        queue.append(now)
        if not request.headers.get('content-length', '0').isdigit() or int(request.headers.get('content-length', '0')) > 8192:
            from fastapi.responses import JSONResponse
            return JSONResponse({'detail': 'Request too large'}, status_code=413)
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > 8192:
                from fastapi.responses import JSONResponse
                return JSONResponse({'detail': 'Request too large'}, status_code=413)
        request._body = bytes(body)
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Content-Security-Policy'] = "default-src 'self'; img-src 'self' https: data:; style-src 'self'; script-src 'self'; frame-ancestors 'none'; base-uri 'none'"
    return response


class VideoRequest(BaseModel):
    url: str = Field(max_length=2048)
    quality: int = Field(default=720, ge=144, le=1080)
    authorized: bool = False


async def stop_process(process):
    if process.returncode is not None:
        return
    try:
        if os.name == 'nt':
            killer = await asyncio.create_subprocess_exec('taskkill', '/PID', str(process.pid), '/T', '/F', stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
            await killer.wait()
        else:
            import signal
            os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    await process.wait()


async def collect_output(process, directory):
    async def read_limited(stream):
        data = bytearray()
        while chunk := await stream.read(65536):
            data.extend(chunk)
            if len(data) > 8 * 1024 * 1024:
                raise RuntimeError('ข้อมูลจากแพลตฟอร์มมีขนาดใหญ่เกินกำหนด')
        return bytes(data)
    async def disk_guard():
        while True:
            await asyncio.sleep(0.25)
            total = sum(f.stat().st_size for f in Path(directory).rglob('*') if f.is_file())
            if total > MAX_BYTES * 2:
                raise RuntimeError('ไฟล์ชั่วคราวมีขนาดใหญ่เกินกำหนด')
    readers = asyncio.gather(read_limited(process.stdout), read_limited(process.stderr))
    guard = asyncio.create_task(disk_guard())
    try:
        done, _ = await asyncio.wait([readers, guard], return_when=asyncio.FIRST_COMPLETED)
        if guard in done:
            await guard
        output = await readers
        await process.wait()
        return output
    except BaseException:
        await stop_process(process)
        raise
    finally:
        readers.cancel()
        guard.cancel()
        await asyncio.gather(readers, guard, return_exceptions=True)


def downloader_error(stderr):
    """Return a fixed message; never expose raw stderr, URLs, or credentials."""
    text = stderr.decode('utf-8', errors='replace').lower()
    if 'tunnel connection failed: 403' in text or 'connect tunnel failed' in text:
        return 'พร็อกซีปฏิเสธการเชื่อมต่อ (CONNECT 403) กรุณาให้ผู้ดูแลตรวจสอบสิทธิ์เครือข่ายของเซิร์ฟเวอร์ ยังตรวจสอบสถานะวิดีโอไม่ได้'
    if 'ffmpeg is not installed' in text or 'ffprobe and ffmpeg not found' in text:
        return 'เซิร์ฟเวอร์ไม่พบ FFmpeg กรุณาให้ผู้ดูแลติดตั้งและตรวจสอบ PATH'
    if 'requested format is not available' in text:
        return 'วิดีโอนี้ไม่มีรูปแบบ MP4 ในคุณภาพที่เลือก กรุณาเลือกคุณภาพอื่น'
    if 'sign in' in text or 'login required' in text or 'log in' in text:
        return 'แพลตฟอร์มต้องการการเข้าสู่ระบบ จึงดาวน์โหลดผ่านบริการนี้ไม่ได้'
    return 'ไม่สามารถเข้าถึงวิดีโอได้ ลิงก์อาจไม่เป็นสาธารณะ แพลตฟอร์มจำกัดการเข้าถึง หรือเครือข่ายไม่อนุญาต'


async def run_ytdlp(url, extra, directory, timeout=180):
    proxy = f'http://127.0.0.1:{app.state.proxy.server_address[1]}'
    args = [sys.executable, '-m', 'yt_dlp', '--ignore-config', '--no-playlist', '--no-cache-dir', '--proxy', proxy,
            '--socket-timeout', '15', '--retries', '1', '--extractor-retries', '1', '--max-filesize', str(MAX_BYTES),
            '--no-warnings', '--no-progress', '--compat-options', 'no-certifi', *extra, '--', validate_url(url)]
    # Only the yt-dlp process fetches remote media. FFmpeg merges local files.
    process = await asyncio.create_subprocess_exec(*args, cwd=directory, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, start_new_session=os.name != 'nt')
    try:
        output, error = await asyncio.wait_for(collect_output(process, directory), timeout)
    except (asyncio.TimeoutError, asyncio.CancelledError):
        await stop_process(process)
        raise
    if process.returncode:
        raise RuntimeError(downloader_error(error))
    return output


@app.get('/')
async def home():
    return FileResponse(ROOT / 'static/index.html')


@app.post('/api/inspect')
async def inspect(body: VideoRequest):
    validate_url(body.url)
    if SLOTS.locked():
        raise HTTPException(429, 'ระบบกำลังทำงาน กรุณาลองอีกครั้ง')
    async with SLOTS:
        try:
            raw = await run_ytdlp(body.url, ['--dump-single-json', '--skip-download'], app.state.directory, 60)
            info = json.loads(raw)
            formats = info.get('formats') or []
            heights = quality_options(formats)
            thumbnail = info.get('thumbnail') or ''
            if not thumbnail.startswith('https://'):
                thumbnail = ''
            return {'title': info.get('title', 'Reel'), 'thumbnail': thumbnail, 'duration': info.get('duration'), 'qualities': heights}
        except (RuntimeError, asyncio.TimeoutError, ValueError) as exc:
            raise HTTPException(502, str(exc) or 'ตรวจสอบวิดีโอหมดเวลา')


def quality_options(formats):
    qualities = set()
    for fmt in formats:
        if fmt.get('ext') != 'mp4' or fmt.get('vcodec') == 'none':
            continue
        dimensions = [fmt.get(key) for key in ('width', 'height')]
        dimensions = [value for value in dimensions if isinstance(value, int) and value > 0]
        if dimensions and 144 <= min(dimensions) <= 1080:
            qualities.add(min(dimensions))
    return sorted(qualities)


def format_selector(quality):
    # Portrait 720p is commonly 720x1280: match either side, not height alone.
    video = f'(bv[height<={quality}][ext=mp4]/bv[width<={quality}][ext=mp4])'
    combined = f'b[height<={quality}][ext=mp4]/b[width<={quality}][ext=mp4]'
    return f'{video}+ba[ext=m4a]/{combined}'


def ensure_media_tools():
    missing = [name for name in ('ffmpeg', 'ffprobe') if not shutil.which(name)]
    if missing:
        raise RuntimeError('เซิร์ฟเวอร์ยังไม่พร้อมรวมวิดีโอและเสียง: ไม่พบ ' + ', '.join(missing) + ' กรุณาให้ผู้ดูแลติดตั้ง FFmpeg บนเครื่องที่รันเว็บ')


def completed_video(directory, output):
    video = directory / 'video.mp4'
    text = output.decode('utf-8', errors='replace').lower()
    if video.is_file():
        if video.stat().st_size > MAX_BYTES:
            raise RuntimeError('ไฟล์วิดีโอมีขนาดเกิน 100 MB')
        if video.stat().st_size == 0:
            raise RuntimeError('ไฟล์วิดีโอว่างเปล่า กรุณาลองใหม่')
        return video
    if 'max-filesize' in text or ('larger than' in text and 'filesize' in text):
        raise RuntimeError('ไฟล์วิดีโอมีขนาดเกิน 100 MB')
    if 'does not pass filter' in text:
        raise RuntimeError('วิดีโอถูกข้าม: รองรับเฉพาะวิดีโอไม่สดที่ระบุความยาวได้และยาวไม่เกิน 10 นาที')
    if any(directory.glob('video.f*')):
        raise RuntimeError('ดาวน์โหลดภาพหรือเสียงแล้ว แต่ยังรวมเป็น MP4 ไม่สำเร็จ กรุณาให้ผู้ดูแลตรวจสอบ FFmpeg')
    raise RuntimeError('ดาวน์โหลดจบแต่ไม่พบไฟล์ MP4 กรุณาลองใหม่หรือให้ผู้ดูแลตรวจสอบขั้นตอนดาวน์โหลด')


async def download(key, body):
    job = JOBS[key]
    directory = Path(app.state.directory) / key
    directory.mkdir()
    try:
        ensure_media_tools()
        async with SLOTS:
            output = await run_ytdlp(body.url, ['-f', format_selector(body.quality),
                '--merge-output-format', 'mp4', '--downloader', 'native', '--hls-prefer-native',
                '--match-filter', 'duration <= 600 & !is_live', '-o', str(directory / 'video.%(ext)s')], directory)
        completed_video(directory, output)
        job['status'] = 'ready'
    except Exception as exc:
        job.update(status='error', error=str(exc) or 'ดาวน์โหลดหมดเวลา กรุณาลองอีกครั้ง')
        shutil.rmtree(directory, ignore_errors=True)


@app.post('/api/download', status_code=202)
async def begin(body: VideoRequest):
    validate_url(body.url)
    if not body.authorized:
        raise HTTPException(422, 'กรุณายืนยันสิทธิ์ในการดาวน์โหลด')
    try:
        ensure_media_tools()
    except RuntimeError as exc:
        raise HTTPException(503, str(exc))
    if sum(j['status'] == 'working' for j in JOBS.values()) >= 2:
        raise HTTPException(429, 'คิวเต็ม กรุณาลองอีกครั้ง')
    key = uuid.uuid4().hex
    JOBS[key] = {'status': 'working', 'created': time.monotonic()}
    task = asyncio.create_task(download(key, body))
    app.state.tasks.add(task)
    task.add_done_callback(app.state.tasks.discard)
    return {'id': key}


@app.get('/api/jobs/{key}')
async def status(key: str):
    if key not in JOBS:
        raise HTTPException(404, 'ไม่พบรายการ หรือไฟล์หมดอายุแล้ว')
    job = JOBS[key]
    return {'status': job['status'], 'error': job.get('error')}


@app.get('/api/files/{key}')
async def file(key: str):
    if key not in JOBS or JOBS[key]['status'] != 'ready':
        raise HTTPException(404, 'ไม่พบไฟล์')
    return FileResponse(Path(app.state.directory) / key / 'video.mp4', filename='reelsave.mp4', media_type='video/mp4')
