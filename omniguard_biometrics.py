import os
import time
import cv2
import numpy as np
from scipy.spatial import distance as dist
import face_recognition

# Standard, clean MediaPipe initialization
import mediapipe as mp
mp_face_mesh = mp.solutions.face_mesh
mp_drawing = mp.solutions.drawing_utils
BASELINE_IMAGE_PATH = "AMITT.jpg"

if not os.path.exists(BASELINE_IMAGE_PATH):
    raise FileNotFoundError(f"[!] Critical: Please place '{BASELINE_IMAGE_PATH}' in the project directory.")

print("[*] OmniGuard Biometric Vault: Generating 128-d baseline encodings...")
baseline_image = face_recognition.load_image_file(BASELINE_IMAGE_PATH)

# NEW: Dynamically scale down massive high-res photos to prevent dlib C++ Memory crashes
h, w = baseline_image.shape[:2]
if w > 800:
    ratio = 800.0 / w
    new_h = int(h * ratio)
    baseline_image = cv2.resize(baseline_image, (800, new_h))
    print(f"[*] Image scaled down to 800x{new_h} to optimize memory allocation.")

try:
    ADMIN_ENCODING = face_recognition.face_encodings(baseline_image)[0]
    print("[+] Admin identity encoding successfully mapped to RAM.")
except IndexError:
    raise ValueError("[!] Could not detect a face in the baseline image. Please use a clearer photo.")
# --- 2. MEDIA-PIPE INITIALIZATION ---

    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7


LEFT_EYE = [362, 385, 387, 263, 373, 380]
RIGHT_EYE = [33, 160, 158, 133, 153, 144]
EAR_THRESHOLD = 0.21
CONSECUTIVE_FRAMES = 2


def calculate_ear(eye_landmarks):
    v1 = dist.euclidean(eye_landmarks[1], eye_landmarks[5])
    v2 = dist.euclidean(eye_landmarks[2], eye_landmarks[4])
    h1 = dist.euclidean(eye_landmarks[0], eye_landmarks[3])
    return (v1 + v2) / (2.0 * h1)


def extract_landmarks(face_landmarks, indices, img_w, img_h):
    return np.array([
        [int(face_landmarks.landmark[i].x * img_w),
         int(face_landmarks.landmark[i].y * img_h)]
        for i in indices
    ])


def verify_biometrics(timeout_seconds=15):
    # ADD THIS LINE: Initialize the MediaPipe Face Mesh AI model
    face_mesh = mp_face_mesh.FaceMesh(max_num_faces=1, min_detection_confidence=0.7, min_tracking_confidence=0.7)

    # ... your existing webcam code continues below ...

    """Requires both a physical blink (liveness) AND a mathematical 128-d identity match."""
    print("[*] OmniGuard Active: Awaiting Liveness & Identity Verification...")
    cap = cv2.VideoCapture(0)

    blink_counter = 0
    start_time = time.time()
    liveness_proven = False
    identity_verified = False

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        # --- NEW: Apply Mobile HDR (CLAHE) to the ENTIRE video feed instantly ---
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l_channel, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        cl = clahe.apply(l_channel)
        hdr_frame = cv2.cvtColor(cv2.merge((cl, a, b)), cv2.COLOR_LAB2BGR)
        # -----------------------------------------------------------------------

        # Feed the brightened HDR frame to MediaPipe for perfect blink detection in the dark
        rgb_frame = cv2.cvtColor(hdr_frame, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(rgb_frame)

        # ... (Your existing blink math/EAR calculation goes here, using 'results') ...

        if time.time() - start_time > timeout_seconds:
            print("[-] Biometric Timeout: No human presence detected.")
            break

        img_h, img_w, _ = frame.shape
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(rgb_frame)

        if results.multi_face_landmarks:
            for face_landmarks in results.multi_face_landmarks:
                left_eye_coords = extract_landmarks(face_landmarks, LEFT_EYE, img_w, img_h)
                right_eye_coords = extract_landmarks(face_landmarks, RIGHT_EYE, img_w, img_h)

                left_ear = calculate_ear(left_eye_coords)
                right_ear = calculate_ear(right_eye_coords)
                avg_ear = (left_ear + right_ear) / 2.0

                if avg_ear < EAR_THRESHOLD:
                    blink_counter += 1
                else:
                    if blink_counter >= CONSECUTIVE_FRAMES:
                        print("\n[+] Liveness Confirmed! (Blink registered)")
                        print("[*] Extracting 128-d live facial embedding...")

                        # --- NEW: Stabilized Identity Retry Loop ---
                        # --- NEW: Stabilized Identity Retry Loop with Anti-Backlight ---
                        live_encodings = []
                        # --- NEW: Mobile ISP Architecture (Deep Learning ROI + CLAHE) ---
                        live_encodings = []
                        for _ in range(15):
                            ret, fresh_frame = cap.read()
                            if not ret:
                                continue

                            # 1. Ask MediaPipe (CNN) to find the face bounding box in the shadows
                            results = face_mesh.process(cv2.cvtColor(fresh_frame, cv2.COLOR_BGR2RGB))
                            if not results.multi_face_landmarks:
                                continue

                            # Extract the bounding box coordinates from MediaPipe's mesh
                            landmarks = results.multi_face_landmarks[0].landmark
                            h, w, _ = fresh_frame.shape
                            x_min = int(min([lm.x for lm in landmarks]) * w)
                            y_min = int(min([lm.y for lm in landmarks]) * h)
                            x_max = int(max([lm.x for lm in landmarks]) * w)
                            y_max = int(max([lm.y for lm in landmarks]) * h)

                            # Convert to dlib's required format: (top, right, bottom, left)
                            # We expand the box slightly to ensure the whole chin/hairline is caught
                            top, right, bottom, left = max(0, y_min - 20), min(w, x_max + 20), min(h, y_max + 20), max(
                                0, x_min - 20)
                            mobile_roi_box = [(top, right, bottom, left)]

                            # 2. Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
                            # This is exactly how mobile HDR algorithms pull faces out of shadows
                            lab = cv2.cvtColor(fresh_frame, cv2.COLOR_BGR2LAB)
                            l_channel, a, b = cv2.split(lab)
                            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
                            cl = clahe.apply(l_channel)
                            merged = cv2.merge((cl, a, b))
                            hdr_frame = cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)

                            # 3. Force-feed the MediaPipe box to dlib so it bypasses HOG entirely
                            rgb_hdr = cv2.cvtColor(hdr_frame, cv2.COLOR_BGR2RGB)
                            live_encodings = face_recognition.face_encodings(rgb_hdr,
                                                                             known_face_locations=mobile_roi_box)

                            if live_encodings:
                                break
                                # ----------------------------------------------------------------
                        # --------------------------------------------------------------- # Successfully grabbed a perfect, clear extraction!
                        # -------------------------------------------

                        if not live_encodings:
                            print("[-] IDENTITY REJECTED: Could not extract facial features. Ensure good lighting.")
                            cap.release()
                            cv2.destroyAllWindows()
                            return False

                        # Compare the fresh, clear snapshot to your baseline
                        live_encoding = live_encodings[0]

                        # NOTE: tolerance=0.6 is the standard. If it still rejects you, increase this slightly (e.g., 0.65)
                        matches = face_recognition.compare_faces([ADMIN_ENCODING], live_encoding, tolerance=0.6)

                        if matches[0]:
                            print("[+] IDENTITY VERIFIED: Admin access granted.")
                            cap.release()
                            cv2.destroyAllWindows()
                            return True
                        else:
                            print("[-] IDENTITY REJECTED: Face does not match Admin baseline.")
                            cap.release()
                            cv2.destroyAllWindows()
                            return False

                cv2.polylines(frame, [left_eye_coords], True, (0, 255, 0), 1)
                cv2.polylines(frame, [right_eye_coords], True, (0, 255, 0), 1)

        cv2.imshow("OmniGuard Anti-Spoofing Vault", frame)

        # TRIGGER IDENTITY CHECK ONLY AFTER LIVENESS IS PROVEN
        if liveness_proven:
            print("[*] Extracting 128-d live facial embedding...")
            live_encodings = face_recognition.face_encodings(rgb_frame)

            if len(live_encodings) > 0:
                live_encodings = face_recognition.face_encodings(rgb_frame)

                if not live_encodings:
                    print("[*] Face not perfectly aligned for identity extraction. Retrying...")
                    continue  # <--- Skip the rest of this loop iteration and grab the next frame

                # If it successfully extracted the 128-d features, compare them:
                live_encoding = live_encodings[0]
                matches = face_recognition.compare_faces([ADMIN_ENCODING], live_encoding, tolerance=0.5)

                if matches[0]:
                    print("[+] IDENTITY VERIFIED: Admin access granted.")
                    # Clean up and return True to resume the process
                    cap.release()
                    cv2.destroyAllWindows()
                    return True
                else:
                    print("[-] IDENTITY REJECTED: Face does not match Admin baseline.")
                    cap.release()
                    cv2.destroyAllWindows()
                    return False

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    return liveness_proven and identity_verified


if __name__ == "__main__":
    access_granted = verify_biometrics()
    print("\n" + "=" * 50)
    print(
        f"KERNEL VERDICT: {'ACCESS GRANTED (Unfreeze Thread)' if access_granted else 'ACCESS DENIED (Terminate Process)'}")
    print("=" * 50 + "\n")