# DeGiro 자동매매 봇

이동평균 교차(MA crossover) + RSI 필터 기반의 규칙 트레이딩 봇입니다. DeGiro 계좌에 실제 주문을 넣습니다.

## ⚠️ 반드시 읽어주세요

- **DeGiro는 공식 공개 API를 제공하지 않습니다.** 이 봇은 비공식 라이브러리인 [`degiro-connector`](https://pypi.org/project/degiro-connector/)를 사용합니다. 리버스 엔지니어링된 API라 DeGiro 쪽에서 예고 없이 동작을 바꾸거나 계정을 제한할 수 있습니다. DeGiro 이용약관을 직접 확인하고 본인 책임 하에 사용하세요.
- **실제 자금이 움직입니다.** `I_UNDERSTAND_THE_RISK=true`로 설정하기 전까지는 주문을 실제로 넣지 않고 로그만 남깁니다(드라이런). 실거래를 켜기 전에 반드시 로그를 확인하세요.
- 이 코드는 투자 자문이 아니며, 전략의 수익성을 보장하지 않습니다. 소액/과거 데이터로 충분히 검증 후 사용하세요.
- `degiro_client.py`는 `degiro-connector` 라이브러리의 일반적인 사용 패턴을 기반으로 작성되었습니다. 설치된 라이브러리 버전에 따라 클래스/메서드 이름이 다를 수 있으니, 실거래 전에 `pip install -r requirements.txt` 후 `python -c "import degiro_connector"`로 실제 API를 확인하고 필요시 `src/degiro_client.py`를 라이브러리 버전에 맞게 조정하세요.

## 전략

- **매수**: 단기 이동평균(fast MA)이 장기 이동평균(slow MA)을 상향 돌파(골든크로스) + RSI가 `rsi_buy_below` 미만
- **매도**: 단기 이동평균이 장기 이동평균을 하향 돌파(데드크로스) + RSI가 `rsi_sell_above` 초과
- 매수한 포지션은 진입가 대비 `stop_loss_pct`만큼 하락하면 즉시 손절 매도

## 리스크 관리 (기본 안전장치)

- `max_position_pct`: 종목당 최대 포지션 비중 (포트폴리오 대비)
- `max_order_value`: 주문 1건당 최대 금액 (하드 캡)
- `max_daily_loss_pct`: 하루 손실 한도 — 초과 시 그날은 모든 신규 주문 중단(서킷 브레이커)
- `stop_loss_pct`: 포지션별 손절 비율

## 설치

```bash
cd degiro-bot
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env        # 실제 DeGiro 계정 정보 입력 (커밋 금지)
cp config.example.yaml config.yaml   # 종목/전략/리스크 파라미터 조정
```

`.env`와 `config.yaml`은 `.gitignore`에 포함되어 있어 실수로 커밋되지 않습니다.

## 실행

```bash
python main.py
```

- `I_UNDERSTAND_THE_RISK=false`(기본값)인 동안은 신호가 발생해도 실제 주문 없이 로그만 남깁니다.
- 충분히 로그를 검토했다면 `.env`에서 `I_UNDERSTAND_THE_RISK=true`로 바꾸면 실거래가 시작됩니다.
- `config.yaml`의 `schedule.interval_minutes` 주기로 계속 전략을 평가합니다 (Ctrl+C로 종료).

## 상시 실행 배포

봇은 while-루프로 계속 도는 장기 실행 프로세스입니다. 24시간 켜져 있는 서버(VPS, 홈서버, NAS 등)에 배포해서 상시 실행하세요.

### 방법 1: Docker (권장)

```bash
cp .env.example .env              # 실제 값 입력
cp config.example.yaml config.yaml

docker compose up -d --build      # 빌드 후 백그라운드 실행
docker compose logs -f            # 로그 확인
docker compose down               # 중지
```

- `restart: unless-stopped`로 설정되어 있어 서버 재부팅이나 프로세스 크래시 후 자동으로 다시 시작됩니다.
- `.env`와 `config.yaml`은 이미지에 포함되지 않고 실행 시점에 마운트/주입됩니다 (`.dockerignore`, `docker-compose.yml` 참고) — 이미지를 어디에 올리거나 공유해도 자격증명이 새지 않습니다.
- 이 저장소를 만든 샌드박스 환경에는 Docker 데몬이 없어 실제 빌드는 검증하지 못했습니다. 배포 전에 실제 서버에서 `docker compose build`로 한 번 확인하세요.

### 방법 2: systemd (Docker 없이 리눅스 서버에 직접)

```bash
sudo useradd --system --home /opt/degiro-bot degirobot
sudo mkdir -p /opt/degiro-bot
sudo cp -r . /opt/degiro-bot        # .env, config.yaml 포함해서 복사
cd /opt/degiro-bot
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
sudo chown -R degirobot:degirobot /opt/degiro-bot

sudo cp deploy/degiro-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now degiro-bot
sudo systemctl status degiro-bot
journalctl -u degiro-bot -f         # 로그 확인
```

`deploy/degiro-bot.service`는 `Restart=on-failure`로 크래시 시 자동 재시작하며, 전용 비루트 사용자(`degirobot`)로 실행합니다. 경로(`/opt/degiro-bot`)는 실제 배포 위치에 맞게 수정하세요.

## 테스트

전략/리스크/지표 로직은 DeGiro 연결 없이 순수 함수로 테스트할 수 있습니다:

```bash
pip install pytest
python -m pytest tests/ -v
```

`degiro_client.py`, `bot.py`의 실거래 연동 부분은 실제 계좌/네트워크가 필요해 단위 테스트 대상에서 제외했습니다.

## 구조

```
degiro-bot/
├── main.py                 # 실행 진입점
├── config.example.yaml     # 종목/전략/리스크 설정 예시
├── .env.example             # 자격증명 예시
├── Dockerfile / docker-compose.yml / .dockerignore   # 상시 실행 배포 (Docker)
├── deploy/degiro-bot.service                          # 상시 실행 배포 (systemd)
├── src/
│   ├── config.py            # 설정/자격증명 로딩
│   ├── indicators.py        # SMA, RSI 계산
│   ├── strategy.py          # 매매 신호 생성
│   ├── risk.py               # 포지션 사이징, 손절, 일일 손실 서킷 브레이커
│   ├── degiro_client.py     # degiro-connector 래퍼 (인증/시세/주문)
│   └── bot.py                 # 메인 루프
└── tests/                     # indicators/strategy/risk 단위 테스트
```
