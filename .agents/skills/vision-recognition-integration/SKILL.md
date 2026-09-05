---
name: vision-recognition-integration
description: >-
  웹캠 기반 YOLOv8/mediapipe 영상인식 파이프라인 구성, Windows 패키지 의존성 설정 및 감지 이벤트 백엔드 전송을 구현할 때 사용하는 스킬.
---

# vision-recognition-integration

> 웹캠 영상인식(YOLO/mediapipe) 연동 작업 시 이 스킬을 참고한다.

## 패키지 설치 (초경량 ONNX 엔진 - PyTorch 설치 불필요!)
무거운 PyTorch(2.5GB)와 Ultralytics 대신 `onnxruntime`과 OpenCV 내장 DNN을 활용하여 10초 만에 설치가 완료되며, Windows DLL 충돌([WinError 1114] c10.dll)이 원천 차단됩니다.
```powershell
cd vision
# Python 3.10 ~ 3.12 (또는 최신 Python)
py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1
# requirements.txt로 초경량 설치 (ONNXRuntime, OpenCV, Pillow, Scipy 등 약 150MB)
pip install -r requirements.txt
```

## 최소 파이프라인 (초경량 YOLOv8 ONNX 듀얼 엔진 예시)
`yolov8n.onnx` 모델(12.8MB, Git 추적 포함)을 로드하여 ONNXRuntime 또는 OpenCV 내장 DNN으로 CPU 실시간 고속 추론(15~30ms)을 수행합니다.
```python
import cv2
import numpy as np

# OpenCV 내장 DNN으로 별도 컴파일러 없이 즉시 ONNX 로드 (또는 onnxruntime 사용)
net = cv2.dnn.readNetFromONNX("yolov8n.onnx")
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # Windows에서는 CAP_DSHOW 권장

while True:
    ok, frame = cap.read()
    if not ok:
        continue
    # 640x640 blob 변환 후 추론
    blob = cv2.dnn.blobFromImage(frame, 1/255.0, (640, 640), swapRB=True, crop=False)
    net.setInput(blob)
    preds = net.forward()
    # NMS 필터링 후 감지 결과 확인 및 이벤트 전송
```

## 김재민 학생(얼굴인식 AI)을 위한 초경량 구현 가이드
무겁고 C++ 컴파일러 에러가 발생하는 `face_recognition`/`dlib` 대신, `opencv-python`에 기본 내장된 YuNet/SFace 모델을 사용하면 단 10줄의 코드로 학생 얼굴을 감지·식별할 수 있습니다:
- **얼굴 검출 (Face Detection)**: `cv2.FaceDetectorYN.create()`
- **얼굴 인식 및 임베딩 (Face Recognition)**: `cv2.FaceRecognizerSF.create()`
- **유사도 판정**: `recognizer.match(feat1, feat2, cv2.FaceRecognizerSF_FR_COSINE)`
- **화면 한글 출력**: `main.py`의 `put_korean_text()`를 활용하여 학생 이름 및 학번 선명 렌더링


<details>
<summary>mediapipe로도 가능 (얼굴 감지 등 다른 용도일 때)</summary>

```python
import cv2
import mediapipe as mp

cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
detector = mp.solutions.face_detection.FaceDetection()

while True:
    ok, frame = cap.read()
    if not ok:
        continue
    result = detector.process(frame)
    detected = bool(result.detections)
```
</details>

## 이벤트 전송
```python
import requests
requests.post(
    f"{BACKEND_URL}/api/v1/vision/events",
    json={"event_type": "person_detected", "detected": True, "count": 1, "confidence": 0.9},
    headers={"X-Device-Api-Key": DEVICE_API_KEY},
)
```

## 트리거 연결
백엔드(backend-agent)가 `vision_events`를 받아 팀이 정한 트리거 규칙(AGENTS.md의
"팀 정보" 표 참고)에 따라 desired-state를 갱신한다. vision 클라이언트는 감지 사실만
보고할 뿐, 제어를 직접 판단하지 않는다.
