"""
Vision Client for Smart Classroom System (Windows PC).
Uses YOLOv8 for real-time person detection, seat ROI monitoring, and interactive test simulation.
Compliant with .agents/rules/vision-rules.md and .agents/skills/vision-recognition-integration/SKILL.md.
"""

import os
import sys
import time
from typing import Any, Dict, List, Optional
import cv2
from dotenv import load_dotenv
import numpy as np
import requests

# .env 로드
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
DEVICE_API_KEY = os.getenv("DEVICE_API_KEY", "CLASS_2026_09_05_v1_0_0")
CAMERA_INDEX = int(os.getenv("CAMERA_INDEX", "0"))

MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "yolov8n.pt")


def send_vision_event(
    event_type: str,
    detected: bool = True,
    count: int = 0,
    confidence: Optional[float] = None,
    details: Optional[Dict[str, Any]] = None,
) -> Optional[int]:
    """
    백엔드로 영상인식 감지 이벤트를 전송합니다 (X-Device-Api-Key 인증).
    """
    url = f"{BACKEND_URL}/api/v1/vision/events"
    headers = {
        "X-Device-Api-Key": DEVICE_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "event_type": event_type,
        "detected": detected,
        "count": count,
        "confidence": confidence,
        "details": details or {},
    }
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=2.0)
        print(f"[Vision] Sent event '{event_type}' -> Status {resp.status_code}")
        return resp.status_code
    except Exception as exc:
        print(f"[Vision] Failed to send event '{event_type}': {exc}")
        return None


def main() -> None:
    print("=" * 70)
    print(" Smart Classroom Vision Client (Windows PC)")
    print(f" Backend URL: {BACKEND_URL}")
    print(f" Device Key:  {DEVICE_API_KEY[:4]}****")
    print("=" * 70)

    # 1. YOLO 모델 로드
    yolo_model = None
    if os.path.exists(MODEL_PATH):
        try:
            from ultralytics import YOLO
            print(f"[Vision] Loading YOLOv8 model from {MODEL_PATH}...")
            yolo_model = YOLO(MODEL_PATH)
            print("[Vision] YOLOv8 model loaded successfully.")
        except Exception as exc:
            print(f"[Vision] Warning: Ultralytics YOLO load failed: {exc}")
    else:
        print(f"[Vision] Warning: '{MODEL_PATH}' not found. Running in simulation mode.")

    # 2. 웹캠 열기 (Windows에서는 CAP_DSHOW 권장)
    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
    webcam_available = cap.isOpened()
    if webcam_available:
        print(f"[Vision] Webcam connected on index {CAMERA_INDEX} (CAP_DSHOW).")
    else:
        print(f"[Vision] Webcam not found on index {CAMERA_INDEX}. Virtual feed will be used.")

    window_name = "Smart Classroom Vision Client (Press 'Q' to quit)"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 960, 540)

    # 6개 좌석 ROI 영역 (640x480 프레임 기준: 가로 3개 x 세로 2개 열)
    seat_rois = {
        1: ((50, 80), (220, 220)),
        2: ((240, 80), (410, 220)),
        3: ((430, 80), (600, 220)),
        4: ((50, 260), (220, 400)),
        5: ((240, 260), (410, 400)),
        6: ((430, 260), (600, 400)),
    }
    # 각 좌석 현재 시뮬레이션 상태: "AVAILABLE", "OCCUPIED", "MISMATCH"
    seat_states = {i: "AVAILABLE" for i in range(1, 7)}

    last_person_count = -1
    last_status_msg = "Ready. Press keys below to test triggers."
    last_send_time = 0.0

    print("\n[Controls 안내]")
    print("  [E] 학생 출입 인증 (얼굴 인식 성공 -> 서보문 OPEN + 릴레이 조명 ON + 출석)")
    print("  [U] 미등록자 인증 실패 (부저 경고음 작동)")
    print("  [1~6] 좌석 1~6번 착석 상태 순환 토글 (EMPTY -> OCCUPIED -> MISMATCH)")
    print("  [F] 불꽃 센서 화재 감지 경보 토글")
    print("  [Q] 프로그램 종료\n")

    flame_sim_active = False

    while True:
        if webcam_available:
            ok, frame = cap.read()
            if not ok:
                frame = np.zeros((480, 640, 3), dtype=np.uint8)
        else:
            # 가상 교실 프레임 캔버스 생성
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            frame[:] = (30, 30, 35)

        # 3. YOLOv8 사람 감지 (Webcam 및 모델 사용 가능 시)
        person_count = 0
        conf_val = 0.0
        if yolo_model is not None and webcam_available:
            try:
                results = yolo_model(frame, classes=[0], verbose=False)
                boxes = results[0].boxes
                person_count = len(boxes)
                for box in boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    conf_val = float(box.conf[0])
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 120), 2)
                    cv2.putText(frame, f"Person {conf_val:.2f}", (x1, max(20, y1 - 5)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 120), 1)
            except Exception as exc:
                pass

        # 인원 수 변화 시에만 백엔드 전송 (vision-rules.md 준수: 매 프레임 전송 방지)
        curr_time = time.time()
        if webcam_available and person_count != last_person_count and (curr_time - last_send_time > 2.0):
            send_vision_event(
                event_type="person_detected",
                detected=(person_count > 0),
                count=person_count,
                confidence=conf_val if person_count > 0 else 0.0,
                details={"source": "classroom_cam", "persons": person_count}
            )
            last_person_count = person_count
            last_send_time = curr_time
            last_status_msg = f"Person detected count changed: {person_count}"

        # 4. 6개 좌석 ROI 오버레이 그리기
        for s_id, (pt1, pt2) in seat_rois.items():
            s_status = seat_states[s_id]
            if s_status == "OCCUPIED":
                color = (0, 200, 0)      # 초록
            elif s_status == "MISMATCH":
                color = (0, 0, 240)      # 빨강
            else:
                color = (120, 120, 120)  # 회색

            cv2.rectangle(frame, pt1, pt2, color, 2)
            cv2.putText(frame, f"Seat {s_id}: {s_status}", (pt1[0] + 5, pt1[1] + 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

        # 5. 상단 및 하단 상태/안내 텍스트 표시
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (640, 50), (15, 15, 20), -1)
        cv2.rectangle(overlay, (0, 435), (640, 480), (15, 15, 20), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

        cv2.putText(frame, f"AI Smart Classroom Vision Feed | Persons: {person_count}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(frame, f"Msg: {last_status_msg}", (10, 455),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 220, 255), 1)
        cv2.putText(frame, "[E] Entrance  [U] Auth Fail  [1-6] Seats  [F] Flame  [Q] Quit", (10, 473),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (180, 180, 180), 1)

        cv2.imshow(window_name, frame)

        # 키보드 이벤트 처리 (30ms 대기)
        key = cv2.waitKey(30) & 0xFF
        if key == ord('q') or key == ord('Q') or key == 27:  # 27 = ESC
            print("[Vision] Quitting...")
            break

        # [E] 학생 출입 인증 (얼굴 인식 성공)
        elif key == ord('e') or key == ord('E'):
            student_id = "202601"
            student_name = "김재민"
            status_code = send_vision_event(
                event_type="face_recognized",
                detected=True,
                count=1,
                confidence=0.96,
                details={"student_id": student_id, "student_name": student_name, "gate": "entrance"}
            )
            last_status_msg = f"Trigger: Student {student_name} entered! (Door OPEN 5s, Light ON)"

        # [U] 미등록자 인증 실패
        elif key == ord('u') or key == ord('U'):
            status_code = send_vision_event(
                event_type="face_unrecognized",
                detected=False,
                count=1,
                confidence=0.35,
                details={"reason": "Face match threshold not met"}
            )
            last_status_msg = "Trigger: Face Auth Failed! (Buzzer Beep)"

        # [1~6] 좌석 착석 상태 토글
        elif ord('1') <= key <= ord('6'):
            s_num = key - ord('0')
            curr = seat_states[s_num]
            # AVAILABLE -> OCCUPIED -> MISMATCH -> AVAILABLE
            next_state = "OCCUPIED" if curr == "AVAILABLE" else ("MISMATCH" if curr == "OCCUPIED" else "EMPTY")
            seat_states[s_num] = "AVAILABLE" if next_state == "EMPTY" else next_state

            send_vision_event(
                event_type="seat_status",
                detected=(next_state != "EMPTY"),
                count=1,
                confidence=0.92,
                details={"seat_id": s_num, "status": next_state}
            )
            last_status_msg = f"Seat {s_num} set to {next_state}"

        # [F] 불꽃 감지 화재 경보
        elif key == ord('f') or key == ord('F'):
            flame_sim_active = not flame_sim_active
            send_vision_event(
                event_type="flame_detected",
                detected=flame_sim_active,
                count=1 if flame_sim_active else 0,
                confidence=0.99,
                details={"flame_active": flame_sim_active}
            )
            last_status_msg = f"Flame Alert: {'ACTIVE (Buzzer Alert!)' if flame_sim_active else 'CLEARED'}"

    if cap.isOpened():
        cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
