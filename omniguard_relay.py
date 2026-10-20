from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import json
import uvicorn

app = FastAPI(title="OmniGuard OOB Secure Relay")


# Store active connections
class ConnectionManager:
    def __init__(self):
        self.mobile_client: WebSocket = None
        self.daemon_client: WebSocket = None

    async def connect_mobile(self, websocket: WebSocket):
        await websocket.accept()
        self.mobile_client = websocket
        print("[+] Mobile Authenticator Connected via WebSocket.")

    async def connect_daemon(self, websocket: WebSocket):
        await websocket.accept()
        self.daemon_client = websocket
        print("[+] OmniGuard EDR Daemon Connected via WebSocket.")

    async def relay_to_mobile(self, payload: dict):
        if self.mobile_client:
            await self.mobile_client.send_json(payload)
        else:
            print("[-] Mobile device not connected. Cannot relay threat data.")


manager = ConnectionManager()


@app.websocket("/ws/mobile")
async def websocket_mobile(websocket: WebSocket):
    await manager.connect_mobile(websocket)
    try:
        while True:
            # Wait for the mobile device to send back a mathematically signed decision
            signed_response = await websocket.receive_text()
            print(f"[*] Received Signed Verdict from Mobile: {signed_response}")

            # Relay the decision back down to the Windows Daemon
            if manager.daemon_client:
                await manager.daemon_client.send_text(signed_response)
    except WebSocketDisconnect:
        manager.mobile_client = None
        print("[-] Mobile Authenticator Disconnected.")


@app.websocket("/ws/daemon")
async def websocket_daemon(websocket: WebSocket):
    await manager.connect_daemon(websocket)
    try:
        while True:
            # Receive threat payload from the Python EDR
            threat_data = await websocket.receive_text()
            payload = json.loads(threat_data)
            print(f"[!!!] INCOMING THREAT RELAY: {payload['process']} (PID: {payload['pid']})")

            # Push the alert to the mobile device
            await manager.relay_to_mobile(payload)
    except WebSocketDisconnect:
        manager.daemon_client = None
        print("[-] OmniGuard EDR Daemon Disconnected.")


if __name__ == "__main__":
    print("[*] Starting OmniGuard Secure Relay on port 8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000)