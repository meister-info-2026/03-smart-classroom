---
name: vision-recognition-integration
description: >-
  웹캠 기반 YOLOv8/mediapipe 영상인식 파이프라인 구성, Windows 패키지 의존성 설정 및 감지 이벤트 백엔드 전송을 구현할 때 사용하는 스킬.
---

# vision-recognition-integration

> 웹캠 영상인식(YOLO/mediapipe) 연동 작업 시 이 스킬을 참고한다.

## 패키지 설치 (Windows 주의)
Windows 기본 경로 길이 제한(260자)과 최신 NumPy 2.x·PyTorch 바이너리 충돌로
`pip install ultralytics`가 `[WinError 206] 파일 이름이나 확장명이 너무 깁니다`로
실패할 수 있다. 아래처럼 버전을 고정해서 설치한다.
```powershell
cd vision
python -m venv venv
.\venv\Scripts\Activate.ps1
# 1. 경로 에러가 없는 경량 CPU PyTorch 설치
pip install torch==2.2.2+cpu torchvision==0.17.2+cpu --extra-index-url https://download.pytorch.org/whl/cpu
# 2. 호환 패키지 설치
pip install "numpy<2" opencv-python==4.9.0.80 ultralytics requests python-dotenv
```
그래도 경로 에러가 나면 관리자 권한 PowerShell에서 Windows 긴 경로 제한을 아예
해제한다(FAQ 참고):
```powershell
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force
```

## 최소 파이프라인 (YOLOv8n 예시 — 실제 검증된 조합)
사람 감지처럼 "특정 인물 식별이 아닌 사람/사물 존재 여부"에는 mediapipe의
얼굴 감지보다 YOLOv8n(경량 객체 감지 모델)이 더 적합하고 실제로도 검증됐다.
```python
import cv2
from ultralytics import YOLO

model = YOLO("yolov8n.pt")
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # Windows에서는 CAP_DSHOW로 열어야 웹캠 인식이 안정적

while True:
    ok, frame = cap.read()
    if not ok:
        continue
    results = model(frame, classes=[0], verbose=False)  # class 0 = person
    detected = len(results[0].boxes) > 0
    # 상태가 바뀔 때만 이벤트 전송 (vision-rules.md 참고)
```

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

## 얼굴 인식(InsightFace) — 무거운 의존성 주의
"이 사람이 누구인지 식별"해야 하는 경우(출입 인증 등)는 위의 YOLOv8n(존재 감지)이나
mediapipe(단순 얼굴 감지)로는 부족하다. `insightface`로 얼굴 임베딩을 추출해야
하는데, 최초 실행 시 큰 모델(예: buffalo_l, 수백MB)을 자체적으로 자동 다운로드하므로
yolov8n.pt를 사전 탑재한 것과 같은 이유(실습실 전체가 동시에 받으면 학내망 부하)로
주의가 필요하다. **모델을 한 번 받아 저장소에 커밋해두는 것을 권장한다.**
```bash
pip install insightface onnxruntime opencv-python
```
```python
import cv2
from insightface.app import FaceAnalysis

face_app = FaceAnalysis(name="buffalo_l")
face_app.prepare(ctx_id=0)  # CPU: ctx_id=-1

cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
ok, frame = cap.read()
faces = face_app.get(frame)
if faces:
    embedding = faces[0].embedding  # 512차원 벡터
```

### 임베딩 추출(vision)과 매칭(backend) 역할 분리 `[권장]`
InsightFace 추론(무거움)은 vision 클라이언트에만 두고, 저장된 전체 사용자
임베딩과의 코사인 유사도 비교(DB 접근 필요)는 backend가 담당하는 것을 권장한다.
vision은 **원본 이미지가 아니라 임베딩 벡터만** 전송한다.
```python
import requests
requests.post(
    f"{BACKEND_URL}/api/recognition",
    json={
        "embedding": embedding.tolist(),
        "camera_type": "entry",   # "entry" | "classroom"
        "action": "check_in",
        "classroom_id": classroom_id,
    },
    headers={"X-Device-Api-Key": DEVICE_API_KEY},
)
```
매칭·응답 형식은 `attendance-tracking-integration` 스킬을 참고한다.

## 좌석 ROI 체류시간 판정 (예: 3초)
"잠깐 지나간 것"과 "실제로 착석한 것"을 구분하려면 프레임 단위 감지가 아니라
**좌석별 타이머**가 필요하다. 서버 부하를 줄이기 위해 vision 클라이언트가 로컬에서
타이머를 재고, 확정된 결과만 백엔드에 보고하는 것을 권장한다.
```python
seat_first_seen = {}  # {seat_id: timestamp}
DWELL_SECONDS = 3

for seat_id, detected_user_id in current_frame_detections.items():
    reserved_user_id = reserved_seats.get(seat_id)
    if detected_user_id == reserved_user_id:
        seat_first_seen.setdefault(seat_id, time.time())
        if time.time() - seat_first_seen[seat_id] >= DWELL_SECONDS:
            report_seat_status(seat_id, "OCCUPIED", detected_user_id)
    elif detected_user_id is not None:
        seat_first_seen.pop(seat_id, None)
        report_seat_status(seat_id, "MISMATCH", detected_user_id)
    else:
        seat_first_seen.pop(seat_id, None)
```

## 카메라 2대 이상 사용 시 `.env` 확장
기본 `CAMERA_INDEX` 하나만으로는 부족하다. 카메라별로 이름을 붙여 확장한다.
```
ENTRY_CAMERA_INDEX=0
CLASSROOM_CAMERA_INDEX=1
```
