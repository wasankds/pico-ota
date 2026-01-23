const express = require('express');
const mqtt = require('mqtt');
const net = require('net');
const app = express();

const PI_ZERO_IP = '192.168.1.134';
const client = mqtt.connect('mqtt://localhost');

app.use(express.static('public'));

let currentController = null; // เก็บ Session ID ของผู้ควบคุม
app.get('/control', (req, res) => {
  // เช็กว่าคนส่งคำสั่งมาคือคนที่คุมอยู่ปัจจุบันหรือไม่ (หรือถ้ายังไม่มีคนคุมเลย)
  if (!currentController) {
    currentController = req.ip; // ใช้ IP เป็นตัวระบุเบื้องต้น
  }

  if (currentController === req.ip) {
    const cmd = req.query.cmd;
    client.publish('robot/control', cmd);
    res.send({ status: 'ok', controller: true });
  } else {
    // ถ้าไม่ใช่คนคุม ให้ปฏิเสธคำสั่ง
    res.status(403).send({ status: 'busy', message: 'System is controlled by another user' });
  }
});
// เพิ่มระบบ Release Lock เมื่อคนคุมปิดเว็บ
app.get('/release', (req, res) => {
  if (currentController === req.ip) {
    currentController = null;
    res.send({ status: 'released' });
  } else {
    res.status(403).send({ status: 'denied' });
  }
});

app.get('/stream', (req, res) => {
  console.log("[*] Client requesting stream...");

  res.writeHead(200, {
    'Content-Type': 'multipart/x-mixed-replace; boundary=frame',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive'
  });

  const tcpClient = new net.Socket();

  // --- จุดสำคัญ: ดักจับ Error ไม่ให้ Node.js Crash ---
  tcpClient.on('error', (err) => {
    console.error(`[!] Pi Zero Connection Error: ${err.message}`);
    // ส่งข้อความบอก Browser นิดหน่อยแล้วจบการเชื่อมต่อ
    res.end();
  });

  tcpClient.connect(8000, PI_ZERO_IP, () => {
    console.log(`[+] Connected to Pi Zero Stream`);
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

  req.on('close', () => {
    console.log("[*] Web client closed. Destroying socket.");
    tcpClient.destroy();
  });
});

app.listen(3000, () => console.log('Server on 3000'));