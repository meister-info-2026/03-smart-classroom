# 라즈베리파이 5 하드웨어 제어 데몬 (pi)

## 💡 [라즈베리파이 5 (Debian 12 Bookworm / Debian 13 Trixie) 전용 가이드]

### [중요] RP1 칩셋 및 gpiozero / lgpio 안내
- 라즈베리파이 5(RP1 칩셋)에서는 PyPI에서 `pip install lgpio` 시 C 컴파일 에러가 발생합니다.
- 따라서 `gpiozero`와 `lgpio`는 라즈베리파이의 시스템 APT 패키지로 설치하고, 가상환경 생성 시 `--system-site-packages` 옵션을 적용합니다.

### 1) 시스템 APT 패키지 설치
```bash
sudo apt update && sudo apt install -y python3-gpiozero python3-lgpio
```

### 2) 가상환경 생성 (--system-site-packages 적용)
```bash
cd pi
python3 -m venv --system-site-packages venv
source venv/bin/activate
```

### 3) 가상환경 내부 패키지 설치
```bash
pip install -r requirements.txt
```
