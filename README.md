# ReelSave V2

เว็บภาษาไทยสำหรับตรวจสอบและดาวน์โหลดวิดีโอที่ผู้ใช้มีสิทธิ์บันทึก ใช้ FastAPI, yt-dlp และ FFmpeg พร้อม UI แบบ responsive ที่ออกแบบใหม่สำหรับ ReelSave

## เปิดจาก GitHub ด้วย VS Code บน Windows

1. ติดตั้ง Git for Windows หากยังไม่มี แล้วเปิด VS Code ใหม่
2. กด Ctrl+Shift+P → Git: Clone → วาง `https://github.com/Arizeth/reelsave.git`
3. เลือกโฟลเดอร์แม่ที่จะเก็บโปรเจกต์ เช่น `E:\Reel` แล้วกด Open เมื่อ clone เสร็จ ถ้ามีโฟลเดอร์ reelsave เดิมอยู่แล้ว ให้เลือกโฟลเดอร์แม่อื่นเพื่อเก็บงานเดิมไว้
4. หาก GitHub ขอเข้าสู่ระบบ ให้ลงชื่อเข้าใช้บัญชีที่มีสิทธิ์เข้าถึง repository ผ่านเบราว์เซอร์ ไม่ใส่ token ลงในไฟล์
5. เปิด Terminal ใน VS Code แล้วรัน `.\START-WINDOWS.cmd` ตัวเปิดจะติดตั้ง dependencies และเปิดเว็บอัตโนมัติ
6. หากต้องการใช้ F5 ให้ติดตั้ง Python extension ตามที่ VS Code แนะนำ เลือก Python 3.12 ผ่าน Python: Select Interpreter แล้วเลือก `ReelSave: Windows local web` ใน Run and Debug

รับอัปเดตครั้งต่อไปผ่าน Source Control → Pull หรือ `git pull --ff-only` หลังเก็บการแก้ไขของตัวเองเรียบร้อยแล้ว โค้ดรันบน Windows ของคุณ ไม่ใช่บน GitHub และไม่จำเป็นต้องใช้ GitHub Pages

## รันใน GitHub Codespaces (Linux)

FFmpeg ที่ติดตั้งไว้บน Windows ไม่ได้ติดตั้งเข้า Codespaces ด้วย ต้องติดตั้งใน Terminal ของ Codespaces:

```bash
sudo apt-get update
sudo apt-get install -y ffmpeg
ffmpeg -version
ffprobe -version
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m uvicorn app:app --host 0.0.0.0 --port 8000 --no-proxy-headers
```

เปิดแท็บ Ports → พอร์ต 8000 → Open in Browser โดยเก็บ visibility เป็น Private ระหว่างทดสอบ เปิด Terminal ค้างไว้ เมื่ออัปเดตโค้ดให้กด Ctrl+C แล้ว `git pull --ff-only` และเริ่ม uvicorn ใหม่อีกครั้ง

หาก preview สำเร็จแต่ดาวน์โหลดล้มเหลว ให้ดูข้อความใหม่บนเว็บ: ระบบจะตรวจ ffmpeg/ffprobe ก่อนรับงาน และแยกกรณีไฟล์เกินขนาด, วิดีโอถูกข้ามตามนโยบาย, หรือภาพ/เสียงยังไม่ได้รวม แทนข้อความรวมสาเหตุเดิม จำลองแล้วว่า yt-dlp อาจคืน exit 0 เมื่อไม่มี FFmpeg แต่ทิ้งไฟล์ .f*.mp4 และ .m4a แยกกัน จึงไม่ใช้ exit code อย่างเดียวตัดสินว่าดาวน์โหลดสำเร็จ

## เปิดตัวอย่างบน Windows แบบดับเบิลคลิก

แตก ReelSave-V2-Windows.zip ลงโฟลเดอร์ใหม่เพื่อไม่ทับโปรเจกต์เดิม แล้วดับเบิลคลิก `START-WINDOWS.cmd` ตัวเปิดจะสร้าง .venv ของ Windows, ติดตั้ง requirements และเปิดเบราว์เซอร์เมื่อเซิร์ฟเวอร์พร้อม ต้องมี Python 3.12 ผ่านคำสั่ง py และ FFmpeg/ffprobe บน PATH ใช้อินเทอร์เน็ตในการติดตั้งครั้งแรก เปิดหน้าต่างคำสั่งค้างไว้ขณะใช้งาน กด Ctrl+C เพื่อหยุด

ไฟล์เปิดใช้งาน Windows ผ่านการตรวจ syntax บนคลาวด์ แต่ยังไม่ได้รันบน Windows จริง หาก Windows ไม่แสดงนามสกุลไฟล์ ให้มองหา START-WINDOWS ที่ชนิดไฟล์เป็น Windows Command Script

## เริ่มใช้งานบน Windows (PowerShell)

ติดตั้ง Python 3.12 และ FFmpeg / ffprobe ให้เรียกได้จาก PATH จากนั้นเปิด PowerShell ในโฟลเดอร์โปรเจกต์:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
ffmpeg -version
.\.venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8000 --no-proxy-headers
```

เปิดเบราว์เซอร์ที่ `http://127.0.0.1:8000` ใช้ Python ของ virtualenv เดียวกันทั้งเว็บและ yt-dlp เพื่อหลีกเลี่ยงปัญหา PATH / เวอร์ชันไม่ตรงกัน โดย backend เรียก `sys.executable -m yt_dlp` ผ่าน subprocess แบบไม่มี shell

## Linux / คลาวด์

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 8000 --no-proxy-headers
```

ต้องมี ffmpeg และ ffprobe ใน PATH รันด้วย **worker เดียว** เนื่องจากคิวและ rate limit อยู่ในหน่วยความจำ ไม่มีฐานข้อมูลหรือ credential ที่ต้องตั้งค่า

## ทดสอบ

```sh
.venv/bin/python -m pytest -q
```

Windows เปลี่ยนเป็น `.\.venv\Scripts\python.exe -m pytest -q` ชุดทดสอบตรวจ URL, private IP, proxy CONNECT, API preview, job/file flow, error, rate limit และการรวมเสียง/ภาพด้วย yt-dlp + FFmpeg จริง การทดสอบ API extraction/download ใช้ mock ไม่ใช่หลักฐานว่าดาวน์โหลดจาก Meta หรือ TikTok สำเร็จ

## Docker / เตรียม production

```sh
docker compose up --build -d
docker compose logs -f
```

Compose ผูกพอร์ตเฉพาะ loopback ใช้ non-root, read-only filesystem, tmpfs 512 MB, memory 768 MB, 2 CPU, PID limit และตัด capabilities ก่อนเปิดสาธารณะให้เพิ่ม reverse proxy HTTPS, จำกัด request body 8 KB และ timeout ให้รองรับงาน 180 วินาที ตรวจจำนวน connection และ rate limit ที่ edge ด้วย อย่าเปิดพอร์ต backend สู่ Internet โดยตรง ค่า rate limit ปัจจุบันอ่าน IP ของ socket จึงรวมผู้ใช้ทั้งหมดหลัง reverse proxy; หากต้องใช้ forwarded IP ต้องกำหนด trusted proxy ที่เจาะจงและปรับ middleware พร้อมทดสอบก่อน

สำหรับหลาย instance ต้องย้าย jobs/rate limits/queue ไป shared storage เพิ่ม authentication หรือ abuse controls, observability, global storage quotas และตรวจ dependency/security updates ให้เป็นขั้นตอนก่อน production ระบบนี้ยังเป็น local MVP

## ข้อจำกัดและการรักษาความปลอดภัย

- รับเฉพาะ HTTPS จาก hostname Facebook, Instagram, TikTok ที่ระบุใน backend ไม่รับ URL ใดก็ได้
- yt-dlp ใช้ HTTPS CONNECT proxy ภายใน จำกัดทุกปลายทางรวมถึง redirect เป็นโดเมนแพลตฟอร์ม/CDN ใน TRUSTED_DOMAINS ตรวจ DNS ทุก address และปฏิเสธ private, loopback, reserved IP และพอร์ตอื่นนอกจาก 443
- เมื่อไม่มี HTTPS_PROXY จะเชื่อมต่อ IP ที่ตรวจแล้วโดยตรง เมื่อมี HTTPS_PROXY จะส่ง CONNECT ผ่าน upstream ที่ระบบจัดเตรียมไว้โดยใช้ hostname เดิม หลังตรวจ allowlist/DNS แล้ว **โหมด upstream ไม่สามารถ pin IP ที่ upstream resolve ได้** จึงต้องใช้ trusted proxy ที่บังคับปฏิเสธ private/reserved destinations ณ จุดเชื่อมต่อจริงก่อนเปิด production การตรวจ DNS ฝั่งแอปเพียงอย่างเดียวไม่รับประกันป้องกัน DNS rebinding ที่ upstream
- ใช้ `--compat-options no-certifi` เพื่อใช้ system certificate trust รวมถึง SSL_CERT_FILE ที่คลาวด์จัดเตรียมไว้ ยังคงตรวจ TLS และ hostname ไม่ใช้ `--no-check-certificates` อย่าตั้ง SSL_CERT_FILE เป็นไฟล์ที่ไม่ได้รับความเชื่อถือ
- ใช้ native media downloader; FFmpeg ใช้ merge ไฟล์ในเครื่อง ไม่รับ remote URL จากผู้ใช้โดยตรง ไม่ใช้ cookies/login หรือข้าม DRM
- จำกัดงานดาวน์โหลด 2 งาน, extraction timeout 60 วินาที, download timeout 180 วินาที และการย่อขนาด timeout 120 วินาที, คุณภาพสูงสุด 1440p โดยอิงด้านสั้น (เช่น 720×1280 คือ 720p), วิดีโอไม่เกิน 10 นาที, ไฟล์ผลลัพธ์ไม่เกิน 100 MB และตรวจ temporary disk usage ระหว่างทำงาน เกณฑ์ขนาดเป็นการตรวจแบบ polling อาจเกินชั่วขณะได้; hard storage/CPU/memory limits อยู่ใน Compose
- ไฟล์และสถานะงานลบเมื่อครบประมาณ 30 นาที; ปิดโปรแกรมลบ temp directory ปัจจุบัน งานไม่คงอยู่หลัง restart หากถูก kill แบบฉับพลันให้ลบโฟลเดอร์ `reelsave-*` ใน system temp ที่ไม่มี instance ใช้งานอยู่
- ลิงก์ไฟล์ใช้ random job ID แบบ bearer; อย่าแชร์ ID กับบุคคลอื่น ไม่มีบัญชีผู้ใช้หรือ ACL แยกผู้ใช้
- รูป thumbnail โหลดจาก HTTPS ต้นทางในเบราว์เซอร์ ซึ่งต้นทางอาจเห็น IP ของผู้ใช้ ชื่อวิดีโอแสดงผ่าน textContent ไม่แทรก HTML
- ความคืบหน้าแสดงเป็นขั้นตอน ไม่ใช่เปอร์เซ็นต์จริง MP4 บางคุณภาพอาจไม่มี และแพลตฟอร์มอาจบล็อก IP, ต้อง login หรือจำกัดภูมิภาค ระบบจะแจ้งข้อผิดพลาด ไม่พยายามข้ามข้อจำกัด
- yt-dlp ถูก pin เพื่อทำซ้ำได้ แต่ extractor ของแพลตฟอร์มเปลี่ยนได้ ควรอัปเดตอย่างตั้งใจแล้วทดสอบซ้ำ
- Environment ที่จำกัด egress ต้องอนุญาตโดเมนแพลตฟอร์มและ media CDN ที่ใช้งานจริงผ่าน settings ไม่ควรเปิด wildcard ทั้ง Internet เพื่อแก้ปัญหาอย่างเดียว

## สถานะการตรวจสอบล่าสุด

เริ่มจาก repository ว่าง จึงไม่มีโค้ด Windows เดิมให้วิเคราะห์ แต่ตรวจและแก้ปัญหาใน MVP นี้ได้ดังนี้:

1. Network proxy เดิมไม่อนุญาต Facebook หลังผู้ใช้บันทึกและ Publish แล้วหน้า Facebook ตอบ HTTP 200
2. yt-dlp ใช้ certifi ซึ่งไม่รวม trusted CA ของ proxy ในคลาวด์ แก้โดยใช้ system trust ผ่าน no-certifi โดยไม่ปิด TLS verification
3. Proxy ภายในแอปเชื่อมต่อโดยตรง ซึ่งไม่เหมาะกับ managed egress แก้ให้รองรับ HTTPS_PROXY โดยคงการจำกัด hostname และตรวจ public DNS พร้อมข้อจำกัดด้าน upstream IP pinning ที่ระบุไว้ข้างต้น
4. ตัวเลือกคุณภาพเดิมกรอง height <= 720 ทำให้เลือก Reel แนวตั้ง 720×1280 ไม่ได้ แก้ preview ให้อิงด้านสั้นและ selector ให้เลือกได้ทั้งแนวนอน/แนวตั้ง ไม่สร้างคุณภาพสมมุติเมื่อ metadata ไม่มี dimensions

ผลทดสอบจริงกับ Facebook Reel 3922253057922307 ที่ผู้ใช้ส่งเพื่อทดสอบ:

- POST /api/inspect: HTTP 200, thumbnail พร้อม, ความยาว 16.044 วินาที, คุณภาพ 720p และ 1080p
- POST /api/download ที่ 720p → polling job → GET /api/files: สำเร็จ HTTP 200, video/mp4, 5,430,554 bytes
- ffprobe: ภาพ AV1 720×1280, เสียง AAC, ความยาวรวม 16.047007 วินาที
- FFmpeg ถอดรหัสภาพและเสียงตลอดไฟล์ผ่าน ไม่มีข้อผิดพลาด (เป็นการตรวจทางเทคนิค ยังไม่ได้ฟัง/ดูด้วยคน)
- AV1 ใน MP4 อาจไม่เล่นในเบราว์เซอร์/มือถือรุ่นเก่า ยังไม่มีการ transcode เป็น H.264
- ชุด pytest ล่าสุด 59 tests ครอบคลุม API/security, upstream CONNECT, ตัวเลือกฟอร์แมตแนวตั้งด้วย yt-dlp และ FFmpeg merge จริง มี Starlette TestClient deprecation warning 1 รายการ
- JavaScript syntax และ Compose config ผ่าน Docker image build ครั้งก่อนติด DNS deb.debian.org ภายใน Docker ยังไม่ได้ทดสอบ container runtime หลัง Publish
- Instagram, TikTok, Windows runtime, มือถือจริง และ Facebook 1080p ยังไม่ได้ทดสอบ; ตรวจหน้าเว็บด้วย Chromium ที่ viewport desktop/mobile แล้ว

## เลือกหลายความละเอียด

หน้า preview แสดงตารางพร้อมปุ่มต่อความละเอียด โดยอ่านคุณภาพต้นทางจริง ไม่แสดงว่าดาวน์โหลดความคมชัดที่ไม่มีอยู่ได้:

- **ไฟล์ต้นทางพร้อมเสียง**: ใช้ MP4 ที่มีทั้งภาพและเสียงอยู่แล้ว
- **ต้นทาง · รวมภาพและเสียง**: ดาวน์โหลดภาพและเสียงแยกกันแล้วรวมโดยไม่ encode ภาพใหม่
- **ย่อขนาด · ใช้เวลาประมวลผล**: เมื่อไม่มีขนาดที่เลือก ระบบเลือกต้นทางที่เล็กที่สุดซึ่งยังใหญ่กว่าเป้าหมาย แล้วย่อด้วย FFmpeg เป็น H.264/AAC ไม่ upscale

คุณภาพต้นทางรองรับถึง 1440p ตัวเลือกย่อขนาดคือ 360p, 480p, 540p, 640p, 720p และ 1080p เมื่อมีต้นทางใหญ่พอ ความละเอียดอิงด้านสั้นสำหรับแนวตั้ง เช่น 720×1280 คือ 720p ไม่ใช่ 1280p ไม่มี MP3 ในเวอร์ชันนี้

ทุกงานตรวจ metadata/ระยะเวลา/คุณภาพที่เลือกใหม่ก่อนดาวน์โหลด ไม่เชื่อข้อมูลความละเอียดที่ส่งมาจากเบราว์เซอร์ งานย่อขนาดใช้ CPU เพิ่มขึ้น จำกัด FFmpeg เป็น 2 threads และ filter 1 thread ใช้ slot เดียวกับงานดาวน์โหลดตลอดกระบวนการ รองรับสูงสุดสองงานพร้อมกัน ตรวจขนาดไฟล์ 100 MB และ temporary disk ระหว่างประมวลผล FFmpeg/ffprobe ที่อ่านไฟล์ในเครื่องจำกัด protocol เป็น file,pipe ไม่รับ remote URL งานย่อจำกัดภาพต้นทางไม่เกิน 3840 ต่อด้านและจำนวนพิกเซลไม่เกิน 1440×2560 หากหมดเวลาให้เลือกคุณภาพต้นทางแทน

ผลทดสอบรอบเพิ่มหลายความละเอียดกับ Reel เดิมผ่าน API จริง:

| ตัวเลือก | ขนาดภาพที่ได้ | Codec ภาพ / เสียง | ขนาดไฟล์ | ผลตรวจ |
| --- | --- | --- | --- | --- |
| 1440p ต้นทาง | 1440×2560 | AV1 / AAC | 8,157,611 bytes | ffprobe และถอดรหัสเต็มไฟล์ผ่าน |
| 480p ย่อขนาด | 480×854 | H.264 / AAC | 3,103,658 bytes | ffprobe และถอดรหัสเต็มไฟล์ผ่าน |

ตรวจ UI ด้วย Playwright/Chromium: ตาราง 7 แถว, ส่งคุณภาพที่เลือกถูกต้อง, แสดงขั้นตอนย่อขนาด, ไม่มีช่องติ๊กหรือปุ่มบันทึกซ้ำ และเริ่มดาวน์โหลดไฟล์อัตโนมัติหลังงานพร้อม ตรวจ viewport 320px/390px ไม่มีหน้าเว็บล้นแนวนอน และไม่มี JavaScript error ชุด pytest ล่าสุดผ่าน 59 tests รวม FFmpeg ย่อแนวตั้ง/แนวนอนจริง ป้องกัน upscale, validation และการหยุด subprocess เมื่อ timeout

ขั้นตอนถัดไป: ทดสอบบนมือถือจริงและใช้ลิงก์ Instagram/TikTok ที่ผู้ใช้มีสิทธิ์ดาวน์โหลด ก่อน production ต้องตรวจ trusted upstream egress และข้อจำกัดระบบในหัวข้อด้านบน

## หน้าตาและการดาวน์โหลดเวอร์ชันพาสเทล

ปรับ CI เป็นพื้นอ่อน โทนครีม/เขียวเซจ/ลาเวนเดอร์ ไม่มีแสงนีออน หัวข้อใช้ “ดาวน์โหลดวิดีโอและเพลงออนไลน์ฟรี” ตามที่ร้องขอ แต่ฟังก์ชันยังเป็น MP4 เท่านั้น และระบุใน FAQ ว่ายังไม่มี MP3

เอาช่องติ๊กออกจาก UI ผู้ใช้กดดาวน์โหลดตามความละเอียดเพียงครั้งเดียว ระบบเตรียม/ย่อไฟล์แล้วส่งไฟล์ attachment ให้เบราว์เซอร์อัตโนมัติ ไม่มีปุ่มบันทึกอีกขั้น ระหว่างทำงานปิดปุ่มเพื่อป้องกันงานซ้ำ ข้อความและแนวทางการใช้เฉพาะเนื้อหาที่มีสิทธิ์ยังอยู่บนหน้าเว็บ API เดิมยังรับ authorized:true จากการกดดาวน์โหลด โดยไม่ได้เพิ่มระบบบัญชีหรือสิทธิ์เข้าถึงใหม่

ทดสอบผ่าน Chromium กับ Facebook Reel ที่ผู้ใช้ส่งจริง: คลิก 720p ครั้งเดียว ได้ไฟล์ reelsave-720p.mp4 ขนาด 5,430,554 bytes โดยอัตโนมัติ ffprobe ยืนยันภาพ 720×1280 และมีเสียง การตั้งค่าเบราว์เซอร์ของผู้ใช้อาจยังแสดงหน้าต่างเลือกตำแหน่งบันทึกตามปกติ
