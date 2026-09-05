"""
스마트 교실 비전 AI 클라이언트 (Windows PC).
초경량 ONNX 추론 엔진(ONNXRuntime / OpenCV DNN 듀얼 지원)과 한글 폰트 UI 오버레이를 탑재하여
사람 검출, 6석 좌석 ROI 모니터링, 출입 얼굴 인증 및 화재 경보 시뮬레이션을 수행합니다.

규격 준수:
- .agents/rules/vision-rules.md
- .agents/skills/vision-recognition-integration/SKILL.md
"""

import os
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

import cv2
from dotenv import load_dotenv
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import requests

# .env 로드
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
DEVICE_API_KEY = os.getenv("DEVICE_API_KEY", "CLASS_2026_09_05_v1_0_0")
CAMERA_INDEX = int(os.getenv("CAMERA_INDEX", "0"))
MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "yolov8n.onnx")


class YOLOv8ONNXDetector:
    """
    초경량 YOLOv8 ONNX 추론 엔진.
    1순위: ONNXRuntime (CPU 고속 최적화)
    2순위: OpenCV 내장 DNN (DLL 의존성 제로 2중 안전장치)
    """

    def __init__(self, model_path: str, conf_thresh: float = 0.45, iou_thresh: float = 0.45):
        self.model_path = model_path
        self.conf_thresh = conf_thresh
        self.iou_thresh = iou_thresh
        self.engine_name = "None"
        self.session = None
        self.net = None
        self.input_shape = (640, 640)

        if not os.path.exists(model_path):
            print(f"[Vision/ONNX] Error: Model file not found: {model_path}")
            return

        # 1. ONNXRuntime 시도
        try:
            import onnxruntime as ort

            opts = ort.SessionOptions()
            opts.intra_op_num_threads = 4
            opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            self.session = ort.InferenceSession(
                model_path, sess_options=opts, providers=["CPUExecutionProvider"]
            )
            self.input_name = self.session.get_inputs()[0].name
            self.engine_name = "ONNXRuntime"
            print(f"[Vision/ONNX] Loaded with {self.engine_name} successfully.")
            return
        except Exception as exc:
            print(f"[Vision/ONNX] ONNXRuntime load failed ({exc}). Falling back to cv2.dnn...")

        # 2. cv2.dnn 폴백
        try:
            self.net = cv2.dnn.readNetFromONNX(model_path)
            try:
                self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
                self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
            except Exception:
                pass
            self.engine_name = "OpenCV DNN"
            print(f"[Vision/ONNX] Loaded with {self.engine_name} fallback successfully.")
        except Exception as exc:
            print(f"[Vision/ONNX] cv2.dnn load failed: {exc}")
            self.engine_name = "Failed"

    def _letterbox(self, im: np.ndarray) -> Tuple[np.ndarray, float, Tuple[float, float]]:
        shape = im.shape[:2]
        new_shape = self.input_shape
        r = min(new_shape[0] / shape[0], new_shape[1] / shape[1])
        new_unpad = int(round(shape[1] * r)), int(round(shape[0] * r))
        dw, dh = new_shape[1] - new_unpad[0], new_shape[0] - new_unpad[1]
        dw /= 2
        dh /= 2

        if shape[::-1] != new_unpad:
            im = cv2.resize(im, new_unpad, interpolation=cv2.INTER_LINEAR)
        top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
        left, right = int(round(dw - 0.1)), int(round(dw + 0.1))
        im = cv2.copyMakeBorder(im, top, bottom, left, right, cv2.BORDER_CONSTANT, value=(114, 114, 114))
        return im, r, (dw, dh)

    def detect_persons(self, frame: np.ndarray) -> List[Tuple[int, int, int, int, float]]:
        """
        프레임에서 '사람(person, class_id=0)' 객체를 감지하여 [(x1, y1, x2, y2, conf), ...] 목록을 반환합니다.
        """
        if self.engine_name not in ("ONNXRuntime", "OpenCV DNN"):
            return []

        h_orig, w_orig = frame.shape[:2]
        letterboxed, r, (dw, dh) = self._letterbox(frame)

        # 전처리: BGR -> RGB, HWC -> CHW, 정규화 0~1
        blob = cv2.cvtColor(letterboxed, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        blob = np.transpose(blob, (2, 0, 1))
        blob = np.expand_dims(blob, axis=0)  # (1, 3, 640, 640)

        # 추론
        preds = None
        if self.engine_name == "ONNXRuntime":
            preds = self.session.run(None, {self.input_name: blob})[0]
        else:
            self.net.setInput(blob)
            preds = self.net.forward()

        # 출력 형태 파싱: (1, 84, 8400) -> (8400, 84)
        if preds.shape[1] == 84:
            preds = np.transpose(preds[0], (1, 0))  # (8400, 84)
        elif preds.shape[2] == 84:
            preds = preds[0]

        boxes = []
        confidences = []

        # YOLOv8 COCO class 0 = person
        for row in preds:
            person_score = float(row[4])
            if person_score >= self.conf_thresh:
                cx, cy, w, h = float(row[0]), float(row[1]), float(row[2]), float(row[3])
                # letterbox 좌표를 원본 프레임 좌표로 역산
                x1 = int((cx - w / 2 - dw) / r)
                y1 = int((cy - h / 2 - dh) / r)
                x2 = int((cx + w / 2 - dw) / r)
                y2 = int((cy + h / 2 - dh) / r)

                # 클리핑
                x1 = max(0, min(w_orig, x1))
                y1 = max(0, min(h_orig, y1))
                x2 = max(0, min(w_orig, x2))
                y2 = max(0, min(h_orig, y2))

                boxes.append([x1, y1, x2 - x1, y2 - y1])
                confidences.append(person_score)

        if not boxes:
            return []

        indices = cv2.dnn.NMSBoxes(boxes, confidences, self.conf_thresh, self.iou_thresh)
        results = []
        if len(indices) > 0:
            for idx in np.array(indices).flatten():
                x, y, w, h = boxes[idx]
                results.append((x, y, x + w, y + h, confidences[idx]))
        return results


def put_korean_text(
    img: np.ndarray,
    text: str,
    org: Tuple[int, int],
    font_size: int = 16,
    color: Tuple[int, int, int] = (255, 255, 255),
    bg_color: Optional[Tuple[int, int, int]] = None,
) -> np.ndarray:
    """
    OpenCV 영상 프레임에 한글 텍스트를 깨짐 없이 선명하게 렌더링합니다.
    """
    img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(img_pil)

    font = None
    font_candidates = [
        "malgun.ttf",  # Windows 맑은 고딕
        "gulim.ttc",   # Windows 굴림
        "batang.ttc",  # Windows 바탕
        "C:\\Windows\\Fonts\\malgun.ttf",
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    ]
    for fc in font_candidates:
        try:
            font = ImageFont.truetype(fc, font_size)
            break
        except Exception:
            continue
    if font is None:
        font = ImageFont.load_default()

    x, y = org
    if bg_color is not None:
        bbox = draw.textbbox((x, y), text, font=font)
        # 패딩 추가
        draw.rectangle([bbox[0] - 3, bbox[1] - 2, bbox[2] + 3, bbox[3] + 2], fill=bg_color)

    draw.text((x, y), text, font=font, fill=color)
    return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)


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
        print(f"[Vision] Event '{event_type}' sent -> HTTP {resp.status_code}")
        return resp.status_code
    except Exception as exc:
        print(f"[Vision] Failed to send event '{event_type}': {exc}")
        return None


def main() -> None:
    print("=" * 70)
    print(" 🏫 Smart Classroom Vision Client (초경량 ONNX 엔진 탑재)")
    print(f" 백엔드 주소: {BACKEND_URL}")
    print(f" 디바이스 키: {DEVICE_API_KEY[:4]}****")
    print("=" * 70)

    # 1. 초경량 ONNX 감지 모델 로드
    detector = YOLOv8ONNXDetector(MODEL_PATH)
    print(f"[Vision] 추론 엔진: {detector.engine_name}")

    # 2. 웹캠 연결 (Windows CAP_DSHOW)
    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
    webcam_available = cap.isOpened()
    if webcam_available:
        print(f"[Vision] 웹캠 연결 완료 (포트 {CAMERA_INDEX}, CAP_DSHOW)")
    else:
        print(f"[Vision] 웹캠 미연결(포트 {CAMERA_INDEX}) -> 가상 교실 프레임 캔버스로 실행합니다.")

    window_name = "Smart Classroom Vision Client (Q: 종료)"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 960, 540)

    # 6개 좌석 ROI 영역 (640x480 프레임 기준: 가로 3열 x 세로 2행)
    seat_rois = {
        1: ((50, 80), (220, 220)),
        2: ((240, 80), (410, 220)),
        3: ((430, 80), (600, 220)),
        4: ((50, 260), (220, 400)),
        5: ((240, 260), (410, 400)),
        6: ((430, 260), (600, 400)),
    }
    # 각 좌석 상태: "AVAILABLE", "OCCUPIED", "MISMATCH"
    seat_states = {i: "AVAILABLE" for i in range(1, 7)}

    last_person_count = -1
    last_status_msg = "준비 완료. 아래 단축키를 눌러 시뮬레이션을 테스트하세요."
    last_send_time = 0.0
    flame_sim_active = False

    print("\n[단축키 조작 안내]")
    print("  [E] 학생 출입 인증 (얼굴 인식 성공 -> 서보문 OPEN + 릴레이 조명 ON + 출석)")
    print("  [U] 미등록자 인증 실패 (부저 경고음 작동)")
    print("  [1~6] 좌석 1~6번 착석 상태 순환 (빈좌석 -> 착석 -> 좌석불일치)")
    print("  [F] 불꽃 센서 화재 감지 경보 토글")
    print("  [Q] 비전 클라이언트 종료\n")

    while True:
        if webcam_available:
            ok, frame = cap.read()
            if not ok:
                frame = np.zeros((480, 640, 3), dtype=np.uint8)
        else:
            # 가상 교실 프레임 캔버스
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            frame[:] = (32, 32, 38)

        # 3. 초경량 ONNX 사람 감지
        person_boxes = []
        if detector.engine_name != "None":
            try:
                person_boxes = detector.detect_persons(frame)
            except Exception as exc:
                pass

        person_count = len(person_boxes)
        max_conf = max([p[4] for p in person_boxes], default=0.0)

        # 감지된 사람 바운딩 박스 그리기
        for (x1, y1, x2, y2, conf) in person_boxes:
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 230, 110), 2)
            frame = put_korean_text(
                frame,
                f"사람 {conf * 100:.0f}%",
                (x1, max(10, y1 - 22)),
                font_size=14,
                color=(255, 255, 255),
                bg_color=(0, 140, 60),
            )

        # 인원수 변경 감지 시 백엔드 전송 (디바운스 2초)
        curr_time = time.time()
        if webcam_available and person_count != last_person_count and (curr_time - last_send_time > 2.0):
            send_vision_event(
                event_type="person_detected",
                detected=(person_count > 0),
                count=person_count,
                confidence=max_conf if person_count > 0 else 0.0,
                details={"source": "classroom_cam", "persons": person_count},
            )
            last_person_count = person_count
            last_send_time = curr_time
            last_status_msg = f"교실 재실 인원 변동: {person_count}명 감지됨"

        # 4. 6개 좌석 ROI 오버레이
        for s_id, (pt1, pt2) in seat_rois.items():
            s_status = seat_states[s_id]
            if s_status == "OCCUPIED":
                box_color = (0, 200, 80)     # 초록 (정상 착석)
                label_text = f"{s_id}번 좌석: 착석"
                bg_label = (0, 120, 40)
            elif s_status == "MISMATCH":
                box_color = (0, 60, 240)     # 빨강 (좌석 불일치 경고)
                label_text = f"{s_id}번 좌석: 불일치(경고)"
                bg_label = (0, 30, 160)
            else:
                box_color = (130, 130, 140)  # 회색 (빈 좌석)
                label_text = f"{s_id}번 좌석: 빈 좌석"
                bg_label = (60, 60, 65)

            cv2.rectangle(frame, pt1, pt2, box_color, 2)
            frame = put_korean_text(
                frame,
                label_text,
                (pt1[0] + 6, pt1[1] + 8),
                font_size=15,
                color=(255, 255, 255),
                bg_color=bg_label,
            )

        # 5. 상단 헤더 & 하단 상태 바 (반투명 오버레이)
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (640, 52), (18, 18, 24), -1)
        cv2.rectangle(overlay, (0, 426), (640, 480), (18, 18, 24), -1)
        cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)

        # 상단 타이틀 및 상태
        header_text = f"스마트 교실 비전 AI  |  재실: {person_count}명  |  엔진: {detector.engine_name}"
        frame = put_korean_text(frame, header_text, (12, 14), font_size=16, color=(255, 255, 255))

        # 하단 상태 메시지 및 단축키 안내
        frame = put_korean_text(
            frame,
            f"상태: {last_status_msg}",
            (12, 432),
            font_size=14,
            color=(0, 230, 255),
        )
        frame = put_korean_text(
            frame,
            "[E] 입실인증  [U] 인증실패  [1~6] 좌석토글  [F] 화재경보  [Q] 종료",
            (12, 456),
            font_size=13,
            color=(190, 190, 200),
        )

        cv2.imshow(window_name, frame)

        # 키보드 이벤트 처리 (30ms 대기)
        key = cv2.waitKey(30) & 0xFF
        if key == ord("q") or key == ord("Q") or key == 27:
            print("[Vision] 비전 클라이언트를 종료합니다.")
            break

        # [E] 학생 출입 인증 (얼굴 인식 성공)
        elif key == ord("e") or key == ord("E"):
            student_id = "202601"
            student_name = "김재민"
            send_vision_event(
                event_type="face_recognized",
                detected=True,
                count=1,
                confidence=0.96,
                details={"student_id": student_id, "student_name": student_name, "gate": "entrance"},
            )
            last_status_msg = f"학생 {student_name}({student_id}) 입실 완료! (자동문 OPEN 5초 + 조명 점등)"

        # [U] 미등록자 인증 실패
        elif key == ord("u") or key == ord("U"):
            send_vision_event(
                event_type="face_unrecognized",
                detected=False,
                count=1,
                confidence=0.35,
                details={"reason": "Face match threshold not met"},
            )
            last_status_msg = "미등록자 얼굴 인증 실패! (부저 경고음 작동)"

        # [1~6] 좌석 착석 상태 순환 토글
        elif ord("1") <= key <= ord("6"):
            s_num = key - ord("0")
            curr = seat_states[s_num]
            next_state = "OCCUPIED" if curr == "AVAILABLE" else ("MISMATCH" if curr == "OCCUPIED" else "AVAILABLE")
            seat_states[s_num] = next_state

            send_vision_event(
                event_type="seat_status",
                detected=(next_state != "AVAILABLE"),
                count=1,
                confidence=0.92,
                details={"seat_id": s_num, "status": next_state},
            )
            state_kr = "착석" if next_state == "OCCUPIED" else ("좌석 불일치" if next_state == "MISMATCH" else "빈 좌석")
            last_status_msg = f"{s_num}번 좌석 상태 변경 -> {state_kr}({next_state})"

        # [F] 불꽃 감지 화재 경보
        elif key == ord("f") or key == ord("F"):
            flame_sim_active = not flame_sim_active
            send_vision_event(
                event_type="flame_detected",
                detected=flame_sim_active,
                count=1 if flame_sim_active else 0,
                confidence=0.99,
                details={"flame_active": flame_sim_active},
            )
            last_status_msg = f"화재 경보: {'[발생] 부저 비상 경보 작동!' if flame_sim_active else '[해제] 정상 복구'}"

    if cap.isOpened():
        cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
