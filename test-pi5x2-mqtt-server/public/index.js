let lastSentCommand = "";
let isRecording = false;
const keyState = {}; // เก็บสถานะการกดปุ่ม

document.addEventListener('DOMContentLoaded', function () {
  console.log("EagleEye System Started");
  const img = document.getElementById('mainStream');
  if (img) img.src = "/stream";

  checkCurrentStatus();

  // ส่งคำสั่งหยุดเริ่มต้น (ไม่ใช้ฟังก์ชัน send เพื่อเลี่ยงการตั้งค่า lastSentCommand)
  fetch('/control?cmd=stop');
  fetch('/control?cmd=servo_stop');
});

// คืนสิทธิ์เมื่อปิดหน้าเว็บ
window.addEventListener('beforeunload', () => fetch('/release'));
 

//=========================================================
// ฟังก์ชันส่งคำสั่งไปยังเซิร์ฟเวอร์
//=========================================================
// 

//=========================================================
// ฟังก์ชันส่งคำสั่ง (ปรับปรุงให้รองรับการกดรัว)
//=========================================================
function send(cmd) {
  // คำสั่งเคลื่อนที่หลัก
  const movementCommands = ['forward', 'backward', 'left', 'right'];
  const isMovement = movementCommands.includes(cmd);

  // ถ้าสั่งเคลื่อนที่ซ้ำเดิม ให้บล็อกไว้ (ยกเว้นสั่ง stop ให้ปล่อยผ่านเสมอ)
  if (isMovement && cmd === lastSentCommand) {
    return;
  }

  // อัปเดตสถานะล่าสุดทันที
  lastSentCommand = cmd;
  console.log(">>> SENDING:", cmd);

  fetch(`/control?cmd=${cmd}`)
    .then(response => {
      const statElement = document.getElementById('stat');
      if (statElement) {
        if (response.status === 403) {
          statElement.innerText = "⚠️ มีคนอื่นกำลังควบคุมอยู่!";
          statElement.style.color = "red";
        } else {
          statElement.innerText = "Last Command: " + cmd;
          statElement.style.color = "green";
        }
      }
    })
    .catch(err => {
      console.error("Fetch Error:", err);
      // ถ้า Error ให้ล้างค่าล่าสุด เพื่อให้กดซ้ำได้
      lastSentCommand = "";
    });
}



function wheelControl(event, cmd) {
  if (event.cancelable) event.preventDefault();
  send(cmd);
}

function emergencyStop() {
  send('emergency_stop');
}

function resetServo() {
  send('servo_stop');
  setTimeout(() => { send('pan_center'); }, 100);
  setTimeout(() => { send('tilt_center'); }, 250);
}

// --- จุดที่แก้ไข: แก้ชื่อ ID ให้ตรงกับ HTML (recBtn) ---
function updateRecordUI() {
  const btn = document.getElementById('recBtn'); // แก้จาก recordBtn เป็น recBtn
  if (!btn) return;

  if (isRecording) {
    btn.innerText = "● STOP RECORDING";
    btn.style.backgroundColor = "red";
    btn.classList.add('recording-active');
  } else {
    btn.innerText = "START RECORD";
    btn.style.backgroundColor = "";
    btn.classList.remove('recording-active');
  }
}

function checkCurrentStatus() {
  fetch('/get-status')
    .then(res => res.json())
    .then(data => {
      isRecording = data.isRecording;
      updateRecordUI();
    })
    .catch(err => console.error("Status Check Error:", err));
}

function toggleRecord() {
  const cmd = isRecording ? 'rec_stop' : 'rec_start';
  fetch(`/control?cmd=${cmd}`)
    .then(res => res.json())
    .then(data => {
      if (data.status === 'ok') {
        isRecording = !isRecording;
        updateRecordUI();
      }
    })
    .catch(err => console.error("Record Toggle Error:", err));
}

window.oncontextmenu = (e) => { e.preventDefault(); return false; };



//=========================================================
// KEYBOARD CONTROL (ใช้ e.code เพื่อความแม่นยำสูง)
//=========================================================
document.addEventListener('keydown', function (e) {
  // ป้องกันการเลื่อนหน้าจอเมื่อกด Arrow Keys หรือ Space
  if (["Space", "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"].includes(e.code)) {
    e.preventDefault();
  }

  const code = e.code; // ใช้ e.code จะเสถียรกว่า e.key

  if (keyState[code]) return; // ป้องกัน Repeat รัวๆ
  keyState[code] = true;

  switch (code) {
    case 'KeyW': send('forward'); break;
    case 'KeyS': send('backward'); break;
    case 'KeyA': send('left'); break;
    case 'KeyD': send('right'); break;
    case 'ArrowUp': send('tilt_up'); break;
    case 'ArrowDown': send('tilt_down'); break;
    case 'ArrowLeft': send('pan_left'); break;
    case 'ArrowRight': send('pan_right'); break;
    case 'Digit5':
    case 'Numpad5': resetServo(); break;
    case 'Space': emergencyStop(); break;
  }
});

document.addEventListener('keyup', function (e) {
  const code = e.code;
  keyState[code] = false; // ปลดล็อคสถานะปุ่ม

  // ตรวจสอบว่าปุ่มที่ปล่อยเป็นกลุ่มไหน
  if (['KeyW', 'KeyS', 'KeyA', 'KeyD'].includes(code)) {
    lastSentCommand = ""; // ล้างค่าก่อนส่ง stop
    send('stop');
  }
  else if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(code)) {
    lastSentCommand = ""; // ล้างค่าก่อนส่ง servo_stop
    send('servo_stop');
  }
});