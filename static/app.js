const $ = id => document.getElementById(id);
let inspectedURL = '';
let busy = false;
$('thumbnail').addEventListener('error', () => { $('thumbnail').hidden = true; });
function message(text) { $('message').textContent = text; }
function setBusy(value) {
  busy = value;
  $('inspect').disabled = value;
  document.querySelectorAll('.quality-download').forEach(button => { button.disabled = value; });
}
async function api(path, body) {
  const response = await fetch(path, body ? {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)} : {});
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'ข้อมูลไม่ถูกต้อง กรุณาตรวจสอบลิงก์');
  return data;
}
function showQualities(options) {
  $('qualities').replaceChildren();
  const labels = {direct:'ไฟล์ต้นทางพร้อมเสียง', merge:'ต้นทาง · รวมภาพและเสียง', render:'ย่อขนาด · ใช้เวลาประมวลผล'};
  for (const option of options) {
    const row = document.createElement('tr');
    const quality = document.createElement('th');
    quality.scope = 'row';
    quality.textContent = `${option.quality}p`;
    const preparation = document.createElement('td');
    const badge = document.createElement('span');
    badge.className = option.kind === 'render' ? 'quality-tag render' : 'quality-tag';
    badge.textContent = labels[option.kind] || labels.merge;
    preparation.append(badge);
    const action = document.createElement('td');
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'quality-download';
    button.textContent = option.kind === 'render' ? 'สร้าง MP4 ↓' : 'ดาวน์โหลด ↓';
    button.setAttribute('aria-label', `${button.textContent} ${option.quality}p`);
    button.dataset.quality = option.quality;
    button.addEventListener('click', () => download(option));
    action.append(button);
    row.append(quality, preparation, action);
    $('qualities').append(row);
  }
}
$('form').addEventListener('submit', async event => {
  event.preventDefault();
  if (busy) return;
  setBusy(true);
  $('preview').hidden = $('actions').hidden = $('file').hidden = true;
  $('authorized').checked = false;
  inspectedURL = '';
  message('กำลังตรวจสอบวิดีโอ…');
  const url = $('url').value.trim();
  try {
    const data = await api('/api/inspect', {url});
    if (!data.options?.length) throw new Error('ไม่พบคุณภาพ MP4 ที่ระบุขนาดได้และระบบรองรับ');
    inspectedURL = url;
    $('title').textContent = data.title;
    $('duration').textContent = data.duration ? `ความยาว ${Math.round(data.duration)} วินาที` : 'ไม่ทราบความยาว';
    $('thumbnail').hidden = !data.thumbnail;
    if (data.thumbnail) $('thumbnail').src = data.thumbnail;
    showQualities(data.options);
    $('preview').hidden = $('actions').hidden = false;
    message('ตรวจสอบแล้ว ยืนยันสิทธิ์และเลือกความละเอียดจากตารางได้เลย');
  } catch (error) { message(error.message); }
  finally { setBusy(false); }
});
async function download(option) {
  if (busy) return;
  if (!$('authorized').checked) return message('กรุณายืนยันว่าคุณมีสิทธิ์ดาวน์โหลดเนื้อหานี้');
  setBusy(true);
  $('file').hidden = true;
  try {
    const {id} = await api('/api/download', {url:inspectedURL, quality:option.quality, authorized:true});
    message('กำลังตรวจสอบคุณภาพวิดีโอ…');
    const stages = {inspecting:'กำลังตรวจสอบคุณภาพวิดีโอ…', downloading:'กำลังดาวน์โหลดและรวมภาพกับเสียง…', rendering:`กำลังย่อวิดีโอเป็น ${option.quality}p…`};
    for (let count = 0; count < 240; count++) {
      await new Promise(resolve => setTimeout(resolve, 2000));
      const job = await api(`/api/jobs/${id}`);
      if (job.status === 'error') throw new Error(job.error);
      if (job.status === 'ready') {
        $('file').href = `/api/files/${id}`;
        $('file').textContent = `บันทึกไฟล์ MP4 ${option.quality}p ↓`;
        $('file').hidden = false;
        message(`ไฟล์ ${option.quality}p พร้อมแล้ว กดบันทึกไฟล์ได้เลย`);
        return;
      }
      message(stages[job.stage] || stages.downloading);
    }
    throw new Error('รอนานเกินไป กรุณาลองใหม่ภายหลัง');
  } catch (error) { message(error.message); }
  finally { setBusy(false); }
}
