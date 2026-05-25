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

## Example config

```json
{
  "symbol": "005930",
  "name": "Samsung Electronics",
  "buy_price": 70000,
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
