const net = require('net');
const express = require('express');
const { spawn } = require('child_process');
const app = express();
const port = 3000;

// --- CONFIGURATION ---
const PI_ZERO = "wasankds@192.168.1.134";
const PI_ZERO_FOLDER = "/home/wasankds/pizero-servo";
const PI_ZERO_RUN_FILE = "servo-argrument-speed-que-from-server.py";
// const PI_ZERO_STOP_FILE = "stop-servo.py";

const PYTHON = "/usr/bin/python3";
const SCRIPT_PATH = `${PI_ZERO_FOLDER}/${PI_ZERO_RUN_FILE}`;
const CENTER_POS = 1500;
// const STOP_PATH = `${PI_ZERO_FOLDER}/${PI_ZERO_STOP_FILE}`;

// สำหรับทดสอบ Orbit
const PI_ZERO_ORBIT_FILE = "servo-orbit.py";
const ORBIT_PATH = `${PI_ZERO_FOLDER}/${PI_ZERO_ORBIT_FILE}`;


app.use(express.static('.'));

function sendSSH(remoteCommand) {
  console.log(`Executing: ${remoteCommand}`);

  const child = spawn('ssh', [
    // '-t', // เพิ่ม -t ตรงนี้จะช่วยให้ทั้ง move และ orbit เสถียรขึ้น
    '-o', 'StrictHostKeyChecking=no',
    PI_ZERO,
    remoteCommand
  ]);

  child.stdout.on('data', (data) => console.log(`[Pi Zero]: ${data}`));
  child.stderr.on('data', (data) => console.error(`[SSH Error]: ${data}`));
}

// --- API ROUTES ---

// สั่งขยับ
app.get('/move', (req, res) => {
  // console.log('req.query ==> ', req.query);
  const { pan, tilt, speed = 3 } = req.query;
  // สั่งรันสคริปต์ขยับ
  const remoteCmd = `${PYTHON} ${SCRIPT_PATH} --pan ${pan || CENTER_POS} --tilt ${tilt || CENTER_POS} --speed ${speed}`;
  console.log(`Move Command: ${remoteCmd}`);

  sendSSH(remoteCmd);
  res.send('Moved');
});

// center
app.get('/center', (req, res) => {
  // console.log('req.query ==> ', req.query);
  const remoteCmd = `${PYTHON} ${SCRIPT_PATH} --pan ${CENTER_POS} --tilt ${CENTER_POS} --speed 3`;

  sendSSH(remoteCmd);
  res.send('Centered');
});


app.get('/stop', (req, res) => {
  const remoteCmd1 = `pkill -f ${PI_ZERO_RUN_FILE};`;
  const remoteCmd2 = `pkill -f ${PI_ZERO_ORBIT_FILE}`;
  console.log("🛑 Stopping All Processes");
  sendSSH(remoteCmd1);
  sendSSH(remoteCmd2);

  res.send('Stopped');
});


// orbit
app.get('/orbit', (req, res) => {
  const remoteCmd = `${PYTHON} ${ORBIT_PATH}`;
  const child = spawn('ssh', [
    // '-t', 
    '-o', 'StrictHostKeyChecking=no',
    PI_ZERO,
    remoteCmd
  ]);

  child.stdout.on('data', (data) => console.log(`[Orbit Out]: ${data}`));
  child.stderr.on('data', (data) => console.error(`[Orbit Err]: ${data}`));
  
  // เมื่อ Orbit จบลง (ถ้ามันจบเอง)
  child.on('close', () => console.log("Orbit Process Closed"));

  res.send('Orbit Started');
});



// สร้างตัวแปรเก็บสถานะการเชื่อมต่อกล้องตัวเดียว
let cameraSocket = null;
const videoClients = new Set(); // เก็บ Response ของคนที่เปิดดูเว็บทุกคน

app.get('/video_feed', (req, res) => {
    // 1. ตั้งค่า Header MJPEG
    res.writeHead(200, {
        'Content-Type': 'multipart/x-mixed-replace; boundary=frame',
        'Cache-Control': 'no-cache',
        'Connection': 'close',
        'Pragma': 'no-cache'
    });

    // 2. เพิ่ม Client คนนี้เข้ากลุ่มผู้ดู
    videoClients.add(res);

    // 3. ถ้ายังไม่มีใครเชื่อมต่อกับ Pi Zero เลย ให้เริ่มเชื่อมต่อ
    if (!cameraSocket) {
        cameraSocket = new net.Socket();
        let buffer = Buffer.alloc(0);
        let expectedLength = 0;

        cameraSocket.connect(8000, '192.168.1.134', () => {
            console.log('--- Initialized Global Camera Socket ---');
        });

        cameraSocket.on('data', (chunk) => {
            buffer = Buffer.concat([buffer, chunk]);
            while (true) {
                if (expectedLength === 0) {
                    if (buffer.length >= 4) {
                        expectedLength = buffer.readUInt32LE(0);
                        buffer = buffer.slice(4);
                    } else break;
                }

                if (expectedLength > 0 && buffer.length >= expectedLength) {
                    const frame = buffer.slice(0, expectedLength);
                    buffer = buffer.slice(expectedLength);
                    
                    // กระจายภาพเฟรมนี้ให้ทุกคนที่เชื่อมต่ออยู่
                    const frameData = `--frame\r\nContent-Type: image/jpeg\r\nContent-Length: ${frame.length}\r\n\r\n${frame.toString('binary')}\r\n`;
                    videoClients.forEach(client => {
                        client.write(Buffer.from(frameData, 'binary'));
                    });

                    expectedLength = 0;
                } else break;
            }
        });

        cameraSocket.on('error', () => { cameraSocket.destroy(); cameraSocket = null; });
        cameraSocket.on('close', () => { cameraSocket = null; });
    }

    // 4. เมื่อมีคนปิดหน้าเว็บ
    req.on('close', () => {
        videoClients.delete(res);
        // ถ้าไม่มีใครดูแล้วเลยจริงๆ ให้ปิด Socket ที่ต่อกับ Pi Zero เพื่อประหยัดไฟ/ความร้อน
        if (videoClients.size === 0 && cameraSocket) {
            console.log('No viewers left, closing camera socket.');
            cameraSocket.destroy();
            cameraSocket = null;
        }
    });
});
app.listen(port, () => {
  console.log(`🚀 Pi 5 Controller: http://localhost:${port}`);
});