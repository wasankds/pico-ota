

document.addEventListener('DOMContentLoaded', () => {

  // เพิ่มฟังก์ชันดักจับ Error เพื่อให้ลองโหลดใหม่ถ้าภาพไม่ขึ้น
  const v = document.getElementById('cameraStream');
  v.onerror = function () {
    console.log("Stream error, retrying...");
    setTimeout(() => { v.src = "/video_feed?t=" + new Date().getTime(); }, 2000);
  };


  // // บังคับโหลด Stream เมื่อเปิดหน้าเว็บ
  // window.onload = function() {
  //     const streamImg = document.getElementById('cameraStream');
  //     // เพิ่ม timestamp ป้องกัน cache
  //     streamImg.src = "/video_feed?t=" + new Date().getTime();
      
  //     // ถ้าโหลดพลาด ให้ลองใหม่ทุก 3 วินาที
  //     streamImg.onerror = function() {
  //         console.log("Stream lost, retrying...");
  //         setTimeout(() => {
  //             streamImg.src = "/video_feed?t=" + new Date().getTime();
  //         }, 3000);
  //     };
  // };


});



let currentPan = 1500;
let currentTilt = 1500;
let isOrbiting = false;
const step = 100;

function setButtonsState(disabled) {
  isOrbiting = disabled;
  const navButtons = document.querySelectorAll('.grid-container button, .orbit-btn');
  navButtons.forEach(btn => {
    btn.disabled = disabled;
    btn.style.opacity = disabled ? "0.4" : "1";
  });
}


//
function moveByStep(x, y) {
  if (isOrbiting) return;

if(IS_FLIP_VERTICAL) {
    // Pan ถูกแล้ว ให้ใช้ค่าเดิม (เช่น -=)
    currentPan -= (x * step); 
    
    // Tilt ยังสลับอยู่ ให้เปลี่ยนจาก -= เป็น += (หรือจาก += เป็น -=)
    currentTilt += (y * step); 
  } else {
    currentPan += (x * step);
    currentTilt -= (y * step);
  }

  // จำกัดขอบเขต Servo
  currentPan = Math.max(500, Math.min(2500, currentPan));
  currentTilt = Math.max(1150, Math.min(2500, currentTilt));
  
  updateDisplay();
  fetch(`/move?pan=${currentPan}&tilt=${currentTilt}&speed=3`);
}
function centerAll() {
  if (isOrbiting) return;
  currentPan = 1500;
  currentTilt = 1500;
  updateDisplay();
  fetch(`/center`);
}

function stopNow() {
  fetch('/stop').then(() => {
    setButtonsState(false);
  });
}

function testOrbit() {
  if (confirm("เริ่ม Orbit?")) {
    setButtonsState(true);
    fetch('/orbit');
  }
}

function updateDisplay() {
  document.getElementById('valPan').innerText = currentPan;
  document.getElementById('valTilt').innerText = currentTilt;
}