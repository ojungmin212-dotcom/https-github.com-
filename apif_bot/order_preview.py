from __future__ import annotations

from dataclasses import dataclass

from .models import OrderRequest, Side


@dataclass(frozen=True)
class NativeOrderPreview:
    request: OrderRequest
    tr_code: str
    tr_name: str
    order_type_code: str = "00"
    order_type_name: str = "지정가"
    market_code: str = "SOR"
    account_index: int = 1
    live_order_blocked: bool = True

    @property
    def amount(self) -> int:
        return self.request.amount

    def to_log_lines(self) -> list[str]:
        side_name = "매수" if self.request.side == Side.BUY else "매도"
        blocked = "차단됨" if self.live_order_blocked else "허용됨"
        return [
            f"{side_name} 준비: TR {self.tr_code} ({self.tr_name})",
            f"종목 {self.request.symbol}, 수량 {self.request.quantity:,}주, 가격 {self.request.price:,}원",
            f"예상금액 {self.amount:,}원, 주문유형 {self.order_type_name}({self.order_type_code}), 시장 {self.market_code}",
            f"계좌 순번 {self.account_index}, 실제 주문 전송 상태: {blocked}",
        ]


def build_native_order_preview(
    request: OrderRequest,
    *,
    market_code: str = "SOR",
    account_index: int = 1,
    live_order_blocked: bool = True,
) -> NativeOrderPreview:
    _validate_request(request)
    market = market_code.strip().upper() or "SOR"
    if market not in {"SOR", "KRX", "NXT"}:
        raise ValueError("market_code must be one of SOR, KRX, NXT.")
    if account_index < 1:
        raise ValueError("account_index must be at least 1.")

    if request.side == Side.BUY:
        return NativeOrderPreview(
            request=request,
            tr_code="c8102",
            tr_name="주식매수 주문",
            market_code=market,
            account_index=account_index,
            live_order_blocked=live_order_blocked,
        )
    return NativeOrderPreview(
        request=request,
        tr_code="c8101",
        tr_name="주식매도 주문",
        market_code=market,
        account_index=account_index,
        live_order_blocked=live_order_blocked,
    )


def _validate_request(request: OrderRequest) -> None:
    if not request.symbol.isdigit() or len(request.symbol) != 6:
        raise ValueError("symbol must be a 6-digit stock code.")
    if request.price <= 0:
        raise ValueError("price must be greater than 0.")
    if request.quantity <= 0:
        raise ValueError("quantity must be greater than 0.")
