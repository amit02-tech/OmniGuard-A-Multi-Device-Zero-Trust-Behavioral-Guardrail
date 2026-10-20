import wmi
import ctypes
from ctypes import wintypes
import time
import os
import torch
import torch.nn as nn
import asyncio
import websockets
import json
import base64
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature

# --- 5. OOB CRYPTOGRAPHIC RELAY SYSTEM ---
# --- 5. OOB CRYPTOGRAPHIC RELAY SYSTEM ---
# --- 5. OOB CRYPTOGRAPHIC RELAY SYSTEM ---
try:
    with open("daemon_public.pem", "rb") as key_file:
        public_key = serialization.load_pem_public_key(key_file.read())
except FileNotFoundError:
    print("[-] Error: daemon_public.pem not found. Run generate_keys.py first.")
    exit(1)

async def _oob_transaction(payload):
    uri = "ws://localhost:8000/ws/daemon"
    try:
        async with websockets.connect(uri) as websocket:
            await websocket.send(json.dumps(payload))
            print("[*] Threat data pushed to Secure Relay. Waiting for Mobile signature...")

            response_str = await websocket.recv()
            response = json.loads(response_str)

            action = response.get("action")
            resp_pid = response.get("pid")
            signature_b64 = response.get("signature")

            # Verify the Ed25519 Signature
            signature_bytes = base64.b64decode(signature_b64)
            message_to_sign = f"{action}:{resp_pid}".encode('utf-8')

            try:
                public_key.verify(signature_bytes, message_to_sign)
                print("[+] Cryptographic Signature VERIFIED! No MITM tampering detected.")
                return action == "APPROVE"
            except InvalidSignature:
                print("[-] CRITICAL: Invalid cryptographic signature! Forgery attempt detected.")
                return False
    except Exception as e:
        print(f"[-] OOB Relay Network Error: {e}")
        return False

def request_oob_verification(pid, process_name, command_line, bio_status):
    # Added bio_status to the payload so the phone knows if the face failed!
    payload = {"pid": pid, "process": process_name, "command": command_line, "biometrics_passed": bio_status}
    return asyncio.run(_oob_transaction(payload))

# --- INTEGRATING MODULE 2 ---
from omniguard_biometrics import verify_biometrics

# --- 1. NATIVE WINDOWS API BINDINGS ---
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
ntdll = ctypes.WinDLL('ntdll', use_last_error=True)

PROCESS_ALL_ACCESS = 0x001F0FFF
PAGE_EXECUTE_READWRITE = 0x40
MEM_COMMIT = 0x1000

class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_void_p),
        ("AllocationBase", ctypes.c_void_p),
        ("AllocationProtect", wintypes.DWORD),
        ("Alignment1", wintypes.DWORD),
        ("RegionSize", ctypes.c_size_t),
        ("State", wintypes.DWORD),
        ("Protect", wintypes.DWORD),
        ("Type", wintypes.DWORD),
        ("Alignment2", wintypes.DWORD),
    ]

# --- 2. KERNEL THREAD CONTROL SYSTEM ---
def atomic_suspend(pid):
    """Instantly freezes all threads in the process at the OS kernel level."""
    handle = kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, pid)
    if not handle: return False
    status = ntdll.NtSuspendProcess(handle)
    kernel32.CloseHandle(handle)
    return status == 0

def atomic_resume(pid):
    """Unfreezes the process, allowing execution to continue."""
    handle = kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, pid)
    if not handle: return False
    status = ntdll.NtResumeProcess(handle)
    kernel32.CloseHandle(handle)
    return status == 0

def atomic_terminate(pid):
    """Mercilessly kills the process and dumps it from memory."""
    handle = kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, pid)
    if not handle: return False
    status = kernel32.TerminateProcess(handle, -1)
    kernel32.CloseHandle(handle)
    return status != 0

def scan_process_memory(pid):
    """Scans the virtual address space for committed RWX shellcode allocations."""
    handle = kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, pid)
    if not handle: return False
    mbi = MEMORY_BASIC_INFORMATION()
    address = ctypes.c_void_p(0)
    injected = False
    while kernel32.VirtualQueryEx(handle, address, ctypes.byref(mbi), ctypes.sizeof(mbi)):
        if mbi.State == MEM_COMMIT and mbi.Protect == PAGE_EXECUTE_READWRITE:
            injected = True
            break
        base_addr = mbi.BaseAddress or 0
        address = ctypes.c_void_p(base_addr + mbi.RegionSize)
    kernel32.CloseHandle(handle)
    return injected

# --- 3. PYTORCH NLP INFERENCE ENGINE ---
VALID_CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -_\\/.:\"'^%$#@!&*"
CHAR_TO_INDEX = {char: idx + 1 for idx, char in enumerate(VALID_CHARS)}
VOCAB_SIZE = len(VALID_CHARS) + 1
MAX_SEQ_LENGTH = 128

def vectorize_command(cmd):
    vec = [CHAR_TO_INDEX.get(c, 0) for c in str(cmd)[:MAX_SEQ_LENGTH]]
    vec += [0] * (MAX_SEQ_LENGTH - len(vec))
    return vec

class EDRCommandClassifier(nn.Module):
    def __init__(self):
        super(EDRCommandClassifier, self).__init__()
        self.embedding = nn.Embedding(num_embeddings=VOCAB_SIZE, embedding_dim=64)
        self.conv1 = nn.Conv1d(in_channels=64, out_channels=128, kernel_size=5, padding=2)
        self.bn1 = nn.BatchNorm1d(128)
        self.relu = nn.ReLU()
        self.pool1 = nn.MaxPool1d(kernel_size=2)
        self.conv2 = nn.Conv1d(in_channels=128, out_channels=128, kernel_size=3, padding=1)
        self.bn2 = nn.BatchNorm1d(128)
        self.pool2 = nn.MaxPool1d(kernel_size=2)
        self.dropout = nn.Dropout(0.3)
        self.fc1 = nn.Linear(128 * (MAX_SEQ_LENGTH // 4), 64)
        self.fc2 = nn.Linear(64, 1)

    def forward(self, x):
        x = self.embedding(x)
        x = x.permute(0, 2, 1)
        x = self.pool1(self.relu(self.bn1(self.conv1(x))))
        x = self.pool2(self.relu(self.bn2(self.conv2(x))))
        x = x.view(x.size(0), -1)
        x = self.dropout(x)
        x = self.relu(self.fc1(x))
        x = self.dropout(x)
        return self.fc2(x)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
nlp_model = EDRCommandClassifier().to(device)
nlp_model.load_state_dict(torch.load("omniguard_nlp.pth", map_location=device, weights_only=True))
nlp_model.eval()

def analyze_command_threat(command_string, threshold=0.85):
    if not command_string or not command_string.strip(): return False, 0.0
    tensor = torch.tensor([vectorize_command(command_string)], dtype=torch.long).to(device)
    with torch.no_grad():
        score = torch.sigmoid(nlp_model(tensor).squeeze()).item()
    return score >= threshold, score

# --- 4. MASTER REAL-TIME EVENT LOOP ---
def run_edr_daemon():
    print("[*] OMNIGUARD ENTERPRISE EDR ONLINE")
    print("[*] Engine: PyTorch CNN | Hardware: GPU | Vault: OpenCV")
    print("[*] Actively monitoring kernel process creation...\n")

    c = wmi.WMI()
    process_watcher = c.Win32_Process.watch_for("creation")
    TARGET_EXECUTABLES = ["powershell.exe", "cmd.exe", "pwsh.exe", "python.exe"]

    while True:
        try:
            new_process = process_watcher()
            pid = int(new_process.ProcessId)
            name = new_process.Name.lower()
            raw_cmd = new_process.CommandLine if new_process.CommandLine else ""

            if not raw_cmd:
                continue

            # --- ENTERPRISE WHITELIST ---
            cmd_lower = raw_cmd.lower().replace('"', '').strip()

            if "jetbrains" in cmd_lower or "pycharm" in cmd_lower or "shell-integrations" in cmd_lower:
                continue
            if cmd_lower == "powershell.exe" or cmd_lower.endswith("\\powershell.exe") or cmd_lower.endswith(
                    "\\cmd.exe"):
                continue
            if "mcafee" in cmd_lower or "chrome-extension" in cmd_lower:
                continue
            # ----------------------------

            is_malicious = False
            is_injected = False

            if name in TARGET_EXECUTABLES:
                # --- UPDATED: Lower the threshold to 0.50 (50%) to make the AI more aggressive ---
                is_malicious, score = analyze_command_threat(raw_cmd, threshold=0.50)

                # VISUAL DEBUGGER: Print every command the AI analyzes and its threat score
                print(f"[*] AI SCAN -> Score: {score:.4f} | Process: {name} | Cmd: {raw_cmd[:60]}...")

                # ... (rest of your loop remains exactly the same) ...

                if name == "python.exe":
                    time.sleep(1)
                    is_injected = scan_process_memory(pid)

            if is_malicious or is_injected:
                # 1. Freeze the execution thread immediately
                atomic_suspend(pid)

                # 2. Trigger Factor 1: Local Biometric Vault
                # 2. Trigger Factor 1: Local Biometric Vault
                print("[*] Initiating Factor 1: Local Biometric Verification...")
                is_bio_authorized = verify_biometrics(timeout_seconds=15)

                if not is_bio_authorized:
                    print("[!] BIOMETRIC FAILURE: Unauthorized face detected or timeout!")
                    print("[*] Escalating to Factor 2: Alerting Mobile Owner of physical intrusion...")
                else:
                    print("[+] Biometrics passed. Sending to Mobile for final 2FA confirmation...")

                # 3. Trigger Factor 2: Mobile Cryptographic OOB (ALWAYS RUNS)
                is_oob_authorized = request_oob_verification(pid, name, raw_cmd, is_bio_authorized)

                # 4. Final Zero-Trust Execution Decision
                print("\n" + "=" * 70)
                if is_oob_authorized:
                    print("[+] ZERO-TRUST VERIFIED: Mobile device explicitly authorized execution.")
                    print("[*] Firing NtResumeProcess...")
                    atomic_resume(pid)
                    print("[+] OS Kernel Lock Removed. Process executing normally.")
                else:
                    print("[-] THREAT CONFIRMED: Mobile device explicitly denied execution.")
                    print("[*] Firing TerminateProcess...")
                    atomic_terminate(pid)
                    print("[-] Malware destroyed from RAM.")
                print("=" * 70 + "\n")


        except Exception as e:

            # Print any silent errors so we can see them!

            print(f"[!] BACKGROUND ERROR: {e}")

            continue

if __name__ == "__main__":
    run_edr_daemon()