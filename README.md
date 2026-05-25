# APIF auto trading draft

This project is a safe first draft for a user-controlled stock auto trading tool.
The user chooses the stock, buy price, sell price, and quantity. The program only
executes those preset rules.

Current mode is `DRY_RUN`. It does not send real orders. When a condition is met,
it writes a simulated order to `logs/orders.csv`.

## Step 1: basic flow

- Wait until the latest price is less than or equal to the buy price.
- Send one buy order.
- Wait until the latest price is greater than or equal to the sell price.
- Send one sell order.
- Stop after one buy and one sell.

## Step 2: safety controls

The program now checks safety rules before it accepts a plan or places an order.

- `allowed_symbols`: only these stock codes can be traded.
- `max_order_amount`: maximum order amount, calculated as price times quantity.
- `max_quantity_per_order`: maximum shares per order.
- `require_market_hours`: blocks orders outside the configured market time.
- `stop_file`: if this file exists, every new order is blocked.

The emergency stop file defaults to `STOP_TRADING`. Creating that file in the
project folder is enough to stop new orders.

## Step 3: API readiness

Before connecting the real NH/Namu QV Open API, run the readiness check:

```powershell
python -m apif_bot.doctor
```

Secrets and account values must stay out of GitHub. Copy `.env.example` to `.env`
on your PC and fill in local values there:

```text
APIF_NAMU_QV_PATH=
APIF_NAMU_ACCOUNT_NO=
APIF_NAMU_ACCOUNT_PRODUCT_CODE=
APIF_NAMU_BRIDGE_COMMAND=
APIF_ENABLE_LIVE_TRADING=NO
```

Keep `APIF_ENABLE_LIVE_TRADING=NO` until mock trading has been verified.

The downloaded Namu OpenAPI folder should contain `bin/wmca.dll`. If that DLL is
32-bit and your Python is 64-bit, direct DLL loading will not work. In that case,
use either 32-bit Python or a small 32-bit helper process that talks to this
Python program.

The helper process protocol is documented in `docs/bridge_protocol.md`.
The native 32-bit helper draft is in `native/namu_bridge`.

데스크톱 컨트롤러 열기:

```powershell
powershell -ExecutionPolicy Bypass -File tools\open_controller.ps1
```

You can test the bridge path with the mock helper:

```powershell
python -m apif_bot.cli --quote-source namu --max-ticks 1 --config config/trade_plan.example.json
```

For the mock helper, set this local `.env` value first:

```text
APIF_NAMU_BRIDGE_COMMAND=python apif_bot/mock_bridge.py
```

## Run tests

```powershell
python -m unittest discover -s tests
```

## Run with sample prices

```powershell
python -m apif_bot.cli --config config/trade_plan.example.json --price-csv tests/sample_prices.csv
```

## Run with manual price input

```powershell
python -m apif_bot.cli --config config/trade_plan.example.json
```

## Live-ready monitoring

실전 전 감시용 설정은 `config/trade_plan.live_ready.json`입니다.

```powershell
python -m apif_bot.cli --quote-source namu --config config/trade_plan.live_ready.json
```

이 설정도 `DRY_RUN`입니다. 실제 주문은 보내지 않고 모의 주문 로그만 남깁니다.
손절가 이하로 떨어지면 목표 매도가를 기다리지 않고 손절 매도 조건으로 처리합니다.

## Example config

```json
{
  "symbol": "005930",
  "name": "Samsung Electronics",
  "buy_price": 70000,
  "stop_loss_price": 68000,
  "sell_price": 75000,
  "quantity": 1,
  "mode": "DRY_RUN",
  "poll_seconds": 3,
  "safety": {
    "allowed_symbols": ["005930"],
    "max_order_amount": 1000000,
    "max_quantity_per_order": 10,
    "require_market_hours": false,
    "market_start": "09:00",
    "market_end": "15:20",
    "stop_file": "STOP_TRADING"
  }
}
```

## Next step

The next development step is broker integration preparation:

1. Install and verify the NH/Namu QV Open API module.
2. Confirm the official quote and order function names.
3. Add a real quote provider.
4. Implement `NamuQvBroker` with mock-investment first.
5. Keep live trading disabled until the mock account has been tested.

Real account trading can cause financial loss. Keep `DRY_RUN` until the broker
module, account permissions, and mock trading behavior are verified.
