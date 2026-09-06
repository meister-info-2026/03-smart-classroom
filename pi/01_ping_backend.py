"""
01_ping_backend.py
--------------------------------------------------------------------------------
[라즈베리파이 5 담당자를 위한 1단계 실습: 교무실(백엔드) 첫 인사 건네기]

* 목적: 라즈베리파이와 백엔드 컴퓨터 사이에 네트워크 통신선이 정상적으로 연결되었는지 확인합니다.
* 실행 방법:
    python 01_ping_backend.py
--------------------------------------------------------------------------------
"""

import os
import sys
import requests
from dotenv import load_dotenv

# 1. pi/.env 파일에서 백엔드 주소를 읽어옵니다.
load_dotenv()
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

print("=" * 60)
print("🍓 [라즈베리파이 5] 백엔드 교무실로 인사를 건넵니다...")
print(f"📍 연결 시도 주소: {BACKEND_URL}/api/devices")
print("=" * 60)

try:
    # 백엔드에 GET 요청으로 현재 등록된 디바이스 목록을 물어봅니다.
    response = requests.get(f"{BACKEND_URL}/api/devices", timeout=3)
    
    if response.status_code == 200:
        data = response.json().get("data", [])
        print("\n🎉 [성공 200 OK] 백엔드 교무실과 연결되었습니다!")
        print(f"📦 교무실 상황판에 등록된 디바이스 개수: {len(data)}개")
        print("\n[등록된 디바이스 목록 미리보기]")
        for dev in data[:5]:
            print(f"  - ID: {dev.get('id'):<15} | 이름: {dev.get('name')}")
        if len(data) > 5:
            print(f"    ... 외 {len(data) - 5}개 부품 등록됨")
        print("\n👉 다음 단계(02_servo_door_daemon_mock.py)로 넘어갈 준비가 끝났습니다!\n")
    else:
        print(f"\n⚠️ [응답 이상] 백엔드가 응답했지만 상태 코드가 다릅니다: {response.status_code}")
        print("응답 내용:", response.text)

except requests.exceptions.ConnectionError:
    print("\n❌ [연결 실패: Connection Error]")
    print("교무실(백엔드) 컴퓨터를 찾을 수 없습니다.")
    print("체크리스트:")
    print(" 1. 백엔드 담당 친구가 서버(FastAPI)를 켰는지 확인하세요 (uvicorn main:app --reload)")
    print(" 2. pi/.env 파일의 BACKEND_URL이 친구 컴퓨터의 IPv4 주소인지 확인하세요")
    print("    (친구 컴퓨터에서 ipconfig를 쳐서 확인한 예: http://192.168.0.25:8000)")
    print(" 3. 친구 컴퓨터의 Windows 방화벽 8000번 포트가 열려있는지 확인하세요\n")

except Exception as e:
    print(f"\n❌ [오류 발생]: {e}\n")
