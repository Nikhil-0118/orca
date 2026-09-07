import subprocess
import time
import urllib.request
import json
import sys

chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
user_data = r"C:\Users\admin\AppData\Local\Temp\chrome_probe_" + str(int(time.time()))

cmd = [
    chrome_path,
    "--headless=new",
    "--remote-debugging-port=9333",
    f"--user-data-dir={user_data}",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-background-networking",
    "http://localhost:5173/"
]

print("Launching Chrome...")
proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

for i in range(20):
    time.sleep(0.5)
    try:
        with urllib.request.urlopen("http://127.0.0.1:9333/json/list", timeout=1) as resp:
            data = json.loads(resp.read().decode())
            print("Connected to Chrome CDP! Pages found:", len(data))
            print(json.dumps(data, indent=2))
            break
    except Exception as e:
        print(f"Waiting for CDP... ({e})")
else:
    print("Failed to connect to Chrome CDP")
    stdout, stderr = proc.communicate(timeout=2)
    print("STDOUT:", stdout.decode(errors="replace"))
    print("STDERR:", stderr.decode(errors="replace"))

proc.terminate()
