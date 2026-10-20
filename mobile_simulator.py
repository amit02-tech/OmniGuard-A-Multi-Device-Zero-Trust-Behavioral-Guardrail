import asyncio
import websockets
import json
import base64
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

# 1. Load the Mobile Private Key
try:
    with open("mobile_private.pem", "rb") as key_file:
        private_key = serialization.load_pem_private_key(
            key_file.read(),
            password=None
        )
except FileNotFoundError:
    print("[-] Error: mobile_private.pem not found. Run generate_keys.py first.")
    exit(1)


async def mobile_client():
    uri = "ws://localhost:8000/ws/mobile"
    print(f"[*] Connecting to Secure Relay at {uri}...")

    async with websockets.connect(uri) as websocket:
        print("[+] Connected! Mobile Authenticator is actively listening for threats...")

        while True:
            # 2. Receive the threat payload from the Relay
            message = await websocket.recv()
            payload = json.loads(message)

            print("\n" + "=" * 70)
            if payload.get('biometrics_passed'):
                print(f"[+] NORMAL 2FA ALERT: Mr. Amit detected at keyboard.")
            else:
                print(f"[!!!] CRITICAL INTRUSION ALERT: UNAUTHORIZED USER AT LAPTOP [!!!]")

            print(f"[*] Process : {payload.get('process')} (PID: {payload.get('pid')})")
            print(f"[*] Command : {payload.get('command')}")
            print("=" * 70)

            # 3. Simulate the user tapping "Approve" or "Deny" on their phone screen
            decision = input("\n[?] Do you authorize this execution? (y/n): ").strip().lower()
            action = "APPROVE" if decision == 'y' else "DENY"

            # 4. Cryptographically sign the action + PID to prevent replay attacks
            message_to_sign = f"{action}:{payload['pid']}".encode('utf-8')
            signature = private_key.sign(message_to_sign)

            # Encode signature to Base64 so it can be transmitted via JSON
            signature_b64 = base64.b64encode(signature).decode('utf-8')

            response_payload = {
                "pid": payload['pid'],
                "action": action,
                "signature": signature_b64
            }

            print(f"[*] Signing decision '{action}' with Ed25519 Private Key...")
            await websocket.send(json.dumps(response_payload))
            print("[+] Cryptographically signed verdict sent back to EDR Daemon.")


if __name__ == "__main__":
    asyncio.run(mobile_client())