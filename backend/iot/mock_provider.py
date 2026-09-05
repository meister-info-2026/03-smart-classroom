"""
Mock Device Provider for local development and testing on Windows PC.
Simulates all 10 devices defined in AGENTS.md and PRD v2.0 without physical hardware.
"""

import asyncio
import logging
import random
from typing import Any, Dict, List, Optional

from iot.base import DeviceProvider
from db.database import (
    get_all_devices,
    get_device,
    update_device_current_state,
    update_device_desired_state,
    log_control_action,
    log_sensor_reading,
)

logger = logging.getLogger("backend.iot.mock")


class MockDeviceProvider(DeviceProvider):
    """
    라즈베리파이 5 대신 Windows PC에서 동작하는 Mock IoT 디바이스 제어기.
    - 자동문(서보모터): OPEN 시 5초 후 자동으로 CLOSED로 복귀 시뮬레이션
    - 온습도 센서: Random Walk로 자연스러운 온습도 데이터 생성
    - 리드스위치: 문 상태에 연동된 닫힘(1)/열림(0) 감지
    - 불꽃 센서: 경보 디바이스 수동 해제 원칙 준수
    """

    def __init__(self) -> None:
        # 메모리 상태 캐시
        self._states: Dict[str, Dict[str, Any]] = {
            "servo_door": {"state": "CLOSED", "value": {"angle": 0}},
            "seat_led": {"state": "OFF", "value": {"brightness": 0}},
            "neopixel_seat": {"state": "OFF", "value": {"mode": "off", "color": "#000000"}},
            "buzzer": {"state": "OFF", "value": {"frequency": 0}},
            "relay_light": {"state": "OFF", "value": {"enabled": False}},
            "cam_entrance": {"state": "ONLINE", "value": {"fps": 30, "resolution": "1080p"}},
            "cam_classroom": {"state": "ONLINE", "value": {"fps": 30, "resolution": "1080p"}},
            "reed_switch": {"state": "CLOSED", "value": {"contact": 1}},
            "flame_sensor": {"state": "SAFE", "value": {"flame_detected": False}},
            "dht_sensor": {"state": "ACTIVE", "value": {"temperature_c": 23.5, "humidity_pct": 52.0}},
        }
        self._door_auto_close_task: Optional[asyncio.Task] = None
        self._buzzer_auto_off_task: Optional[asyncio.Task] = None

    async def get_device_status(self, device_id: str) -> Optional[Dict[str, Any]]:
        """특정 디바이스의 최신 상태를 반환합니다."""
        if device_id in self._states:
            mem = self._states[device_id]
            return {
                "id": device_id,
                "current_state": mem["state"],
                "current_value": mem["value"],
            }
        # DB 조회 폴백
        try:
            db_dev = get_device(device_id)
            if db_dev:
                return db_dev
        except Exception as exc:
            logger.warning(f"Failed to query DB for device {device_id}: {exc}")
        return None

    async def set_actuator_state(
        self,
        device_id: str,
        desired_state: str,
        value: Optional[Any] = None,
        operator: str = "user"
    ) -> Dict[str, Any]:
        """액추에이터의 상태를 변경하고 동작을 시뮬레이션합니다."""
        logger.info(f"[MockProvider] set_actuator_state: {device_id} -> {desired_state} (by {operator})")

        # 메모리 상태 업데이트
        if device_id not in self._states:
            self._states[device_id] = {}

        self._states[device_id]["state"] = desired_state
        if value is not None:
            self._states[device_id]["value"] = value

        # DB 동기화
        try:
            update_device_desired_state(device_id, desired_state, value)
            update_device_current_state(device_id, desired_state, value)
            log_control_action(device_id, desired_state, value, operator)
        except Exception as exc:
            logger.warning(f"DB update failed during set_actuator_state: {exc}")

        # 1. 자동문(MG90S 서보모터) 제어 특수 로직: OPEN 시 5초 후 자동 닫힘 (PRD E-08)
        if device_id == "servo_door":
            if desired_state == "OPEN":
                self._states["servo_door"]["value"] = {"angle": 90}
                # 리드스위치 연동: 문이 열렸으므로 0(열림)
                self._states["reed_switch"]["state"] = "OPEN"
                self._states["reed_switch"]["value"] = {"contact": 0}

                # 기존 예약 태스크가 있으면 취소 후 재등록
                if self._door_auto_close_task and not self._door_auto_close_task.done():
                    self._door_auto_close_task.cancel()
                self._door_auto_close_task = asyncio.create_task(self._auto_close_door_after_delay(5.0))
            elif desired_state == "CLOSED":
                self._states["servo_door"]["value"] = {"angle": 0}
                self._states["reed_switch"]["state"] = "CLOSED"
                self._states["reed_switch"]["value"] = {"contact": 1}

        # 2. 부저 제어 특수 로직: ON 시 2초 후 자동 OFF (경고음 비프음 시뮬레이션)
        if device_id == "buzzer" and desired_state == "ON":
            if self._buzzer_auto_off_task and not self._buzzer_auto_off_task.done():
                self._buzzer_auto_off_task.cancel()
            self._buzzer_auto_off_task = asyncio.create_task(self._auto_off_buzzer_after_delay(2.0))

        return {
            "id": device_id,
            "status": "success",
            "current_state": desired_state,
            "current_value": self._states[device_id].get("value"),
        }

    async def _auto_close_door_after_delay(self, delay_seconds: float) -> None:
        """5초 후 자동으로 자동문을 닫는 백그라운드 시뮬레이션 태스크."""
        try:
            await asyncio.sleep(delay_seconds)
            logger.info("[MockProvider] Auto-closing MG90S servo door (5s elapsed)...")
            await self.set_actuator_state("servo_door", "CLOSED", {"angle": 0}, operator="device")
        except asyncio.CancelledError:
            pass

    async def _auto_off_buzzer_after_delay(self, delay_seconds: float) -> None:
        """2초 후 부저를 자동으로 끄는 백그라운드 시뮬레이션 태스크."""
        try:
            await asyncio.sleep(delay_seconds)
            logger.info("[MockProvider] Auto-stopping buzzer warning beep...")
            await self.set_actuator_state("buzzer", "OFF", {"frequency": 0}, operator="device")
        except asyncio.CancelledError:
            pass

    async def read_sensor_value(self, device_id: str) -> Dict[str, Any]:
        """센서 값을 읽어옵니다. 온습도 센서는 Random Walk로 약간씩 변동시킵니다."""
        if device_id == "dht_sensor":
            curr_temp = self._states["dht_sensor"]["value"].get("temperature_c", 23.5)
            curr_hum = self._states["dht_sensor"]["value"].get("humidity_pct", 52.0)

            # Random walk (-0.2 ~ +0.2)
            new_temp = round(max(18.0, min(30.0, curr_temp + random.uniform(-0.2, 0.2))), 1)
            new_hum = round(max(30.0, min(80.0, curr_hum + random.uniform(-0.5, 0.5))), 1)

            val_dict = {"temperature_c": new_temp, "humidity_pct": new_hum}
            self._states["dht_sensor"]["value"] = val_dict
            try:
                log_sensor_reading("dht_sensor", value_json=val_dict)
            except Exception as exc:
                logger.warning(f"Failed to log sensor reading for dht_sensor: {exc}")

            return {
                "id": "dht_sensor",
                "state": "ACTIVE",
                "value": val_dict,
            }

        elif device_id == "reed_switch":
            val = self._states["reed_switch"]["value"]
            return {"id": "reed_switch", "state": self._states["reed_switch"]["state"], "value": val}

        elif device_id == "flame_sensor":
            val = self._states["flame_sensor"]["value"]
            return {"id": "flame_sensor", "state": self._states["flame_sensor"]["state"], "value": val}

        # 기타 센서
        mem = self._states.get(device_id, {"state": "ONLINE", "value": {}})
        return {"id": device_id, "state": mem.get("state"), "value": mem.get("value")}

    async def get_all_statuses(self) -> List[Dict[str, Any]]:
        """등록된 모든 디바이스의 최신 상태 목록을 반환합니다."""
        results = []
        for dev_id, info in self._states.items():
            results.append({
                "id": dev_id,
                "current_state": info.get("state"),
                "current_value": info.get("value"),
            })
        return results

    def reset_alert_device(self, device_id: str) -> None:
        """경보성 디바이스(불꽃 센서 등)의 수동 해제 처리."""
        if device_id == "flame_sensor":
            self._states["flame_sensor"]["state"] = "SAFE"
            self._states["flame_sensor"]["value"] = {"flame_detected": False}
            try:
                update_device_current_state("flame_sensor", "SAFE", {"flame_detected": False})
            except Exception as exc:
                logger.warning(f"Failed to reset flame alert in DB: {exc}")
