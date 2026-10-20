import psutil
import time
import firebase_admin
from firebase_admin import credentials, messaging

# 1. Authorize Firebase
cred = credentials.Certificate("serviceAccountKey.json")
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

# PASTE YOUR PHYSICAL PHONE TOKEN HERE
device_token = "fj4zQGyWQKK9_PuQbdLBmt:APA91bFDwM0lH1q0wLpMHGuy821F-nQtDr0bGYkkBjsmf1AkzjnbophC67ahHidvZthe3y4zQ0-HWxnFYn9z84uESe7tReDVKFqxj423t71jrPz8aGlsdbU"


def send_alert_to_phone(process_name, pid, command):
    message = messaging.Message(
        data={
            "PROCESS": process_name,
            "PID": str(pid),
            "COMMAND": command
        },
        token=device_token,
    )
    try:
        messaging.send(message)
        print(f"[+] Alert sent to physical phone for {process_name} (PID: {pid})")
    except Exception as e:
        print("[-] Failed to send alert:", e)


def monitor_and_intercept():
    print("🛡️ OmniGuard Live Daemon Active.")
    print("Monitoring for high-risk binaries (powershell.exe, cmd.exe)...")

    seen_pids = set()
    target_binaries = ['powershell.exe', 'cmd.exe']

    while True:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                proc_name = proc.info['name']
                if proc_name and proc_name.lower() in target_binaries:
                    pid = proc.info['pid']

                    if pid not in seen_pids:
                        # 1. FREEZE THE PROCESS IN RAM
                        proc.suspend()
                        print(f"\n[!] THREAT INTERCEPTED: {proc_name} (PID: {pid}) suspended in RAM.")

                        # 2. Extract command arguments
                        cmd_args = proc.info['cmdline']
                        command = " ".join(cmd_args) if cmd_args else "Hidden Command"

                        # 3. Fire alert to physical phone
                        send_alert_to_phone(proc_name, pid, command)

                        seen_pids.add(pid)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

        time.sleep(1)


if __name__ == "__main__":
    monitor_and_intercept()