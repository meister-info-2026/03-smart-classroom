"""
Classroom seats and attendance management router.
Manages 6 classroom seats and real-time attendance status.
"""

from datetime import datetime
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from schemas.devices import SeatReserveRequest, SeatStatus
from websocket_manager import ws_manager

logger = logging.getLogger("backend.routes.classroom")
router = APIRouter()

# 6석 좌석 상태 메모리 캐시 (초기 학생 명단 등록)
SEATS: Dict[int, Dict[str, Any]] = {
    1: {"seat_id": 1, "status": "AVAILABLE", "student_id": None, "student_name": None, "reserved_at": None, "occupied_at": None},
    2: {"seat_id": 2, "status": "AVAILABLE", "student_id": None, "student_name": None, "reserved_at": None, "occupied_at": None},
    3: {"seat_id": 3, "status": "AVAILABLE", "student_id": None, "student_name": None, "reserved_at": None, "occupied_at": None},
    4: {"seat_id": 4, "status": "AVAILABLE", "student_id": None, "student_name": None, "reserved_at": None, "occupied_at": None},
    5: {"seat_id": 5, "status": "AVAILABLE", "student_id": None, "student_name": None, "reserved_at": None, "occupied_at": None},
    6: {"seat_id": 6, "status": "AVAILABLE", "student_id": None, "student_name": None, "reserved_at": None, "occupied_at": None},
}

# 학생 기본 데이터베이스 (PRD 및 AGENTS.md 팀원 명단 연동)
REGISTERED_STUDENTS = {
    "202601": "김재민",
    "202602": "김다온",
    "202603": "김하준",
    "202604": "윤상훈",
    "202605": "이도건",
    "202606": "서종혁",
}

# 출석 기록 리스트
ATTENDANCE_LOG: List[Dict[str, Any]] = [
    {"student_id": "202601", "student_name": "김재민", "status": "미출석", "seat_id": None, "check_in_time": None},
    {"student_id": "202602", "student_name": "김다온", "status": "미출석", "seat_id": None, "check_in_time": None},
    {"student_id": "202603", "student_name": "김하준", "status": "미출석", "seat_id": None, "check_in_time": None},
    {"student_id": "202604", "student_name": "윤상훈", "status": "미출석", "seat_id": None, "check_in_time": None},
    {"student_id": "202605", "student_name": "이도건", "status": "미출석", "seat_id": None, "check_in_time": None},
    {"student_id": "202606", "student_name": "서종혁", "status": "미출석", "seat_id": None, "check_in_time": None},
]


@router.get("/api/seats")
async def get_seats() -> Dict[str, Any]:
    """6개 좌석의 전체 상태 목록을 반환합니다."""
    return {"data": list(SEATS.values())}


@router.post("/api/seats/{seat_id}/reserve")
async def reserve_seat(seat_id: int, req: SeatReserveRequest) -> Dict[str, Any]:
    """특정 좌석을 학생에게 예약(배정)합니다."""
    if seat_id not in SEATS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "SEAT_NOT_FOUND", "message": f"Seat {seat_id} does not exist."}},
        )

    seat = SEATS[seat_id]
    seat["status"] = "RESERVED"
    seat["student_id"] = req.student_id
    seat["student_name"] = req.student_name
    seat["reserved_at"] = datetime.now().strftime("%H:%M:%S")

    # 출석부 정보 업데이트
    for record in ATTENDANCE_LOG:
        if record["student_id"] == req.student_id:
            record["seat_id"] = seat_id
            record["status"] = "좌석선택완료"
            break

    # WebSocket 브로드캐스트
    await ws_manager.broadcast({
        "type": "seat_update",
        "seat": seat,
        "seats": list(SEATS.values()),
    })

    return {"data": seat}


@router.post("/api/seats/{seat_id}/release")
async def release_seat(seat_id: int) -> Dict[str, Any]:
    """좌석 점유/예약을 해제합니다."""
    if seat_id not in SEATS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "SEAT_NOT_FOUND", "message": f"Seat {seat_id} does not exist."}},
        )

    seat = SEATS[seat_id]
    released_student = seat.get("student_id")
    seat["status"] = "AVAILABLE"
    seat["student_id"] = None
    seat["student_name"] = None
    seat["reserved_at"] = None
    seat["occupied_at"] = None

    if released_student:
        for record in ATTENDANCE_LOG:
            if record["student_id"] == released_student:
                record["seat_id"] = None
                record["status"] = "퇴실완료"
                break

    await ws_manager.broadcast({
        "type": "seat_update",
        "seat": seat,
        "seats": list(SEATS.values()),
    })

    return {"data": seat}


@router.get("/api/attendance")
async def get_attendance() -> Dict[str, Any]:
    """전체 학생 출석 및 재실 목록을 반환합니다."""
    return {"data": ATTENDANCE_LOG}
