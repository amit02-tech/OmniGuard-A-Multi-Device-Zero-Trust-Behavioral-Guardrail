# OmniGuard: Zero-Trust EDR System
## 5-Month Master Engineering Roadmap

---

### Month 1: Core EDR & Deep System Hooking (Module 1)
**Focus:** Interception & Isolation
*   **Advanced Hooking:** Move beyond basic command-line parsing. Implement Windows API hooking via `pywin32` and `ctypes` to monitor memory injection, unauthorized registry edits, and hidden process spawning.
*   **RAM-Suspension Matrix:** Perfect the process suspension logic to freeze both parent and child processes the microsecond a behavioral anomaly is detected.
*   **State Management:** Build a bulletproof whitelist for developer tools (like PyCharm/VS Code) to achieve a near-zero false positive rate.
*   **Milestone:** A silent background daemon that successfully isolates Living-off-the-Land (LotL) attacks in system memory.

---

### Month 2: Deep Learning Anti-Spoofing CNN (Module 2)
**Focus:** Unfoolable Biometrics
*   **Dataset Curation:** Gather and label a dataset of live faces versus 2D spoofs (high-res screens, printed photos, varied lighting).
*   **PyTorch Architecture:** Train a custom Convolutional Neural Network (CNN) to analyze facial micro-textures and depth disparities, defeating presentation attacks.
*   **Low-Light Normalization:** Integrate dynamic CLAHE (Contrast Limited Adaptive Histogram Equalization) to ensure the CNN operates flawlessly in dark environments without spiking CPU usage.
*   **Milestone:** An edge-based optical engine that definitively proves a live, authorized human is physically present.

---

### Month 3: Secure Relay & Cryptographic Auth (Modules 3 & 4)
**Focus:** Out-of-Band (OOB) Verification
*   **WebSocket Tunnel:** Architect a FastAPI server secured with TLS/HTTPS to handle instantaneous, bidirectional communication over the local network.
*   **Cryptographic Keys:** Use the Python `cryptography` library to generate Ed25519 public/private key pairs.
*   **Mobile Authenticator:** Build the mobile interface to receive the threat payload (PID, Command, Timestamp). Require the mobile device to mathematically sign the "Approve/Deny" decision using its private key.
*   **Milestone:** A mathematically secure connection where the Windows daemon completely rejects unsigned network commands.

---

### Month 4: Zero-Trust Orchestration & Integration
**Focus:** The Decision Engine
*   **Pipeline Stitching:** Connect the four modules into the master Zero-Trust Decision Matrix. A RAM freeze (Module 1) must instantly trigger the biometric scan (Module 2) and the mobile payload (Modules 3/4).
*   **Fail-Safe Logic:** Implement strict fallbacks. If the camera is covered, the network drops, or the JWT token expires, the system defaults to killing the process.
*   **Audit Engine:** Build a secure local logging system to record every intercepted threat, biometric verdict, and cryptographic signature for enterprise-level tracking.
*   **Milestone:** A unified, fully communicating architecture operating as a single, cohesive application.

---

### Month 5: Red-Teaming, Optimization & Final Polish
**Focus:** Breaking and Bulletproofing
*   **Penetration Testing:** Actively attack your own system. Simulate advanced PowerShell LotL attacks, attempt local network packet sniffing, and try to bypass the CNN with an iPad video.
*   **Memory Profiling:** Profile the Python code to eliminate memory leaks and optimize the PyTorch tensor operations so OmniGuard runs silently in the background without draining laptop battery life.
*   **Live-Demo Architecture:** Finalize the deployment environment, ensuring the architecture is visually and technically ready for a flawless final B-Tech live demonstration.
*   **Milestone:** A crystal-clear, highly advanced enterprise-grade project ready for final defense.
