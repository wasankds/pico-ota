const express = require('express');
const mqtt = require('mqtt');
const net = require('net');
const app = express();

// --- CONFIG ---
const PI_ZERO_IP = '192.168.1.134';
const MQTT_BROKER = 'mqtt://localhost';
const client = mqtt.connect(MQTT_BROKER);

let currentController = null;
let isRobotRecording = false;

app.use(express.static('public'));

// --- MQTT LOGIC ---
client.on('connect', () => {
  console.log("[*] Connected to MQTT Broker");
  client.subscribe('robot/status');
});

// ใน server ส่วน client.on('message')
client.on('message', (topic, message) => {
  if (topic === 'robot/status') {
    const status = message.toString();
    isRobotRecording = (status === 'recording');
    console.log(`[*] Sync Status from Pi Zero: ${status}`);
    // (Optional) พ่น log ออกมาดูว่ามันส่ง idle กลับมาจริงไหมตอนกด Stop
  }
});

// --- API ENDPOINTS ---

// 1. เช็กสถานะการบันทึก (สำหรับหน้าเว็บตอนโหลดใหม่)
app.get('/get-status', (req, res) => {
  // สั่งให้ Pi Zero ส่งสถานะล่าสุดกลับมาทาง MQTT
  client.publish('robot/control', 'check_status');
  // ตอบสถานะที่บันทึกไว้ล่าสุด
  res.send({ isRecording: isRobotRecording });
});

// 2. ควบคุมหุ่นยนต์ (ล็อคสิทธิ์คนแรก)
app.get('/control', (req, res) => {
  if (!currentController) {
    currentController = req.ip;
    console.log(`[+] Controller Assigned: ${req.ip}`);
  }

  if (currentController === req.ip) {
    // ในส่วน app.get('/control')
    // เมื่อมีการสั่ง rec_stop ให้ Node.js มโนไว้ก่อนเลยว่ากำลังจะหยุด เพื่อให้หน้าเว็บโหลดใหม่แล้วไม่ค้าง
    if (req.query.cmd === 'rec_stop') {
      isRobotRecording = false;
    }
    const cmd = req.query.cmd;
    client.publish('robot/control', cmd);
    res.send({ status: 'ok', controller: true });
  } else {
    res.status(403).send({ status: 'busy', message: 'Another user is controlling' });
  }
});

// 3. ปล่อยสิทธิ์การควบคุม
app.get('/release', (req, res) => {
  if (currentController === req.ip) {
    currentController = null;
    console.log(`[-] Controller Released: ${req.ip}`);
    res.send({ status: 'released' });
  } else {
    res.status(403).send({ status: 'denied' });
  }
});

// 4. ระบบ Stream ภาพ (TCP Proxy)
app.get('/stream', (req, res) => {
  res.writeHead(200, {
    'Content-Type': 'multipart/x-mixed-replace; boundary=frame',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive'
  });

  const tcpClient = new net.Socket();
  tcpClient.setTimeout(5000); // ป้องกันค้างถ้า Pi Zero ไม่ตอบกลับ

  tcpClient.connect(8000, PI_ZERO_IP, () => {
    console.log(`[+] Proxy: Connected to Pi Zero Stream`);
  });

  let buffer = Buffer.alloc(0);
  tcpClient.on('data', (data) => {
    buffer = Buffer.concat([buffer, data]);
    while (buffer.length >= 4) {
      const size = buffer.readUInt32LE(0);
      if (buffer.length >= 4 + size) {
        const jpg = buffer.slice(4, 4 + size);
        res.write(`--frame\r\nContent-Type: image/jpeg\r\nContent-Length: ${jpg.length}\r\n\r\n`);
        res.write(jpg);
        res.write(`\r\n`);
        buffer = buffer.slice(4 + size);
      } else break;
    }
  });

  tcpClient.on('error', (err) => {
    console.error(`[!] Stream Proxy Error: ${err.message}`);
    res.end();
  });

  tcpClient.on('timeout', () => {
    console.log("[!] Stream Connection Timeout");
    tcpClient.destroy();
    res.end();
  });

  req.on('close', () => {
    tcpClient.destroy();
  });
});

// --- START SERVER ---
const PORT = 3000;
app.listen(PORT, () => {
  console.log(`--------------------------------------`);
  console.log(`🚀 Robot Controller Server is running`);
  console.log(`📍 URL: http://localhost:${PORT}`);
  console.log(`📍 Pi Zero IP: ${PI_ZERO_IP}`);
  console.log(`--------------------------------------`);
});