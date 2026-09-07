import subprocess
import time
import urllib.request
import os
import sys

chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
user_data = r"C:\Users\admin\AppData\Local\Temp\chrome_inspect_" + str(int(time.time()))

cmd = [
    chrome_path,
    "--headless=new",
    "--remote-debugging-port=9333",
    f"--user-data-dir={user_data}",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-extensions",
    "--window-size=1280,800",
    "about:blank"
]

print("Launching Chrome on port 9333...")
chrome_proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

try:
    for i in range(25):
        time.sleep(0.5)
        try:
            with urllib.request.urlopen("http://127.0.0.1:9333/json/version", timeout=1) as resp:
                print("Chrome CDP ready!")
                break
        except Exception:
            pass
    else:
        print("Chrome CDP failed to start.")
        sys.exit(1)

    print("Running Node.js DOM inspection...", flush=True)
    script_path = os.path.join(os.path.dirname(__file__), "inspect_leaflet_dom.js")
    node_proc = subprocess.Popen(["node", script_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in node_proc.stdout:
        print(line, end="", flush=True)
    node_proc.wait()

finally:
    chrome_proc.terminate()
    try:
        chrome_proc.wait(timeout=3)
    except Exception:
        chrome_proc.kill()
