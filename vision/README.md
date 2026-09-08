# 스마트 교실 비전 AI 클라이언트 (vision)

## 💡 [학생 필독 - 5초 초고속 세팅 및 김재민 학생(얼굴인식) 가이드]

### 1. 초경량 ONNX 추론 엔진 도입 (PyTorch 설치 불필요!)
- 무거운 PyTorch(2.5GB)와 Ultralytics를 완전히 걷어내고 onnxruntime/cv2.dnn 기반으로 구동됩니다.
- Windows에서 빈번히 발생하는 PyTorch DLL 충돌(`[WinError 1114] c10.dll`)이 원천 차단됩니다.
- 패키지 설치 용량이 2.5GB -> 150MB로 줄어들어 10초 이내에 환경 구축이 완료됩니다.

### 2. 김재민 학생(얼굴인식 AI 담당) 구현 가이드
- 무겁고 C++ 컴파일러(Visual Studio Build Tools) 에러가 잦은 `face_recognition`, `dlib`, `PyTorch` 대신 본 가상환경에 이미 설치된 가볍고 에러 없는 초경량 방식을 사용하세요:
  1. **OpenCV 내장 DNN 방식 (강력 추천)**:
     - `cv2.FaceDetectorYN` (YuNet 얼굴 검출) + `cv2.FaceRecognizerSF` (SFace 얼굴 인식)
     - 별도 라이브러리 추가 설치 없이 `opencv-python`만으로 LFW 99.5% 인식률과 실시간 30+ FPS 달성
  2. **ONNXRuntime 방식**:
     - ArcFace 또는 MobileFaceNet ONNX 모델을 onnxruntime으로 로드하여 얼굴 임베딩 추출
     - 추출된 벡터를 `scipy.spatial.distance.cosine`으로 비교하여 학생 식별

### 3. 가상환경 생성 및 설치
```powershell
# Windows PowerShell (Python 3.12 지정)
py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1
$env:PYTHONUTF8=1; pip install -r requirements.txt
```
