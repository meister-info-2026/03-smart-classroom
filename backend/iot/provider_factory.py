"""
Device Provider Factory.
Selects and returns the appropriate DeviceProvider based on DEVICE_MODE (.env).
"""

import os
from typing import Optional
from iot.base import DeviceProvider
from iot.mock_provider import MockDeviceProvider

_provider_instance: Optional[DeviceProvider] = None


def get_device_provider() -> DeviceProvider:
    """
    현재 설정된 디바이스 모드('mock' or 'hardware')에 맞는 Provider 인스턴스를 반환합니다.
    (1차 시스템에서는 Windows 환경 100% 동작을 위해 MockDeviceProvider를 기본 사용)
    """
    global _provider_instance
    if _provider_instance is None:
        mode = os.getenv("DEVICE_MODE", "mock").lower()
        if mode == "mock":
            _provider_instance = MockDeviceProvider()
        else:
            # 4단계 하드웨어 마이그레이션 대비 (HardwareProvider가 없으면 Mock으로 안전 폴백)
            try:
                from iot.hardware_provider import HardwareDeviceProvider
                _provider_instance = HardwareDeviceProvider()
            except ImportError:
                _provider_instance = MockDeviceProvider()
    return _provider_instance
