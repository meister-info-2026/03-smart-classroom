"""
Vision event ingestion and trigger rules router.
Receives vision events from Windows webcam client and executes trigger rules.
"""

from datetime import datetime
import logging
import os
from typing import Any, Dict, Optional
from fastapi import APIRouter, Header, HTTPException, status

from schemas.devices import VisionEventRequest
from iot.provider_factory import get_device_provider
from db.database import log_vision_event, get_recent_vision_events
from routes.devices import verify_device_api_key
from routes.classroom import SEATS, ATTENDANCE_LOG
from websocket_manager import ws_manager

logger = logging.getLogger("backend.routes.vision")
router = APIRouter()


@router.post("/api/v1/vision/events")
async def receive_vision_event(
    event: VisionEventRequest,
    x_device_api_key: Optional[str] = Header(None),
) -> Dict[str, Any]:
    """
    영상인식 클라이언트로부터 감지 이벤트를 수신하여 DB에 기록하고,
    AGENTS.md의 '트리거 규칙'에 따라 액추에이터 상태를 즉시 제어합니다.
    """
    verify_device_api_key(x_device_api_key)

    # 1. DB에 이벤트 기록
    try:
        log_vision_event(
            event_type=event.event_type,
            detected=event.detected,
            count=event.count,
            confidence=event.confidence,
            details=event.details,
        )
    except Exception as exc:
        logger.warning(f"Failed to log vision event to DB: {exc}")

    provider = get_device_provider()
    actions_taken = []
    now_str = datetime.now().strftime("%H:%M:%S")

    # ==============================================================================
    # 2. AGENTS.md 및 PRD 트리거 규칙 적용
    # ==============================================================================

    # 규칙 ①: 등록 학생 얼굴 인증 성공 -> 입실 처리 및 자동문 개폐
    if event.event_type == "face_recognized" and event.detected:
        student_id = event.details.get("student_id", "202601") if event.details else "202601"
        student_name = event.details.get("student_name", "김재민") if event.details else "김재민"

        # 출석부 기록 갱신
        for record in ATTENDANCE_LOG:
            if record["student_id"] == student_id:
                record["status"] = "출석완료"
                record["check_in_time"] = now_str
                break

        # MG90S 자동문 OPEN (MockProvider 내부에서 5초 뒤 자동 CLOSED 스케줄링)
        await provider.set_actuator_state("servo_door", "OPEN", {"angle": 90}, operator="device")
        actions_taken.append("servo_door_OPEN_5s")

        # 재실 인원 확인 -> 1명 이상이면 교실 조명(릴레이) 자동 ON
        await provider.set_actuator_state("relay_light", "ON", {"enabled": True}, operator="device")
        actions_taken.append("relay_light_ON")

        # 좌석 LED / 안내 점등
        await provider.set_actuator_state("seat_led", "ON", {"brightness": 100}, operator="device")
        actions_taken.append("seat_led_ON")

    # 규칙 ②: 미등록자 / 얼굴 인증 실패 (5회 누적 또는 거부) -> 부저 경고음
    elif event.event_type in ("face_unrecognized", "auth_failed"):
        await provider.set_actuator_state("buzzer", "ON", {"frequency": 1000}, operator="device")
        actions_taken.append("buzzer_warning_ON")

    # 규칙 ③: 6개 좌석 ROI 기반 착석 판정 (RESERVED / OCCUPIED / MISMATCH)
    elif event.event_type == "seat_status" and event.details:
        seat_id = event.details.get("seat_id")
        detected_seat_status = event.details.get("status", "OCCUPIED")  # OCCUPIED / MISMATCH / EMPTY

        if seat_id and seat_id in SEATS:
            seat = SEATS[seat_id]
            # 만약 학생이 예약한 좌석과 실제 착석이 일치하는지 판정
            if detected_seat_status == "OCCUPIED":
                seat["status"] = "OCCUPIED"
                seat["occupied_at"] = now_str
                # 네오픽셀: 초록색 점등
                await provider.set_actuator_state(
                    "neopixel_seat", "ON", {"mode": "solid", "color": "#10B981", "seat_id": seat_id}, operator="device"
                )
            elif detected_seat_status == "MISMATCH":
                seat["status"] = "MISMATCH"
                # 네오픽셀: 빨강 점멸
                await provider.set_actuator_state(
                    "neopixel_seat", "ALERT", {"mode": "blink", "color": "#EF4444", "seat_id": seat_id}, operator="device"
                )
            elif detected_seat_status == "EMPTY":
                if seat["status"] != "RESERVED":
                    seat["status"] = "AVAILABLE"
                await provider.set_actuator_state(
                    "neopixel_seat", "OFF", {"mode": "off", "color": "#000000"}, operator="device"
                )

            actions_taken.append(f"seat_{seat_id}_status_{seat['status']}")

    # 규칙 ④: 교실 인원 감지 (재실 인원 0명이면 조명 자동 소등)
    elif event.event_type == "person_detected":
        if event.count == 0:
            await provider.set_actuator_state("relay_light", "OFF", {"enabled": False}, operator="device")
            actions_taken.append("relay_light_OFF_empty")
        elif event.count >= 1:
            await provider.set_actuator_state("relay_light", "ON", {"enabled": True}, operator="device")
            actions_taken.append("relay_light_ON_occupied")

    # 규칙 ⑤: 불꽃 감지 센서 화재 경보
    elif event.event_type == "flame_detected" and event.detected:
        if hasattr(provider, "_states"):
            provider._states["flame_sensor"]["state"] = "DETECTED"
            provider._states["flame_sensor"]["value"] = {"flame_detected": True}
        await provider.set_actuator_state("buzzer", "ON", {"frequency": 2000}, operator="device")
        await provider.set_actuator_state(
            "neopixel_seat", "ALERT", {"mode": "blink", "color": "#EF4444"}, operator="device"
        )
        actions_taken.append("flame_alert_triggered")

    # ==============================================================================
    # 3. WebSocket 대시보드 실시간 브로드캐스트
    # ==============================================================================
    all_devs = await provider.get_all_statuses()
    await ws_manager.broadcast({
        "type": "vision_event",
        "event": {
            "event_type": event.event_type,
            "detected": event.detected,
            "count": event.count,
            "confidence": event.confidence,
            "details": event.details,
            "timestamp": now_str,
            "actions_taken": actions_taken,
        },
        "devices": all_devs,
        "seats": list(SEATS.values()),
        "attendance": ATTENDANCE_LOG,
    })

    return {
        "status": "success",
        "event_type": event.event_type,
        "actions_taken": actions_taken,
    }


@router.get("/api/vision/events")
async def list_recent_vision_events(limit: int = 20) -> Dict[str, Any]:
    """최근 비전 감지 이벤트 목록을 반환합니다."""
    events = get_recent_vision_events(limit=limit)
    return {"data": events}
