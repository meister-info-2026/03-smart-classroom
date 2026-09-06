"""
test_hardware_gpio.py
--------------------------------------------------------------------------------
[라즈베리파이 5 담당자를 위한 하드웨어 배선 및 GPIO 1분 자가진단 도구]

* 목적:
  - 백엔드 연결 전, 라즈베리파이 5의 물리 부품(부저, 서보모터, LED, 센서)이 정상 작동하는지 확인합니다.
  - RP1 칩셋 환경에서 lgpio 및 gpiozero 핀 팩토리가 정상 로드되는지 검증합니다.

* 실행 방법 (라즈베리파이 터미널):
  python test_hardware_gpio.py
--------------------------------------------------------------------------------
"""

import os
import sys
import time
from dotenv import load_dotenv

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

load_dotenv()

# GPIOZERO Pin Factory 기본값 설정 (RP1 칩셋 대응)
os.environ.setdefault("GPIOZERO_PIN_FACTORY", "lgpio")

print("=" * 65)
print("🍓 [라즈베리파이 5] 하드웨어 GPIO 배선 자가 진단 도구")
print("=" * 65)

# 1. gpiozero 및 lgpio 라이브러리 로드 검증
try:
    from gpiozero import Buzzer, AngularServo, LED, DigitalInputDevice, OutputDevice
    from gpiozero.pins.lgpio import LGPIOFactory
    print("✅ [패키지 확인] gpiozero 및 lgpio 모듈이 정상적으로 로드되었습니다.")
except ImportError as e:
    print("\n❌ [패키지 오류] gpiozero 또는 lgpio 라이브러리를 찾을 수 없습니다.")
    print("라즈베리파이 5(RP1 칩셋)에서는 PyPI pip 빌드 오류를 방지하기 위해")
    print("OS 기본 APT 패키지와 --system-site-packages 가상환경을 사용해야 합니다:\n")
    print("  1) 시스템 APT 패키지 설치:")
    print("     sudo apt update && sudo apt install -y python3-gpiozero python3-lgpio\n")
    print("  2) 가상환경 생성 (시스템 패키지 상속):")
    print("     cd pi")
    print("     python3 -m venv --system-site-packages venv")
    print("     source venv/bin/activate\n")
    print("  3) 순수 Python 의존성 설치:")
    print("     pip install -r requirements.txt\n")
    if sys.platform == "win32":
        print("💡 (안내: 현재 Windows PC 환경입니다. 실제 GPIO 배선 테스트는 라즈베리파이 5에서 실행하세요.)\n")
    sys.exit(1)

# 2. 핀 번호 정의 (PRD v2.0 기준)
BUZZER_PIN = 17
SERVO_PIN = 18
LIGHT_RELAY_PIN = 22
FLAME_PIN = 23
REED_PIN = 27
SEAT_LED_PINS = [5, 6, 13]

def test_buzzer():
    print(f"\n[1/4] 부저 테스트 (GPIO {BUZZER_PIN})...")
    try:
        buzzer = Buzzer(BUZZER_PIN)
        print("  🔊 삐- 소리가 2회 울립니다.")
        buzzer.beep(on_time=0.2, off_time=0.2, n=2, background=False)
        buzzer.close()
        print("  ✅ 부저 테스트 완료")
    except Exception as e:
        print(f"  ⚠️ 부저 테스트 실패: {e}")

def test_servo():
    print(f"\n[2/4] MG90S 자동문 서보모터 테스트 (GPIO {SERVO_PIN})...")
    try:
        servo = AngularServo(SERVO_PIN, min_angle=0, max_angle=90, min_pulse_width=0.0005, max_pulse_width=0.0024)
        print("  🚪 문 열림 (90도 회전)...")
        servo.angle = 90
        time.sleep(1.5)
        print("  🚪 문 닫힘 (0도 복귀)...")
        servo.angle = 0
        time.sleep(1.0)
        servo.close()
        print("  ✅ 서보모터 테스트 완료")
    except Exception as e:
        print(f"  ⚠️ 서보모터 테스트 실패: {e}")

def test_leds():
    print(f"\n[3/4] 좌석 LED 테스트 (GPIO {SEAT_LED_PINS})...")
    try:
        leds = [LED(pin) for pin in SEAT_LED_PINS]
        print("  💡 LED 순차 점등...")
        for i, led in enumerate(leds):
            led.on()
            time.sleep(0.3)
            led.off()
        for led in leds:
            led.close()
        print("  ✅ LED 테스트 완료")
    except Exception as e:
        print(f"  ⚠️ LED 테스트 실패: {e}")

def test_sensors():
    print(f"\n[4/4] 리드스위치(GPIO {REED_PIN}) 및 불꽃센서(GPIO {FLAME_PIN}) 읽기...")
    try:
        reed = DigitalInputDevice(REED_PIN, pull_up=True)
        flame = DigitalInputDevice(FLAME_PIN)
        print(f"  🧲 리드스위치 상태: {'감지(닫힘)' if reed.is_active else '미감지(열림)'} (값: {reed.value})")
        print(f"  🔥 불꽃센서 상태: {'화재 감지(위험)!' if flame.is_active else '정상'} (값: {flame.value})")
        reed.close()
        flame.close()
        print("  ✅ 센서 읽기 완료")
    except Exception as e:
        print(f"  ⚠️ 센서 읽기 실패: {e}")

if __name__ == "__main__":
    print(f"[*] GPIOZERO_PIN_FACTORY = {os.environ.get('GPIOZERO_PIN_FACTORY')}")
    test_buzzer()
    test_servo()
    test_leds()
    test_sensors()
    print("\n🎉 모든 자가진단 항목을 실행했습니다.")
    print("이제 백엔드와 연동하기 위해 'python 01_ping_backend.py'를 실행하세요!\n")
