import asyncio
from contextlib import asynccontextmanager
import logging
import os
import sys
from typing import Any, Dict, List

# ==============================================================================
# sys.path 자동 경로 주입 (어느 디렉토리에서 실행하든 절대/상대 경로 임포트 오류 방지)
# ==============================================================================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from websocket_manager import ws_manager

from db.database import init_db
from iot.provider_factory import get_device_provider
from routes.devices import router as devices_router
from routes.vision import router as vision_router
from routes.classroom import router as classroom_router, SEATS, ATTENDANCE_LOG

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("backend.main")

DEFAULT_ALLOWED_ORIGINS = "http://localhost:3000,http://127.0.0.1:3000"


def get_allowed_origins() -> List[str]:
    """.env의 CORS_ALLOW_ORIGINS를 파싱해 허용 출처 목록을 반환합니다."""
    raw = os.getenv("CORS_ALLOW_ORIGINS", DEFAULT_ALLOWED_ORIGINS)
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


# ==============================================================================
# 백그라운드 센서 데이터 시뮬레이터 (Random Walk 및 센서 자동 갱신)
# ==============================================================================
async def sensor_simulator_task() -> None:
    """3초마다 온습도 센서 및 센서 상태를 자동 갱신하고 WebSocket으로 브로드캐스트합니다."""
    logger.info("Starting background sensor simulator task...")
    provider = get_device_provider()
    while True:
        try:
            await asyncio.sleep(3.0)
            dht_val = await provider.read_sensor_value("dht_sensor")
            reed_val = await provider.read_sensor_value("reed_switch")
            flame_val = await provider.read_sensor_value("flame_sensor")

            # 활성 연결이 있을 때만 WebSocket 브로드캐스트
            if ws_manager.active_connections:
                await ws_manager.broadcast({
                    "type": "sensor_tick",
                    "sensors": {
                        "dht_sensor": dht_val,
                        "reed_switch": reed_val,
                        "flame_sensor": flame_val,
                    }
                })
        except asyncio.CancelledError:
            logger.info("Sensor simulator task stopped.")
            break
        except Exception as exc:
            logger.warning(f"Error in sensor simulator task: {exc}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. 시작 시 DB 초기화 시도 (DB 미실행 시에도 서버가 다운되지 않도록 예외 처리)
    try:
        init_db()
        logger.info("Database schema checked and seed data synced.")
    except Exception as exc:
        logger.warning(f"Database initialization deferred (check MySQL running): {exc}")

    # 2. 백그라운드 센서 시뮬레이터 시작
    sim_task = asyncio.create_task(sensor_simulator_task())
    yield
    # 3. 종료 시 정리
    sim_task.cancel()


app = FastAPI(
    title="Smart Classroom IoT & Vision System API",
    version="1.0.0",
    description="스마트 교실 출입, 출석, 좌석, 재실 통합 관리 백엔드 API",
    lifespan=lifespan,
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(devices_router)
app.include_router(vision_router)
app.include_router(classroom_router)


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """백엔드 서버 헬스체크 엔드포인트"""
    return {"status": "ok", "message": "Backend server is running healthy."}


@app.get("/")
async def root() -> Dict[str, Any]:
    """루트 안내 엔드포인트"""
    return {
        "message": "Smart Classroom IoT & Vision Backend is active.",
        "docs_url": "/docs",
        "health_url": "/health"
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """실시간 디바이스 상태 및 교실 좌석/출석 스트리밍용 WebSocket 엔드포인트"""
    await ws_manager.connect(websocket)
    provider = get_device_provider()

    # 연결 즉시 현재 전체 스냅샷 전송
    try:
        all_devs = await provider.get_all_statuses()
        await websocket.send_json({
            "type": "init_state",
            "devices": all_devs,
            "seats": list(SEATS.values()),
            "attendance": ATTENDANCE_LOG,
        })
    except Exception as exc:
        logger.warning(f"Error sending init state over WebSocket: {exc}")

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as exc:
        logger.warning(f"WebSocket connection closed with error: {exc}")
        ws_manager.disconnect(websocket)
