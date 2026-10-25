const $ = id => document.getElementById(id);
let inspectedURL = '';
let busy = false;
function message(text) { $('message').textContent = text; }
async function api(path, body) {
  const response = await fetch(path, body ? {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)} : {});
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'ข้อมูลไม่ถูกต้อง กรุณาตรวจสอบลิงก์');
  return data;
}
$('form').addEventListener('submit', async event => {
  event.preventDefault();
  if (busy) return;
  busy = true; $('inspect').disabled = true;
  $('preview').hidden = $('actions').hidden = $('file').hidden = true;
  $('authorized').checked = false; inspectedURL = '';
  message('กำลังตรวจสอบวิดีโอ…');
  const url = $('url').value.trim();
  try {
    const data = await api('/api/inspect', {url});
    if (!data.qualities.length) throw new Error('ไม่พบคุณภาพ MP4 ที่ระบุขนาดได้และระบบรองรับ');
    inspectedURL = url;
    $('title').textContent = data.title;
    $('duration').textContent = data.duration ? `ความยาว ${Math.round(data.duration)} วินาที` : 'ไม่ทราบความยาว';
    $('thumbnail').hidden = !data.thumbnail;
    if (data.thumbnail) $('thumbnail').src = data.thumbnail;
    $('quality').replaceChildren(...data.qualities.map(height => new Option(`${height}p`, height)));
    $('quality').value = data.qualities.includes(720) ? 720 : data.qualities.at(-1);
    $('preview').hidden = $('actions').hidden = false;
    message('ตรวจสอบแล้ว เลือกคุณภาพและยืนยันสิทธิ์เพื่อดาวน์โหลด');
  } catch (error) { message(error.message); }
  finally { busy = false; $('inspect').disabled = false; }
});
$('download').addEventListener('click', async () => {
  if (busy) return;
  if (!$('authorized').checked) return message('กรุณายืนยันว่าคุณมีสิทธิ์ดาวน์โหลดเนื้อหานี้');
  busy = true; $('download').disabled = $('inspect').disabled = true; $('file').hidden = true;
  try {
    const {id} = await api('/api/download', {url:inspectedURL, quality:Number($('quality').value), authorized:true});
    message('กำลังดาวน์โหลดและเตรียมไฟล์ MP4…');
    for (let count = 0; count < 120; count++) {
      await new Promise(resolve => setTimeout(resolve, 2000));
      const job = await api(`/api/jobs/${id}`);
      if (job.status === 'error') throw new Error(job.error);
      if (job.status === 'ready') {
        $('file').href = `/api/files/${id}`; $('file').hidden = false;
        message('ไฟล์พร้อมแล้ว กดบันทึกไฟล์ได้เลย'); return;
      }
    }
    throw new Error('รอนานเกินไป กรุณาลองใหม่ภายหลัง');
  } catch (error) { message(error.message); }
  finally { busy = false; $('download').disabled = $('inspect').disabled = false; }
});
