import cv2
import face_recognition
import time
import os
import math


def euclidean_dist(pt1, pt2):
    return math.sqrt((pt1[0] - pt2[0]) ** 2 + (pt1[1] - pt2[1]) ** 2)


def eye_aspect_ratio(eye):
    A = euclidean_dist(eye[1], eye[5])
    B = euclidean_dist(eye[2], eye[4])
    C = euclidean_dist(eye[0], eye[3])
    return (A + B) / (2.0 * C)


def enhance_low_light(rgb_image):
    """Acts as digital night-vision by pulling facial details out of shadows."""
    # Convert RGB to LAB Color Space (Lightness, A-color, B-color)
    lab = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2LAB)
    l, a, b = cv2.split(lab)

    # Apply Contrast Limited Adaptive Histogram Equalization to the Lightness channel
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    cl = clahe.apply(l)

    # Merge back together
    limg = cv2.merge((cl, a, b))
    return cv2.cvtColor(limg, cv2.COLOR_LAB2RGB)


def debug_liveness_engine(timeout_seconds=20):
    print("\n[*] WAKING VISUAL DEBUG MODE (WITH NIGHT-VISION)...")

    image_path = "AMIT.jpg"
    if not os.path.exists(image_path):
        print("[!] FATAL ERROR: 'owner.jpg' not found!")
        return False

    raw_image = cv2.imread(image_path)
    owner_image = cv2.cvtColor(raw_image, cv2.COLOR_BGR2RGB)
    owner_encoding = face_recognition.face_encodings(owner_image)[0]

    cap = cv2.VideoCapture(0)
    start_time = time.time()

    EAR_THRESHOLD = 0.22
    blink_counter = 0
    has_blinked = False

    print("[*] LOOK AT THE CAMERA. Check the terminal for your Eye Aspect Ratio (EAR) math.")

    while time.time() - start_time < timeout_seconds:
        success, frame = cap.read()
        if not success:
            continue

        # Convert to RGB and APPLY NIGHT-VISION ENHANCEMENT
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb_frame = enhance_low_light(rgb_frame)

        # Convert back to BGR just so OpenCV can display the enhanced version to you on screen
        display_frame = cv2.cvtColor(rgb_frame, cv2.COLOR_RGB2BGR)
        cv2.imshow("OmniGuard Night-Vision Debug", display_frame)
        cv2.waitKey(1)

        face_locations = face_recognition.face_locations(rgb_frame)
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
        face_landmarks_list = face_recognition.face_landmarks(rgb_frame, face_locations)

        if not face_locations:
            print("[-] No face detected (Check lighting/distance)")

        for live_encoding, face_landmarks in zip(face_encodings, face_landmarks_list):

            matches = face_recognition.compare_faces([owner_encoding], live_encoding, tolerance=0.65)
            is_match = matches[0]

            left_eye = face_landmarks['left_eye']
            right_eye = face_landmarks['right_eye']
            ear = (eye_aspect_ratio(left_eye) + eye_aspect_ratio(right_eye)) / 2.0

            match_status = "MATCH" if is_match else "MISMATCH"
            print(f"Live EAR: {ear:.3f} | Target: < {EAR_THRESHOLD} | Identity: {match_status}")

            if ear < EAR_THRESHOLD:
                blink_counter += 1
            else:
                if blink_counter >= 2:
                    has_blinked = True
                blink_counter = 0

            if is_match and has_blinked:
                print("\n[+] DEBUG SUCCESS: AUTHORIZED OWNER MATCHED & BLINK CONFIRMED!")
                cap.release()
                cv2.destroyAllWindows()
                return True

    cap.release()
    cv2.destroyAllWindows()
    return False


if __name__ == "__main__":
    debug_liveness_engine()