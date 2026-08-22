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
├── src/
│   ├── config.py            # 설정/자격증명 로딩
│   ├── indicators.py        # SMA, RSI 계산
│   ├── strategy.py          # 매매 신호 생성
│   ├── risk.py               # 포지션 사이징, 손절, 일일 손실 서킷 브레이커
│   ├── degiro_client.py     # degiro-connector 래퍼 (인증/시세/주문)
│   └── bot.py                 # 메인 루프
└── tests/                     # indicators/strategy/risk 단위 테스트
```
