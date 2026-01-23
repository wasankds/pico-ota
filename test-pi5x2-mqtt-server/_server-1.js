const mqtt = require('mqtt');
const client = mqtt.connect('mqtt://localhost'); // เชื่อมต่อกับ Broker ในตัวเอง

client.on('connect', () => {
  console.log('Connected to MQTT Broker on Pi 5');
});

// ฟังก์ชันจำลองการส่งคำสั่งเมื่อมีการกดปุ่มที่หน้าเว็บ
function sendMotorCommand(action) {
  // action อาจจะเป็น 'forward', 'backward' หรือ 'stop'
  const topic = 'robot/motor';
  client.publish(topic, action, { qos: 1 });
  console.log(`Sent command: ${action} to topic: ${topic}`);
}

// ตัวอย่างการเรียกใช้: สั่งเดินหน้า
sendMotorCommand('forward');

// ตัวอย่างการเรียกใช้: สั่งหยุด (เมื่อปล่อยปุ่ม)
setTimeout(() => {
  sendMotorCommand('stop');
}, 3000); // หยุดหลังจาก 3 วินาที