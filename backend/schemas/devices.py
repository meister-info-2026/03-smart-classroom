"""
Pydantic schemas for devices, vision events, and classroom control.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# 1. 디바이스 제어 및 상태 스키마
class DeviceControlRequest(BaseModel):
    desired_state: str = Field(..., description="목표 상태 (예: 'ON', 'OFF', 'OPEN', 'CLOSED')")
    desired_value: Optional[Any] = Field(None, description="상세 제어값 (예: 서보 각도, 밝기, 색상 등)")
    operator: str = Field("user", description="조작자 ('user' 또는 'device')")


class DeviceStateReportRequest(BaseModel):
    current_state: str = Field(..., description="현재 실제 상태")
    current_value: Optional[Any] = Field(None, description="현재 실제 측정/설정값")


class DeviceResponse(BaseModel):
    id: str
    name: str
    kind: str
    desired_state: Optional[str] = None
    current_state: Optional[str] = None
    desired_value: Optional[Any] = None
    current_value: Optional[Any] = None
    updated_at: Optional[str] = None


# 2. 비전 감지 이벤트 스키마
class VisionEventRequest(BaseModel):
    event_type: str = Field(..., description="이벤트 유형 (face_recognized, face_unrecognized, seat_status, person_detected, flame_detected 등)")
    detected: bool = Field(True, description="감지 여부")
    count: int = Field(0, description="감지된 개수")
    confidence: Optional[float] = Field(None, description="신뢰도 (0.0 ~ 1.0)")
    details: Optional[Dict[str, Any]] = Field(None, description="추가 메타데이터 (student_id, seat_id, bbox 등)")


# 3. 좌석 예약 및 출석 스키마
class SeatReserveRequest(BaseModel):
    student_id: str = Field(..., description="학생 학번")
    student_name: str = Field(..., description="학생 이름")


class SeatStatus(BaseModel):
    seat_id: int = Field(..., description="좌석 번호 (1~6)")
    status: str = Field("AVAILABLE", description="좌석 상태: AVAILABLE, RESERVED, OCCUPIED, MISMATCH")
    student_id: Optional[str] = None
    student_name: Optional[str] = None
    reserved_at: Optional[str] = None
    occupied_at: Optional[str] = None


# 4. 공통 API 응답 래퍼
class ApiResponse(BaseModel):
    data: Any
