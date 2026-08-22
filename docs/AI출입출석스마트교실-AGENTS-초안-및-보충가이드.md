# AI 출입 출석 스마트 교실 — AGENTS.md 초안 및 보충 가이드

> **이 문서는 무엇인가요?**
> 「AI 출입 출석 스마트 교실」팀의 PRD(v2.0, 32절)를 스타터 킷 구조와 대조 검토한
> 결과를 바탕으로 만든 문서입니다. 두 부분으로 구성됩니다.
> - **1부**: 이 팀 전용 `AGENTS.md` 초안 — 그대로 복사해 프로젝트 루트 `AGENTS.md`에
>   붙여넣으면 됩니다. 이 팀은 PRD에 팀명·팀원·GPIO 맵·부품까지 이미 확정돼 있어
>   `[미정]`이 매우 적습니다.
> - **2부**: 스타터 킷의 기본 스킬이 커버하지 않는, 이 팀만 추가로 설계해야 하는
>   부분 — 얼굴 임베딩 API 계약, 좌석 체류시간 타이머, `devices` 스키마.
>
> PRD 작성 원칙과 동일하게, **PRD에 없는 내용은 임의로 만들어 넣지 않고 `[미정]`으로
> 남겨두었습니다.** 킷 적용 관점에서 권장하는 내용(PRD의 `image_base64` 대신 임베딩
> 벡터를 쓰는 것 등)은 `[권장]`으로 표시하고, PRD의 원래 설계와 다르다는 점을
> 명시합니다.

---

# 1부. AGENTS.md 초안 (팀 전용)

아래 블록 전체를 프로젝트 루트의 `AGENTS.md` 파일에 그대로 붙여넣습니다. `.agents/`,
`docs/`는 이미 완성되어 있으므로 손대지 않습니다.

````markdown
# AGENTS.md — AI-출입-출석-스마트-교실

## 프로젝트 개요
- 팀 주제: `얼굴 인식과 교실 카메라를 이용해 출입, 출석, 좌석, 재실 상태를 통합
  관리하는 스마트 교실`
- 한 줄 목표: `얼굴 인식과 좌석·교실 카메라 판정을 연결하여 학생의 출입, 출석,
  착석 및 재실 상태를 교사와 관리자가 실시간으로 확인하는 스마트 교실을 구현한다`
- 팀명: `AI 출입 출석 스마트 교실`
- 팀원: 김다온, 김재민, 김하준, 윤상훈, 이도건, 서종혁 (역할은 "팀 정보" 참고)
- 개발 기간: 8주

## 기술 스택 (고정 — 임의로 바꾸지 않는다)
- 백엔드: FastAPI (Python), SQLAlchemy + Alembic
- DB: MySQL 8.4
- 프론트엔드: Next.js(TypeScript), Tailwind CSS
- 하드웨어 제어: Python venv Mock(개발 전반부) → 라즈베리파이 5 + gpiozero(개발 후반부).
  네오픽셀 LED 스트립만 예외로 별도 라이브러리 사용(2부 참고)
- 영상인식: OpenCV(얼굴 검출) + **InsightFace(얼굴 임베딩·식별)** + YOLO(사람 검출) —
  출입 카메라·교실 카메라 2대 모두 Windows PC에서 실행. InsightFace는 무거운
  의존성이라 주의가 필요하다(2부 1절 참고)
- 배포: Render(백엔드) / Vercel(프론트) — 이 팀의 8주 일정에 배포 단계가 명시돼
  있지 않아 적용 여부는 `[미정]`
- 버전관리: GitHub / 문서·협업: Notion

## 핵심 데이터 흐름

> 기본 스타터 킷 예시("웹캠이 사람/사물을 감지 → 즉시 액추에이터 제어")보다 단계가
> 많다 — **얼굴 식별**이라는 새 단계가 앞에 붙고, **좌석 체류시간 판정**이라는 시간
> 기반 단계가 뒤따른다. 상세 설계는 2부와
> `.agents/skills/vision-recognition-integration/SKILL.md`(얼굴/좌석 인식 확장),
> `.agents/skills/attendance-tracking-integration/SKILL.md`(매칭/출결 엔드포인트)를
> 참고한다.

1. 학생/교사가 출입 카메라 앞에서 교실·수업·동작(입실/퇴실)을 선택한다(프론트엔드
   키오스크 화면)
2. vision 클라이언트(출입 카메라)가 얼굴을 검출하고 InsightFace로 임베딩을 추출해
   백엔드에 전송한다(원본 이미지 대신 임베딩 벡터를 보내는 것을 권장 — 2부 참고)
3. 백엔드가 등록된 사용자들의 저장된 임베딩과 코사인 유사도를 비교해 사용자를
   식별하고, 입실/퇴실/재입실 규칙에 따라 `access_logs`/`attendance`/
   `student_status`를 갱신한다
4. 입실이 확정되면 선택 좌석을 `RESERVED`로 표시하고 좌석 LED/네오픽셀
   desired-state를 갱신한다
5. vision 클라이언트(교실 카메라)가 YOLO로 사람을 검출하고, 좌석 ROI 안에서 동일
   학생이 **3초 이상** 검출되는지 로컬 타이머로 확인한 뒤 `OCCUPIED` 또는
   `MISMATCH`를 백엔드에 보고한다
6. 재실 인원이 0→1 이상으로 바뀌면 백엔드가 교실 조명(릴레이) desired-state를
   ON으로, 1 이상→0이면 OFF로 갱신한다
7. 얼굴 인식이 5회 연속 실패하면 백엔드가 경고를 기록하고 부저 desired-state를
   울림으로 바꾼다
8. 하드웨어(Mock 또는 라즈베리파이)가 desired-state를 폴링해 자동문·LED·네오픽셀·
   부저·릴레이를 실제로 반영한다
9. 프론트엔드(교사/관리자 화면)는 WebSocket으로 모든 상태를 실시간 표시한다

## AI 사용 원칙
- 모든 작업은 `.agents/rules/karpathy-principles.md`의 4원칙(생각 먼저·단순함 우선·
  외과적 변경·목표 기반 실행)을 기본으로 따른다
- AI가 생성한 코드는 반드시 학생이 직접 실행하고 결과를 눈으로 확인한다
- "AI가 알아서 잘했다"는 요약만 믿고 다음 단계로 넘어가지 않는다
- 시크릿(API 키, 비밀번호, DB 접속정보)은 절대 채팅/프롬프트에 직접 입력하지 않는다
  (security-rules.md 참고)
- 이 킷의 `.agents/rules`, `.agents/skills`는 이미 완성되어 있다 — **다시 만들어달라고
  요청하지 않는다.** 새 기능을 요청할 때 "역할 지정 + 관련 rules/skills 참고" 문구만
  붙이면 AI가 알아서 참고한다 (토큰 절약)
- **원본 얼굴 이미지, 원본 카메라 영상, 원본 프레임은 저장하지 않는다** — 임베딩
  추출 뒤 즉시 폐기한다 (PRD 15.4, vision-rules.md 개인정보 원칙과 동일)
- 얼굴 등록(enrollment) 시연 범위는 실제 학급 전체가 아니라 **동의한 팀원 범위로
  한정**하는 것을 권장한다(2부 5절 참고) — 실제 학급 전체로 넓히려면 학교 개인정보
  처리 방침을 교사가 먼저 확인한다
- 이 프로젝트는 기본 스킬 범위를 넘는 부분(얼굴 임베딩 매칭, 좌석 체류시간 판정)이
  있다 — 해당 작업을 요청할 때는 `attendance-tracking-integration` 스킬이나 이
  문서 2부의 절 번호를 함께 언급한다

## 폴더 구조
```
AI-출입-출석-스마트-교실/
├── AGENTS.md
├── .agents/            (하네스: rules/skills/workflows/hooks/agents — 이미 완성됨)
├── backend/            (FastAPI, .env.example 포함 — 얼굴 임베딩 매칭도 여기서 처리)
├── frontend/           (Next.js — 학생/교사/관리자 화면을 한 앱 안에서 라우트로 분리)
├── vision/             (출입·교실 카메라 2대, Windows PC에서 실행, .env.example 포함)
└── pi/                 (라즈베리파이 — 자동문·LED·네오픽셀·부저·릴레이·센서, 3주차부터)
```
각 폴더의 `.env.example`을 `.env`로 복사해 실제 값을 채운다 (`.env`는 커밋되지
않는다 — docs/학생용-설치-및-사용-매뉴얼.md 1단계 참고).

## 팀 정보

| 항목 | 값 |
|---|---|
| 팀 주제 | 얼굴 인식과 교실 카메라를 이용한 출입·출석·좌석·재실 통합 관리 스마트 교실 |
| 액추에이터(제어 대상) 목록 | 자동문(MG90S 서보), 좌석 상태 LED(파랑/빨강/초록), 네오픽셀 LED 스트립(좌석별 상태 색상), 부저, 릴레이(교실 조명) — 6개 |
| 센서(모니터링 대상) 목록 | 리드스위치(문 닫힘), 불꽃 센서, I2C 온습도 센서 — 3개. 출입/교실 카메라는 `devices` 테이블 대상이 아니라 영상인식 파이프라인으로 별도 처리(아래 참고) |
| 영상인식 감지 대상 | ① 출입 카메라: 얼굴 검출·식별(InsightFace) — 입실/퇴실/재입실<br>② 교실 카메라: 사람 검출(YOLO) + 좌석 ROI 3초 체류 판정 — 착석/재실/무단이탈 |
| 트리거 규칙 | 얼굴 인식 성공+좌석 일치 → `PRESENT`/`OCCUPIED` + 좌석 LED. 좌석 불일치 → `MISMATCH` + 교사 경고(자동 변경 없음, 교사가 최종 판단). 재실 0→1↑ → 조명 ON, 1↑→0 → 조명 OFF. 인식 5회 연속 실패 → 부저+관리자 경고. 인증 성공 → 자동문 OPEN 5초 후 CLOSED |
| 팀원 역할 분담 | 김다온 → 프로젝트 총괄·GitHub 관리·backend·frontend / 김재민 → 얼굴인식 AI(vision) / 김하준 → 하드웨어 회로(hardware) / 서종혁 → 라즈베리파이5(hardware) / 윤상훈 → 기구물·미니어처 제작 / 이도건 → 기구물 설계도. (킷의 4개 AI 에이전트 역할 중 db-agent는 김다온이 backend와 함께 겸한다) |
````

---

# 2부. 이 팀에 필요한 보충 설계

> 아래 내용은 스타터 킷의 기본 스킬이 다루지 않는 것들입니다. 해당 작업을
> vision-agent/backend-agent/db-agent에게 요청할 때 이 절 번호를 프롬프트에 함께
> 적어주면 AI가 맥락을 정확히 참고합니다.

## 2-1. InsightFace는 킷에서 가장 무거운 신규 의존성입니다 `[중요]`

킷은 원래 yolov8n.pt(6.2MB)를 저장소에 사전 탑재해 "실습실 30~40명이 동시에 모델을
다운로드해 학내망이 막히는" 문제를 피했습니다. `insightface` 패키지는 최초 실행 시
자체적으로 훨씬 큰 모델(예: buffalo_l, 수백MB)을 자동 다운로드하므로 같은 문제가
재발할 수 있습니다.

**`[권장]`**: 팀이 실제 사용할 InsightFace 모델을 한 번 다운로드한 뒤,
`vision/models/`처럼 저장소에 커밋해 학생들이 각자 다운로드하지 않게 하는 것을
고려합니다(용량이 크면 Git LFS 사용을 검토). 대안으로 더 가벼운 얼굴 인식 라이브러리
(예: `face_recognition`)로 낮출 수도 있습니다 — 어떤 쪽이든 **학기 초, 전체 학생이
한꺼번에 실습하기 전에 미리 설치·다운로드해서 검증**하는 것을 강하게 권장합니다.

```bash
cd vision
pip install insightface onnxruntime opencv-python ultralytics requests python-dotenv
```

## 2-2. 임베딩 추출(vision)과 매칭(backend) 역할 분리 `[권장 — PRD와 다름]`

PRD의 API-04(`POST /api/recognition`)는 요청 필드로 `image_base64`(원본에 가까운
이미지)를 명시하고 있습니다. 이렇게 하면 InsightFace 추론이 backend 쪽에서도
일어나야 해서, 무거운 라이브러리가 `vision/`과 `backend/` 양쪽에 다 필요해집니다.

**대신 아래 방식을 권장합니다**: vision 클라이언트가 얼굴 검출 + 임베딩 추출까지
끝내고, **임베딩 벡터(숫자 배열)만** 백엔드로 보냅니다. 전체 사용자 임베딩과의
코사인 유사도 비교(어차피 DB 접근이 필요해 backend에서 해야 함)만 backend가
담당합니다. InsightFace 설치·추론은 `vision/`에만 있으면 됩니다.

```python
# vision/main.py (출입 카메라)
embedding = face_model.get_embedding(face_crop)  # InsightFace, 512차원 벡터
requests.post(
    f"{BACKEND_URL}/api/recognition",
    json={
        "embedding": embedding.tolist(),
        "camera_type": "entry",
        "action": "check_in",
        "classroom_id": classroom_id,
    },
    headers={"X-Device-Api-Key": DEVICE_API_KEY},
)
```
```python
# backend: 코사인 유사도 매칭 (DB 접근 필요 — 여기서만)
import numpy as np
def match_user(embedding, candidates, threshold=0.5):
    best_user, best_score = None, -1
    for user in candidates:  # users.face_embedding
        score = cosine_similarity(embedding, user.face_embedding)
        if score > best_score:
            best_user, best_score = user, score
    decision = "MATCH" if best_score >= threshold else "NO_MATCH"
    return best_user, best_score, decision
```

응답 형식은 PRD API-04와 동일하게 맞춥니다.
```json
{
  "success": true,
  "user_id": 42,
  "name": "김다온",
  "similarity_score": 0.87,
  "decision": "MATCH"
}
```

> PRD 그대로 `image_base64` 방식을 쓰고 싶다면 그것도 가능합니다 — 다만 그 경우
> `backend/requirements.txt`에도 InsightFace를 추가해야 하고, 2-1의 무거운 의존성
> 문제를 backend 서버에서도 신경 써야 합니다.

## 2-3. 좌석 체류시간(3초) 판정

프레임 단위 감지가 아니라 **좌석별 타이머**가 필요합니다. 서버 부하를 줄이기 위해
vision 클라이언트(교실 카메라)가 로컬에서 타이머를 재고, 확정된 결과만 백엔드에
보고하는 것을 권장합니다.

```python
# vision/main.py (교실 카메라) — 좌석별 체류시간 추적
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

## 2-4. 출입/교실 카메라 2대 — `.env` 확장

기본 `vision/.env.example`은 `CAMERA_INDEX` 하나만 지원합니다. 이 팀은 카메라가
2대이므로 아래처럼 나눠 씁니다.
```
ENTRY_CAMERA_INDEX=0
CLASSROOM_CAMERA_INDEX=1
```

## 2-5. `devices` 테이블 (액추에이터 6개 + 센서 3개)

`db-rules.md`의 최소 스키마(`devices`/`sensor_readings`/`control_log`/
`vision_events`)를 그대로 쓰되, `devices` 시드 데이터를 PRD 9.2 GPIO 맵 그대로
등록합니다. 얼굴/좌석 인식 결과는 `vision_events`보다 PRD 자체의 `access_logs`/
`attendance`/`seats` 테이블에 직접 쓰는 것이 더 정확합니다(2-6 참고).

| device_id | kind | GPIO | 설명 |
|---|---|---|---|
| `led_blue` | led | GPIO5 | 상태 LED(파랑) |
| `led_red` | led | GPIO6 | 상태 LED(빨강) |
| `led_green` | led | GPIO13 | 상태 LED(초록) |
| `neopixel_strip` | neopixel | GPIO10(SPI) | 좌석 6석 + 안전 상태 색상 표시 |
| `buzzer` | buzzer | GPIO17 | 얼굴 인식 실패·안전 경고 |
| `door_servo` | servo | GPIO18(PWM) | MG90S 자동문 |
| `light_relay` | relay | GPIO22 | 교실 조명 |
| `reed_switch` | sensor | GPIO27(IN) | 문 닫힘 감지 |
| `flame_sensor` | sensor | GPIO23(IN) | 불꽃 감지 |
| `temp_humidity` | sensor | GPIO2/3(I2C) | 온습도 |

네오픽셀은 `gpiozero`로 직접 제어하기 어려워 `rpi_ws281x` 또는
`adafruit-circuitpython-neopixel` 같은 별도 라이브러리가 필요합니다(PRD 8.1
A-05의 판단이 맞습니다). 라즈베리파이에서 이 라이브러리는 보통 관리자 권한(sudo)이
필요하다는 점을 배선 전에 확인합니다.

## 2-6. 얼굴 등록(enrollment) 흐름과 5회 실패 카운터

**등록**: `POST /api/registration`(학번·이름·유형) → `PENDING` → 관리자
`PUT /api/registration/{id}/approve` → 얼굴 촬영 → 임베딩 추출(2-2와 동일 방식) →
`users.face_embedding` 저장, `is_active=true`. 원본 이미지는 임베딩 추출 직후
폐기합니다(PRD 15.4).

**5회 실패 카운터**: `access_logs`에서 해당 카메라(`camera_type=entry`)의 마지막
성공 이후 연속 실패 횟수를 조회해 5에 도달하면 `warning_logs`에 기록하고 부저
desired-state를 켭니다.

## 2-7. 재실 인원 → 조명 트리거

이 부분은 킷의 기본 예시(AGENTS.md의 "사람 감지 시 조명 ON, 미감지 시 OFF")와
동일한 패턴이라 별도 설계가 필요 없습니다 — `iot-endpoint-generator` 스킬 그대로
적용합니다.

## 2-8. 예시 프롬프트

**DB + 매칭/출결 엔드포인트 (db-agent → backend-agent)**
```
너는 이 프로젝트의 db-agent다. .agents/skills/db-integration/SKILL.md와
.agents/skills/attendance-tracking-integration/SKILL.md를 따른다.

db-rules.md의 devices 테이블에 이 문서 2-5절의 액추에이터·센서를 등록해줘.
PRD의 users/classrooms/seats/schedules/access_logs/attendance/student_status/
registration_requests/warning_logs/hardware_status_logs 테이블도 함께 만들어줘.
```
```
너는 이 프로젝트의 backend-agent다. .agents/skills/attendance-tracking-integration/SKILL.md를
따른다.

POST /api/recognition(임베딩 기반 매칭), POST /api/registration 승인 흐름,
좌석 상태 갱신, 5회 실패 경고 로직을 만들어줘.
```

**얼굴/좌석 인식 (vision-agent)**
```
너는 이 프로젝트의 vision-agent다. .agents/rules/vision-rules.md와
.agents/skills/vision-recognition-integration/SKILL.md를 따른다.

docs/AI출입출석스마트교실-AGENTS-초안-및-보충가이드.md 2-1~2-4절을 참고해서
vision/main.py를 만들어줘. 출입 카메라는 얼굴 검출+InsightFace 임베딩 추출,
교실 카메라는 YOLO 사람 검출 + 좌석 ROI 3초 체류 판정을 각각 처리하고,
결과를 POST /api/recognition으로 전송해줘.
```

---

# 3부. 참고

- 이 문서는 팀의 「프로젝트 개발 계획서」/PRD(AI 출입 출석 스마트 교실, v2.0)
  검토를 바탕으로 작성되었습니다. PRD에 없는 내용은 임의로 만들지 않고 `[미정]`으로
  남겼습니다.
- `docs/백엔드-라즈베리파이5-연동-인터페이스-가이드.md` — desired-state 폴링 계약
  (자동문·LED·네오픽셀·부저·릴레이 모두 이 패턴을 그대로 따릅니다)
- `.agents/rules/vision-rules.md` — 개인정보 보호 원칙(원본 영상·얼굴 이미지 미저장)
- `.agents/rules/db-rules.md` — 경보성 디바이스 원칙, 최소 스키마
- `.agents/rules/api-rules.md` — 사용자향/디바이스향 인증 분리
- `docs/학생용-설치-및-사용-매뉴얼-수정본.md`
