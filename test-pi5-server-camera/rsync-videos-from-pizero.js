const { exec } = require('child_process');

const PI_ZERO_USER = 'wasankds';
const PI_ZERO_IP = '192.168.1.134';
const REMOTE_DIR = '~/eagle-eye-legion-pizero/videos/';
const LOCAL_DIR = './videos-pizero/';

// คำสั่ง rsync:
// -a (archive), 
// -v (verbose), 
// -z (compress ตอนส่ง), 
// --remove-source-files (ดูดเสร็จลบทิ้งที่ต้นทาง)
// --bwlimit=500 (จำกัดแบนด์วิดท์ 500KB/s)
const cmd = `rsync -avz --bwlimit=500 ${PI_ZERO_USER}@${PI_ZERO_IP}:${REMOTE_DIR} ${LOCAL_DIR}`;

console.log("[*] Starting to fetch videos from Pi Zero...");

exec(cmd, (error, stdout, stderr) => {
    if (error) {
        console.error(`[!] Error: ${error.message}`);
        return;
    }
    if (stderr) {
        console.error(`[!] Stderr: ${stderr}`);
    }
    console.log(`[+] Sync Complete:\n${stdout}`);
});