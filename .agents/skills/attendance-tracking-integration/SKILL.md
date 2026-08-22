---
name: attendance-tracking-integration
description: >-
  얼굴 임베딩 코사인 유사도 매칭, 좌석·출석·재실 상태 갱신, 얼굴 등록(enrollment)
  승인 흐름, 5회 인식 실패 경고 로직을 구현할 때 사용하는 스킬.
---

# attendance-tracking-integration

> "AI 출입 출석 스마트 교실"처럼 얼굴 인식 결과로 출입·출석·좌석 상태를 관리해야
> 할 때 이 스킬을 참고한다. `iot-endpoint-generator`(디바이스 CRUD)와는 별개로,
> 사용자 식별과 출결 상태 전이를 다룬다. vision 쪽의 임베딩 추출·좌석 타이머는
> `vision-recognition-integration` 스킬을 참고한다.

## devices 테이블 (액추에이터 6개 + 센서 3개)
`db-rules.md`의 최소 4테이블은 그대로 두고, `devices`에 아래 GPIO 장치를 등록한다.
출입/교실 카메라는 `devices` 대상이 아니다(영상인식 파이프라인으로 별도 처리).

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

## 얼굴 임베딩 매칭 엔드포인트
`vision-recognition-integration` 스킬에서 vision 클라이언트가 보낸 임베딩을 받아
저장된 전체 사용자 임베딩과 코사인 유사도로 비교한다.

**`POST /api/recognition`**
```json
{
  "embedding": [0.0123, -0.045],
  "camera_type": "entry",
  "action": "check_in",
  "classroom_id": 1,
  "seat_id": null
}
```
```python
import numpy as np

def cosine_similarity(a, b):
    a, b = np.array(a), np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

def match_user(embedding, candidates, threshold=0.5):
    best_user, best_score = None, -1
    for user in candidates:  # users 테이블의 face_embedding 전체 후보
        score = cosine_similarity(embedding, user.face_embedding)
        if score > best_score:
            best_user, best_score = user, score
    decision = "MATCH" if best_score >= threshold else "NO_MATCH"
    return best_user, best_score, decision
```
응답:
```json
{
  "success": true,
  "user_id": 42,
  "name": "김다온",
  "similarity_score": 0.87,
  "decision": "MATCH"
}
```
`camera_type=entry`면 입실/퇴실/재입실 규칙에 따라 `access_logs`/`attendance`/
`student_status`를 갱신한다. `camera_type=classroom`이고 `seat_id`가 있으면
좌석 상태(`seats.status`)를 갱신한다(vision이 이미 3초 체류 판정을 끝내고 보낸
결과이므로 backend는 그대로 반영만 한다).

## 얼굴 등록(enrollment) 승인 흐름
1. `POST /api/registration` — 학번·이름·유형 → `registration_requests`에 `PENDING`으로 저장
2. 관리자가 `PUT /api/registration/{id}/approve`
3. 승인 시 얼굴 촬영 → `vision-recognition-integration`과 동일한 방식으로 임베딩 추출
4. `users.face_embedding`에 저장, `is_active=true`
5. **원본 이미지는 임베딩 추출 직후 폐기한다** (저장하지 않음 — vision-rules.md 개인정보 원칙)

거부 시 `PUT /api/registration/{id}/reject`로 상태를 `REJECTED`로 바꾸고 `reason`을
저장한다.

## 5회 인식 실패 경고
`access_logs`에서 해당 카메라(`camera_type=entry`)의 마지막 성공 이후 연속 실패
횟수를 조회한다. 5회에 도달하면 `warning_logs`에 기록하고 부저(`buzzer`)
desired-state를 켠다.

## 재실 인원 → 조명 트리거
`iot-endpoint-generator` 스킬 그대로 적용한다. 재실 인원이 0→1 이상이 되면
`light_relay`의 desired-state를 ON으로, 1 이상→0이면 OFF로 갱신한다.

## 예시 프롬프트
```
너는 이 프로젝트의 backend-agent다. .agents/rules/db-rules.md와
.agents/skills/attendance-tracking-integration/SKILL.md를 따른다.

POST /api/recognition(임베딩 기반 매칭), POST /api/registration 승인 흐름,
좌석 상태 갱신, 5회 실패 경고 로직을 만들어줘.
```
