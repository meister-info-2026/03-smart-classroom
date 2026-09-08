"""
02_servo_door_daemon_mock.py
--------------------------------------------------------------------------------
[라즈베리파이 5 담당자를 위한 2단계 실습: 자동문 폴링 데몬 (Mock 모드)]

* 목적:
    - 백엔드 교무실에 3초마다 "문 열어야 하나요?" 하고 물어봅니다(GET desired-state).
    - 아직 물리적 모터를 꽂지 않았으므로, print() 문으로 화면에 문 열림을 시뮬레이션합니다.
    - 문을 열고 나면 교무실에 "문 열었습니다!"라고 보고(POST state)합니다.
    - 교사 대시보드 웹 화면에 내 보고가 실시간으로 반영되는 것을 확인합니다.

* 실행 방법:
    python 02_servo_door_daemon_mock.py
--------------------------------------------------------------------------------
"""

import os
import sys
import time
import requests
from dotenv import load_dotenv

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
        sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    except Exception:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace", line_buffering=True)

# 1. 설정 불러오기
load_dotenv()
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
DEVICE_API_KEY = os.getenv("DEVICE_API_KEY", "CLASS_2026_09_05_v1_0_0")
DEVICE_ID = "servo_door"

HEADERS = {
    "X-Device-Api-Key": DEVICE_API_KEY,
    "Content-Type": "application/json",
}

print("=" * 65, flush=True)
print("🍓 [라즈베리파이 5] 자동문 서보모터 폴링 데몬 시작 (Mock 모드)", flush=True)
print(f"📍 백엔드 주소: {BACKEND_URL}", flush=True)
print(f"🔑 사용 API 키: {DEVICE_API_KEY[:8]}********", flush=True)
print(f"🏷️ 감시 대상 디바이스: {DEVICE_ID}", flush=True)
print("⏱️ 폴링 주기: 3초 (Ctrl + C 를 누르면 종료됩니다)", flush=True)
print("=" * 65, flush=True)

# 현재 내가 기억하고 있는 문의 상태 (초기: CLOSED)
my_current_state = "CLOSED"


def check_desired_state():
    """교무실에 '자동문 상태를 어떻게 해야 하나요?' 하고 물어보는 함수 (GET)"""
    url = f"{BACKEND_URL}/api/v1/devices/{DEVICE_ID}/desired-state"
    try:
        res = requests.get(url, headers=HEADERS, timeout=3)
        if res.status_code == 200:
            data = res.json().get("data", {})
            return data.get("desired_state"), data.get("desired_value")
        elif res.status_code == 401:
            print("\n❌ [401 에러] API 키가 일치하지 않습니다! pi/.env의 DEVICE_API_KEY를 확인하세요.", flush=True)
            return None, None
        elif res.status_code == 404:
            print(f"\n❌ [404 에러] '{DEVICE_ID}'라는 디바이스를 백엔드에서 찾을 수 없습니다.", flush=True)
            return None, None
        else:
            print(f"⚠️ 상태 조회 오류: HTTP {res.status_code}", flush=True)
            return None, None
    except requests.exceptions.RequestException as e:
        print(f"⚠️ 백엔드 접속 대기 중... ({e.__class__.__name__})", flush=True)
        return None, None


def report_state(new_state: str, new_value: dict = None):
    """실제로 동작을 마친 후 교무실에 '보고서'를 제출하는 함수 (POST)"""
    url = f"{BACKEND_URL}/api/v1/devices/{DEVICE_ID}/state"
    payload = {
        "current_state": new_state,
        "current_value": new_value or {},
    }
    try:
        res = requests.post(url, headers=HEADERS, json=payload, timeout=3)
        if res.status_code == 200:
            print(f"  📤 [보고 완료] 교무실에 '{new_state}' 상태 보고 성공! (대시보드 실시간 동기화)", flush=True)
        else:
            print(f"  ⚠️ 보고 실패: HTTP {res.status_code}", flush=True)
    except Exception as e:
        print(f"  ⚠️ 보고 중 오류 발생: {e}", flush=True)


def main():
    global my_current_state
    
    cycle = 0
    while True:
        cycle += 1
        desired_state, desired_value = check_desired_state()

        if desired_state:
            # 교무실의 목표 상태가 내 현재 상태와 다르면 동작 개시!
            if desired_state != my_current_state:
                print(f"\n⚡ [새 지시 감지!] 교무실 지시: {desired_state} (기존: {my_current_state})", flush=True)
                
                if desired_state == "OPEN":
                    print("🚪 -------------------------------------------------------------", flush=True)
                    print("🚪 [MG90S 서보모터 디버깅 출력] 위잉~ 서보모터가 90도로 돌아가며 문이 활짝 열립니다!", flush=True)
                    print("🚪 (※ 나중에 실제 파이에 모터를 연결하면 여기에 servo.angle = 90 코드가 들어갑니다)", flush=True)
                    print("🚪 -------------------------------------------------------------", flush=True)
                    my_current_state = "OPEN"
                    report_state("OPEN", {"angle": 90})

                elif desired_state == "CLOSED":
                    print("🚪 -------------------------------------------------------------", flush=True)
                    print("🚪 [MG90S 서보모터 디버깅 출력] 찰칵! 서보모터가 0도로 복귀하며 문이 닫힙니다.", flush=True)
                    print("🚪 -------------------------------------------------------------", flush=True)
                    my_current_state = "CLOSED"
                    report_state("CLOSED", {"angle": 0})
            else:
                # 상태 변경 없음 (평화로운 대기)
                print(f"[{time.strftime('%H:%M:%S')}] 힐끔 확인 #{cycle}: 현재 상태 유지 ({my_current_state})", flush=True)
        else:
            # 백엔드에 아직 desired_state가 설정되지 않았거나(초기 NULL) 조회 실패
            print(f"[{time.strftime('%H:%M:%S')}] 힐끔 확인 #{cycle}: 목표 상태 대기 중 (현재: {my_current_state})", flush=True)

        time.sleep(3)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🛑 [종료] 라즈베리파이 데몬을 안전하게 종료합니다. 수고하셨습니다!\n")
