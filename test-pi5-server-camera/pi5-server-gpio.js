/* 

การใช้งาน 
node pi5-server-gpio.js pin=17 status=0

*/


const net = require('net');

// --- CONFIGURATION ---
const PI_ZERO_IP = '192.168.1.134'; // แก้เป็น IP ของ Pi Zero
const PORT = 8001;

// 1. ดึง Argument และ Parse ค่า
const args = process.argv.slice(2);
const params = {};

args.forEach(arg => {
  const [key, value] = arg.split('=');
  if (key && value) params[key.toLowerCase()] = value;
});

const pin = params.pin;
const status = params.status;

if (!pin || (status !== '0' && status !== '1')) {
  console.log('Usage: node control.js pin=14 status=1');
  process.exit(1);
}

// 2. แพ็กข้อมูลในรูปแบบที่ Python เข้าใจ (String)
const payload = `pin:${pin},status:${status}`;

// 3. ส่งข้อมูล
const client = new net.Socket();
client.connect(PORT, PI_ZERO_IP, () => {
  console.log(`[*] Sending to Pi Zero: ${payload}`);
  client.write(payload);
});

client.on('data', (data) => {
  console.log(`[Response]: ${data.toString().trim()}`);
  client.destroy();
});

client.on('error', (err) => {
  console.error(`[!] Error: ${err.message}`);
});