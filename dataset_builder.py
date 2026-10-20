import urllib.request
import zipfile
import io
import yaml
import json
import csv
import random


# --- 1. DATA INGESTION ENGINES ---

def fetch_atomic_red_team():
    print("[*] Downloading Red Canary 'Atomic Red Team' master repository...")
    url = "https://github.com/redcanaryco/atomic-red-team/archive/refs/heads/master.zip"
    commands = []
    try:
        response = urllib.request.urlopen(url)
        zip_file = zipfile.ZipFile(io.BytesIO(response.read()))
        for file_info in zip_file.infolist():
            if "/atomics/T" in file_info.filename and file_info.filename.endswith(".yaml"):
                with zip_file.open(file_info) as file:
                    try:
                        yaml_content = yaml.safe_load(file)
                        for test in yaml_content.get('atomic_tests', []):
                            if 'windows' in test.get('supported_platforms', []):
                                cmd = test.get('executor', {}).get('command', '')
                                if cmd:
                                    commands.append((" ".join(cmd.split()), 1, file_info.filename.split('/')[-2]))
                    except yaml.YAMLError:
                        pass
    except Exception as e:
        print(f"[-] ART Download Failed: {e}")
    return commands


def fetch_lolbas_project():
    print("[*] Contacting LOLBAS API...")
    url = "https://lolbas-project.github.io/api/lolbas.json"
    commands = []
    try:
        response = urllib.request.urlopen(url)
        for entry in json.loads(response.read()):
            for cmd_obj in entry.get('Commands', []):
                cmd = cmd_obj.get('Command', '')
                if cmd:
                    commands.append((cmd, 1, cmd_obj.get('MitreID', 'Unknown')))
    except Exception as e:
        print(f"[-] LOLBAS Download Failed: {e}")
    return commands


def fetch_payloads_all_the_things():
    print("[*] Scraping raw Windows payloads from PayloadsAllTheThings...")
    # Grabbing a raw wordlist of Windows command injection vectors
    url = "https://raw.githubusercontent.com/swisskyrepo/PayloadsAllTheThings/master/Command%20Injection/Intruder/command-execution-windows.txt"
    commands = []
    try:
        response = urllib.request.urlopen(url)
        for line in response.read().decode('utf-8').splitlines():
            if line.strip():
                commands.append((line.strip(), 1, "T1059"))  # Mapping to generic CLI execution
    except Exception as e:
        print(f"[-] Payloads Download Failed: {e}")
    return commands


# --- 2. THE AI DATA AUGMENTATION ENGINE ---

def obfuscate_command(cmd):
    """Takes a standard command and generates advanced hacker variations."""
    variations = []

    # 1. Mixed Casing (pOwErShElL)
    mixed_case = "".join(random.choice([k.upper(), k.lower()]) for k in cmd)
    variations.append(mixed_case)

    # 2. Caret Obfuscation for CMD (c^m^d.e^x^e)
    caret_cmd = ""
    for char in cmd:
        caret_cmd += char + ("^" if char.isalpha() and random.random() > 0.5 else "")
    variations.append(caret_cmd)

    # 3. PowerShell Backtick Obfuscation (p`o`w`e`r`s`h`e`l`l)
    tick_cmd = ""
    for char in cmd:
        tick_cmd += char + ("`" if char.isalpha() and random.random() > 0.5 else "")
    variations.append(tick_cmd)

    return variations


def augment_malicious_data(base_malicious_data):
    print("[*] Augmenting dataset with evasive command obfuscation...")
    augmented_data = list(base_malicious_data)  # Keep the originals

    for cmd, label, mitre_id in base_malicious_data:
        # Generate 3 obfuscated variations for every 1 base command
        for obfuscated in obfuscate_command(cmd):
            augmented_data.append((obfuscated, label, mitre_id))

    print(
        f"[+] Expanded dataset from {len(base_malicious_data)} to {len(augmented_data)} malicious payloads via augmentation.")
    return augmented_data


# --- 3. DATASET BALANCING ---

def generate_benign_noise(target_count):
    print("[*] Generating an equal amount of benign Windows noise to balance the AI...")
    base_commands = [
        "powershell.exe -ExecutionPolicy Restricted -Command Get-Process",
        "cmd.exe /c echo %USERNAME%",
        "C:\\Windows\\System32\\svchost.exe -k netsvcs -p -s Schedule",
        "python.exe c:\\Users\\amita\\PycharmProjects\\PythonProject11\\main.py",
        "ping 8.8.8.8 -n 4",
        "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        "C:\\Windows\\Explorer.EXE",
        "tasklist /v",
        "ipconfig /flushdns"
    ]

    benign_commands = []
    for _ in range(target_count // len(base_commands) + 1):
        for cmd in base_commands:
            # We don't augment benign commands. Normal laptops don't use backtick obfuscation!
            benign_commands.append((cmd, 0, "None"))

    return benign_commands[:target_count]


# --- 4. MASTER COMPILATION ---

def build_master_dataset():
    # Gather Intelligence
    art = fetch_atomic_red_team()
    lolbas = fetch_lolbas_project()
    patt = fetch_payloads_all_the_things()

    # Combine & Augment
    raw_malicious = art + lolbas + patt
    massive_malicious_dataset = augment_malicious_data(raw_malicious)

    # Balance & Save
    benign_dataset = generate_benign_noise(len(massive_malicious_dataset))
    full_dataset = massive_malicious_dataset + benign_dataset
    random.shuffle(full_dataset)

    with open('mitre_commands.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Command', 'Label', 'MITRE_ID'])
        writer.writerows(full_dataset)

    print(f"\n[+] ENTERPRISE DATASET READY: 'mitre_commands.csv' generated with {len(full_dataset)} total rows.")
    print("[*] Start your PyTorch training script immediately.")


if __name__ == "__main__":
    build_master_dataset()