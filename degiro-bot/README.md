# DeGiro 자동매매 봇

이동평균 교차(MA crossover) + RSI 필터 기반의 규칙 트레이딩 봇입니다. DeGiro 계좌에 실제 주문을 넣습니다.

## ⚠️ 반드시 읽어주세요

- **DeGiro는 공식 공개 API를 제공하지 않습니다.** 이 봇은 비공식 라이브러리인 [`degiro-connector`](https://pypi.org/project/degiro-connector/)를 사용합니다. 리버스 엔지니어링된 API라 DeGiro 쪽에서 예고 없이 동작을 바꾸거나 계정을 제한할 수 있습니다. DeGiro 이용약관을 직접 확인하고 본인 책임 하에 사용하세요.
- **실제 자금이 움직입니다.** `I_UNDERSTAND_THE_RISK=true`로 설정하기 전까지는 주문을 실제로 넣지 않고 로그만 남깁니다(드라이런). 실거래를 켜기 전에 반드시 로그를 확인하세요.
- 이 코드는 투자 자문이 아니며, 전략의 수익성을 보장하지 않습니다. 소액/과거 데이터로 충분히 검증 후 사용하세요.
- `degiro_client.py`는 실제 설치된 `degiro-connector==3.0.36` 소스 코드를 직접 읽고 그에 맞춰 작성되었습니다 (`connect`/`get_client_details`/`get_update`/`check_order`/`confirm_order` 액션과 `Order` 모델의 실제 필드명·enum 값 기준). 다만 계좌 잔고/포지션 데이터(`get_update`의 `portfolio`/`cashFunds`/`totalPortfolio`)는 라이브러리가 타입을 강제하지 않는 **원시 JSON**이라, DeGiro가 알려진 "`{name, value}` 쌍의 리스트" 포맷을 그대로 쓴다는 전제 하에 파싱했습니다 — 실제 계좌로 테스트하지 못했으니 실거래 전에 반드시 아래 "실제 계좌 연결 확인"을 먼저 실행하세요.

## 실제 계좌 연결 확인 (실거래 전 필수)

`.env`/`config.yaml`을 채운 뒤, **주문은 전혀 넣지 않는** 읽기 전용 점검 스크립트를 먼저 실행하세요:

```bash
python -m scripts.inspect_account
```

로그인, 포트폴리오 총액/현금, 각 종목 포지션·시세 이력을 출력합니다. `WARNING`이 뜨면(`portfolio value came back as 0`, `no price history returned` 등) `src/degiro_client.py`의 파싱 로직(`_flatten_value_list`, `_iter_positions`, `get_price_history`)이 실제 계좌 응답 형식과 안 맞는다는 뜻이니, 필요하면 `raw=True`로 원본 JSON을 찍어보고 맞춰 수정하세요.

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

## 백테스트: S&P 500과 비교

실거래 전에, 과거 데이터로 이 전략이 S&P 500 매수 후 보유(buy & hold)보다 나은지 확인할 수 있습니다.

```bash
pip install yfinance   # 로컬 CSV를 쓸 경우 불필요

python -m scripts.run_backtest --yf-symbol IWDA.AS --yf-benchmark ^GSPC --years 5
# 또는 로컬 CSV로 (date,close 컬럼):
python -m scripts.run_backtest --symbol-csv data/iwda.csv --benchmark-csv data/spx.csv
```

DeGiro 계좌 없이 순수 가격 데이터만으로 동작하며, 주문도 넣지 않습니다. 백테스트 엔진(`src/backtest.py`)은 실거래 봇과 **동일한** `size_order`/`stop_loss_triggered` 로직을 재사용하므로, 여기서 나온 결과가 실제 봇의 동작과 어긋나지 않습니다.

⚠️ **이 샌드박스 환경은 외부 네트워크(Yahoo Finance 등)에 접근할 수 없어, 실제 과거 데이터로 결과를 직접 확인하지는 못했습니다.** 대신 합성 데이터로 CLI 자체는 끝까지 실행해 동작을 검증했고, 그 과정에서 한 가지를 발견했습니다:

**기본 설정(`config.example.yaml`)의 RSI 필터는 사실상 거래가 거의 안 나오는 조합입니다.** "골든크로스(최근 상승 모멘텀) + RSI가 낮음(과매도)"은 서로 잘 안 겹치는 조건이라, 대부분의 기간에서 매수 신호 자체가 거의 발생하지 않습니다 — 신호가 없으면 계속 현금 보유 상태라 S&P 500을 이길 수가 없습니다. 실거래 전에 `config.yaml`의 `rsi_buy_below`/`rsi_sell_above`를 조정해서 실제로 거래가 발생하는지, 그리고 그 결과가 지수를 이기는지 백테스트로 먼저 확인하는 걸 권장합니다.

## 파라미터 튜닝 (그리드서치 + 아웃오브샘플 검증)

전략이 거의 거래를 안 하거나 지수를 못 이긴다면, 파라미터를 자동으로 여러 조합 돌려서 어떤 조합이 나은지 찾을 수 있습니다.

```bash
python -m scripts.optimize_strategy --yf-symbol IWDA.AS --yf-benchmark ^GSPC --years 8
```

`fast_ma_period`/`slow_ma_period`/`rsi_buy_below`/`rsi_sell_above` 조합을 그리드로 돌려 학습 구간(기본 70%)에서 수익률 상위 5개를 뽑고, **한 번도 보지 않은 나머지 구간(테스트 구간)에서 다시 검증**합니다.

⚠️ **과최적화(overfitting) 주의**: 학습 구간에서 1등인 조합이 테스트 구간에서도 이긴다는 보장은 전혀 없습니다 (실제로 합성 데이터로 돌려보면 학습 구간 1위 조합들이 테스트 구간에서는 대부분 지는 걸 확인했습니다). **학습·테스트 구간 모두에서 지수를 이기는 조합만 신뢰**하세요. 그런 조합이 하나도 없다면, 이 전략 형태(이동평균 교차 + RSI) 자체가 이 종목/기간에서 지수를 이기기 어렵다는 뜻일 수 있습니다 — 그 결과도 유의미한 정보입니다.

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
│   ├── vector_strategy.py  # 백테스트용 벡터화 신호 생성 (strategy.py와 결과 일치 검증됨)
│   ├── backtest.py           # 백테스트 엔진 (실거래와 동일한 risk 로직 재사용)
│   ├── optimize.py            # 파라미터 그리드서치 + train/test 분할
│   └── bot.py                 # 메인 루프
├── scripts/
│   ├── inspect_account.py  # 실거래 전 읽기 전용 계좌 연결 확인
│   ├── run_backtest.py      # S&P 500 대비 백테스트 CLI
│   └── optimize_strategy.py # 파라미터 튜닝 + 아웃오브샘플 검증 CLI
└── tests/                     # indicators/strategy/risk/backtest 단위 테스트
```
