-- ==============================================================================
-- Smart IoT & Vision Control System — Database Initialization Script
-- ==============================================================================

-- MySQL-only (db-migration 스킬에서 Supabase 전환 시 이 두 줄은 제거한다)
CREATE DATABASE IF NOT EXISTS smart_control
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE smart_control;

-- 1. 디바이스 테이블 (센서 및 액추에이터 관리)
CREATE TABLE IF NOT EXISTS devices (
  id VARCHAR(50) PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  kind VARCHAR(30) NOT NULL,
  desired_state VARCHAR(30) NULL,   -- 대시보드/트리거가 지정한 목표 상태
  current_state VARCHAR(30) NULL,   -- 라즈베리파이(또는 Mock)가 보고한 실제 상태
  desired_value JSON NULL,          -- 서보 각도, LED 색상/밝기 등 복합 제어값
  current_value JSON NULL,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 2. 센서 측정치 기록 테이블
CREATE TABLE IF NOT EXISTS sensor_readings (
  id INT AUTO_INCREMENT PRIMARY KEY, -- MySQL-only
  device_id VARCHAR(50) NOT NULL,
  value FLOAT NULL,                  -- 단일 수치형 센서값 (예: 리드스위치 0/1 등)
  unit VARCHAR(20) NULL,
  value_json JSON NULL,              -- 다중 측정값 (예: 온습도 {"temperature_c": 24.5, "humidity_pct": 55.0})
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
);

-- 3. 제어 이력 테이블
CREATE TABLE IF NOT EXISTS control_log (
  id INT AUTO_INCREMENT PRIMARY KEY, -- MySQL-only
  device_id VARCHAR(50) NOT NULL,
  action VARCHAR(50) NOT NULL,
  value JSON NULL,
  actor VARCHAR(20) NOT NULL DEFAULT 'user', -- 'user' 또는 'device'
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
);

-- 4. 비전 감지 이벤트 테이블
CREATE TABLE IF NOT EXISTS vision_events (
  id INT AUTO_INCREMENT PRIMARY KEY, -- MySQL-only
  event_type VARCHAR(50) NOT NULL,
  detected BOOLEAN NOT NULL DEFAULT FALSE,
  count INT NOT NULL DEFAULT 0,
  confidence FLOAT NULL,
  details JSON NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ==============================================================================
-- AGENTS.md 팀 정보 시드 데이터 (센서 5종 + 액추에이터 5종)
-- 재실행해도 현재/목표 상태를 덮어쓰지 않도록 desired/current_state는 시드에서 제외
-- ==============================================================================
INSERT INTO devices (id, name, kind) VALUES
  -- 액추에이터 (5종)
  ('servo_door', 'MG90S 서보모터(자동문)', 'servo'),
  ('seat_led', '좌석 LED', 'led'),
  ('neopixel_seat', '네오픽셀', 'neopixel'),
  ('buzzer', '부저', 'buzzer'),
  ('relay_light', '릴레이(교실 조명)', 'relay'),
  -- 센서 (5종)
  ('cam_entrance', 'FHD 출입 웹캠', 'camera'),
  ('cam_classroom', 'FHD 교실 웹캠', 'camera'),
  ('reed_switch', '리드스위치', 'reed_switch'),
  ('flame_sensor', '불꽃 센서', 'flame_sensor'),
  ('dht_sensor', '온습도 센서', 'dht11')
ON DUPLICATE KEY UPDATE
  name = VALUES(name),
  kind = VALUES(kind);
