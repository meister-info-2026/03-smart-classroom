"""
Endpoints for IoT device control and status queries.
Compliant with .agents/rules/api-rules.md and .agents/skills/iot-endpoint-generator/SKILL.md.
"""

import os
import logging
from typing import Any, Dict, Optional
from fastapi import APIRouter, Header, HTTPException, status
from fastapi.responses import JSONResponse

from schemas.devices import DeviceControlRequest, DeviceStateReportRequest
from iot.provider_factory import get_device_provider
from db.database import (
    get_all_devices,
    get_device,
    get_sensor_history,
    get_recent_control_logs,
    update_device_desired_state,
    update_device_current_state,
)
from websocket_manager import ws_manager

logger = logging.getLogger("backend.routes.devices")
router = APIRouter()

DEVICE_API_KEY = os.getenv("DEVICE_API_KEY", "CLASS_2026_09_05_v1_0_0")


def verify_device_api_key(x_device_api_key: Optional[str] = Header(None)) -> None:
    """디바이스향 엔드포인트 전용 API Key 인증 검증 (api-rules.md 준수)."""
    if not x_device_api_key or x_device_api_key != DEVICE_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "UNAUTHORIZED", "message": "Invalid or missing X-Device-Api-Key"}},
        )


# ==============================================================================
# 1. 사용자향 엔드포인트 (대시보드 / 프론트엔드용)
# ==============================================================================

@router.get("/api/devices")
async def list_devices() -> Dict[str, Any]:
    """모든 디바이스 목록 및 실시간 상태를 반환합니다."""
    try:
        provider = get_device_provider()
        db_devices = get_all_devices()
        live_statuses = await provider.get_all_statuses()
        live_map = {item["id"]: item for item in live_statuses}

        merged = []
        for dev in db_devices:
            dev_id = dev["id"]
            if dev_id in live_map:
                dev["current_state"] = live_map[dev_id].get("current_state", dev.get("current_state"))
                dev["current_value"] = live_map[dev_id].get("current_value", dev.get("current_value"))
            merged.append(dev)

        return {"data": merged}
    except Exception as exc:
        logger.error(f"Error in list_devices: {exc}")
        return {"data": []}


@router.get("/api/devices/{device_id}")
async def get_device_detail(device_id: str) -> Dict[str, Any]:
    """특정 디바이스의 상세 상태를 조회합니다."""
    provider = get_device_provider()
    dev_status = await provider.get_device_status(device_id)
    if not dev_status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "DEVICE_NOT_FOUND", "message": f"Device '{device_id}' not found"}},
        )
    return {"data": dev_status}


@router.post("/api/devices/{device_id}/control")
async def control_device(device_id: str, req: DeviceControlRequest) -> Dict[str, Any]:
    """액추에이터의 상태를 제어하고 대시보드에 실시간 브로드캐스트합니다."""
    provider = get_device_provider()
    result = await provider.set_actuator_state(
        device_id=device_id,
        desired_state=req.desired_state,
        value=req.desired_value,
        operator=req.operator,
    )

    # 대시보드 실시간 동기화를 위해 WebSocket 브로드캐스트
    await ws_manager.broadcast({
        "type": "device_update",
        "device_id": device_id,
        "desired_state": req.desired_state,
        "current_state": result.get("current_state", req.desired_state),
        "current_value": result.get("current_value"),
    })

    return {"data": result}


@router.post("/api/devices/{device_id}/reset-alert")
async def reset_alert(device_id: str) -> Dict[str, Any]:
    """경보성 디바이스(불꽃 센서 등)의 수동 해제 처리 (db-rules.md 준수)."""
    provider = get_device_provider()
    if hasattr(provider, "reset_alert_device"):
        provider.reset_alert_device(device_id)

    await ws_manager.broadcast({
        "type": "device_update",
        "device_id": device_id,
        "current_state": "SAFE",
        "current_value": {"flame_detected": False},
    })

    return {"data": {"id": device_id, "status": "alert_reset_success"}}


@router.get("/api/devices/{device_id}/history")
async def get_device_history(device_id: str, limit: int = 50) -> Dict[str, Any]:
    """특정 디바이스의 최근 센서 측정치 또는 제어 이력을 반환합니다."""
    readings = get_sensor_history(device_id, limit=limit)
    if readings:
        return {"data": readings}
    logs = get_recent_control_logs(device_id, limit=limit)
    return {"data": logs}


# ==============================================================================
# 2. 디바이스향 엔드포인트 (라즈베리파이 5 / 하드웨어 폴링 계약 인터페이스)
# ==============================================================================

@router.get("/api/v1/devices/{device_id}/desired-state")
async def get_desired_state(
    device_id: str,
    x_device_api_key: Optional[str] = Header(None),
) -> Dict[str, Any]:
    """라즈베리파이 데몬이 desired-state를 폴링할 때 호출하는 엔드포인트."""
    verify_device_api_key(x_device_api_key)
    dev = get_device(device_id)
    if not dev:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "NOT_FOUND", "message": f"Device {device_id} not found"}},
        )
    return {
        "data": {
            "id": dev["id"],
            "desired_state": dev.get("desired_state"),
            "desired_value": dev.get("desired_value"),
            "updated_at": str(dev.get("updated_at")),
        }
    }


@router.post("/api/v1/devices/{device_id}/state")
async def report_device_state(
    device_id: str,
    req: DeviceStateReportRequest,
    x_device_api_key: Optional[str] = Header(None),
) -> Dict[str, Any]:
    """라즈베리파이 데몬이 실제 하드웨어 반영 결과를 보고하는 엔드포인트."""
    verify_device_api_key(x_device_api_key)
    update_device_current_state(device_id, req.current_state, req.current_value)

    await ws_manager.broadcast({
        "type": "device_update",
        "device_id": device_id,
        "current_state": req.current_state,
        "current_value": req.current_value,
    })

    return {"data": {"id": device_id, "status": "reported"}}
