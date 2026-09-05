"""
Database connection and helper functions for MySQL/MariaDB.
Compliant with .agents/rules/db-rules.md and .agents/skills/db-integration/SKILL.md.
"""

import json
import logging
import os
from contextlib import contextmanager
from typing import Any, Dict, Generator, List, Optional

from dotenv import load_dotenv
import pymysql
import pymysql.cursors

# .env 로드 (backend 디렉토리 기준)
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BACKEND_DIR, ".env"))

logger = logging.getLogger("backend.db")

# DB 접속 설정 상수
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "smart_control")

# 디바이스 초기 시드 데이터 (AGENTS.md 팀 정보 기준: 액추에이터 5종 + 센서 5종)
DEFAULT_SEED_DEVICES = [
    {"id": "servo_door", "name": "MG90S 서보모터(자동문)", "kind": "servo"},
    {"id": "seat_led", "name": "좌석 LED", "kind": "led"},
    {"id": "neopixel_seat", "name": "네오픽셀", "kind": "neopixel"},
    {"id": "buzzer", "name": "부저", "kind": "buzzer"},
    {"id": "relay_light", "name": "릴레이(교실 조명)", "kind": "relay"},
    {"id": "cam_entrance", "name": "FHD 출입 웹캠", "kind": "camera"},
    {"id": "cam_classroom", "name": "FHD 교실 웹캠", "kind": "camera"},
    {"id": "reed_switch", "name": "리드스위치", "kind": "reed_switch"},
    {"id": "flame_sensor", "name": "불꽃 센서", "kind": "flame_sensor"},
    {"id": "dht_sensor", "name": "온습도 센서", "kind": "dht11"},
]


def get_db_connection(include_database: bool = True) -> pymysql.Connection:
    """
    MySQL/MariaDB 데이터베이스 커넥션을 생성하여 반환합니다.
    """
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME if include_database else None,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )


@contextmanager
def get_db_cursor() -> Generator[pymysql.cursors.DictCursor, None, None]:
    """
    안전한 트랜잭션 관리와 자동 반환을 위한 Cursor 컨텍스트 매니저.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        yield cursor
        conn.commit()
    except Exception as exc:
        conn.rollback()
        logger.error(f"Database query error occurred, rolling back transaction: {exc}")
        raise
    finally:
        cursor.close()
        conn.close()


def init_db() -> None:
    """
    서버 시작 시 데이터베이스 및 테이블 존재 여부를 확인하고, 없으면 생성합니다.
    시드 디바이스 목록을 ON DUPLICATE KEY UPDATE로 안전하게 반영합니다.
    """
    try:
        # 1. 데이터베이스 생성 확인
        root_conn = get_db_connection(include_database=False)
        with root_conn.cursor() as cur:
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
            )
        root_conn.commit()
        root_conn.close()

        # 2. 테이블 스키마 생성 및 시드 적용
        with get_db_cursor() as cursor:
            # devices 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS devices (
                    id VARCHAR(50) PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    kind VARCHAR(30) NOT NULL,
                    desired_state VARCHAR(30) NULL,
                    current_state VARCHAR(30) NULL,
                    desired_value JSON NULL,
                    current_value JSON NULL,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # sensor_readings 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sensor_readings (
                    id INT AUTO_INCREMENT PRIMARY KEY, -- MySQL-only
                    device_id VARCHAR(50) NOT NULL,
                    value FLOAT NULL,
                    unit VARCHAR(20) NULL,
                    value_json JSON NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
                );
            """)

            # control_log 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS control_log (
                    id INT AUTO_INCREMENT PRIMARY KEY, -- MySQL-only
                    device_id VARCHAR(50) NOT NULL,
                    action VARCHAR(50) NOT NULL,
                    value JSON NULL,
                    actor VARCHAR(20) NOT NULL DEFAULT 'user',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
                );
            """)

            # vision_events 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vision_events (
                    id INT AUTO_INCREMENT PRIMARY KEY, -- MySQL-only
                    event_type VARCHAR(50) NOT NULL,
                    detected BOOLEAN NOT NULL DEFAULT FALSE,
                    count INT NOT NULL DEFAULT 0,
                    confidence FLOAT NULL,
                    details JSON NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 디바이스 시드 데이터 적용 (상태는 덮어쓰지 않고 name, kind만 갱신)
            seed_query = """
                INSERT INTO devices (id, name, kind)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    name = VALUES(name),
                    kind = VALUES(kind);
            """
            for dev in DEFAULT_SEED_DEVICES:
                cursor.execute(seed_query, (dev["id"], dev["name"], dev["kind"]))

        logger.info("Database schema initialized and seed devices verified successfully.")
    except Exception as exc:
        logger.error(f"Failed to initialize database: {exc}")
        raise


def get_device(device_id: str) -> Optional[Dict[str, Any]]:
    """단일 디바이스 정보를 조회합니다."""
    with get_db_cursor() as cursor:
        cursor.execute("SELECT * FROM devices WHERE id = %s;", (device_id,))
        return cursor.fetchone()


def get_all_devices() -> List[Dict[str, Any]]:
    """등록된 모든 디바이스 목록을 조회합니다."""
    with get_db_cursor() as cursor:
        cursor.execute("SELECT * FROM devices ORDER BY id ASC;")
        return cursor.fetchall()


def update_device_desired_state(
    device_id: str,
    desired_state: str,
    desired_value: Optional[Any] = None
) -> None:
    """
    대시보드 또는 트리거 규칙에 의해 요청된 디바이스의 목표 상태(desired_state/value)를 갱신합니다.
    """
    serialized_value = json.dumps(desired_value) if desired_value is not None else None
    query = """
        UPDATE devices
        SET desired_state = %s,
            desired_value = %s
        WHERE id = %s;
    """
    with get_db_cursor() as cursor:
        cursor.execute(query, (desired_state, serialized_value, device_id))


def update_device_current_state(
    device_id: str,
    current_state: str,
    current_value: Optional[Any] = None
) -> None:
    """
    라즈베리파이 또는 Mock 디바이스가 보고한 실제 상태(current_state/value)를 갱신합니다.
    """
    serialized_value = json.dumps(current_value) if current_value is not None else None
    query = """
        UPDATE devices
        SET current_state = %s,
            current_value = %s
        WHERE id = %s;
    """
    with get_db_cursor() as cursor:
        cursor.execute(query, (current_state, serialized_value, device_id))


def log_sensor_reading(
    device_id: str,
    value: Optional[float] = None,
    unit: Optional[str] = None,
    value_json: Optional[Dict[str, Any]] = None
) -> None:
    """
    센서의 측정값을 sensor_readings 테이블에 기록합니다.
    단일 수치형은 value+unit에, 복합 데이터(온습도 등)는 value_json에 저장합니다.
    """
    serialized_json = json.dumps(value_json) if value_json is not None else None
    query = """
        INSERT INTO sensor_readings (device_id, value, unit, value_json)
        VALUES (%s, %s, %s, %s);
    """
    with get_db_cursor() as cursor:
        cursor.execute(query, (device_id, value, unit, serialized_json))


def get_sensor_history(device_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """특정 센서의 최근 측정 이력을 반환합니다."""
    query = """
        SELECT * FROM sensor_readings
        WHERE device_id = %s
        ORDER BY created_at DESC
        LIMIT %s;
    """
    with get_db_cursor() as cursor:
        cursor.execute(query, (device_id, limit))
        return cursor.fetchall()


def log_control_action(
    device_id: str,
    action: str,
    value: Any = None,
    actor: str = "user"
) -> None:
    """
    액추에이터 제어 명령 이력을 control_log 테이블에 기록합니다.
    actor: 'user' 또는 'device'
    """
    serialized_value = json.dumps(value) if value is not None else None
    query = """
        INSERT INTO control_log (device_id, action, value, actor)
        VALUES (%s, %s, %s, %s);
    """
    with get_db_cursor() as cursor:
        cursor.execute(query, (device_id, action, serialized_value, actor))


def get_recent_control_logs(
    device_id: Optional[str] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """최근 제어 이력을 조회합니다."""
    if device_id:
        query = """
            SELECT * FROM control_log
            WHERE device_id = %s
            ORDER BY created_at DESC
            LIMIT %s;
        """
        params = (device_id, limit)
    else:
        query = """
            SELECT * FROM control_log
            ORDER BY created_at DESC
            LIMIT %s;
        """
        params = (limit,)

    with get_db_cursor() as cursor:
        cursor.execute(query, params)
        return cursor.fetchall()


def log_vision_event(
    event_type: str,
    detected: bool = True,
    count: int = 0,
    confidence: Optional[float] = None,
    details: Optional[Dict[str, Any]] = None
) -> None:
    """
    영상인식 클라이언트(얼굴 인식, ROI 착석 판정 등)의 감지 이벤트를 기록합니다.
    """
    serialized_details = json.dumps(details) if details is not None else None
    query = """
        INSERT INTO vision_events (event_type, detected, count, confidence, details)
        VALUES (%s, %s, %s, %s, %s);
    """
    with get_db_cursor() as cursor:
        cursor.execute(query, (event_type, detected, count, confidence, serialized_details))


def get_recent_vision_events(limit: int = 20) -> List[Dict[str, Any]]:
    """최근 비전 감지 이벤트를 조회합니다."""
    query = """
        SELECT * FROM vision_events
        ORDER BY created_at DESC
        LIMIT %s;
    """
    with get_db_cursor() as cursor:
        cursor.execute(query, (limit,))
        return cursor.fetchall()
