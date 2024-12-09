import time
from typing import Optional
from ..order import Order, OrderSide, OrderType, OrderStatus
from .order_execution_strategy import OrderExecutionStrategy

class BacktestOrderExecutionStrategy(OrderExecutionStrategy):
    async def execute_market_order(
        self, 
        order_side: OrderSide, 
        pair: str, 
        quantity: float,
        price: float
    ) -> Optional[Order]:
        order_id = f"backtest-{int(time.time())}"
        return Order(
            identifier=order_id,
            status=OrderStatus.OPEN,
            order_type=OrderType.MARKET,
            side=order_side,
            price=price,
            average=100,
            amount=1,
            filled=quantity,
            remaining=0,
            timestamp=1695890800,
            datetime="111",
            last_trade_timestamp=1,
            symbol=pair,
            time_in_force="GTC"
        )
    
    async def execute_limit_order(
        self, 
        order_side: OrderSide, 
        pair: str, 
        quantity: float, 
        price: float
    ) -> Optional[Order]:
        order_id = f"backtest-{int(time.time())}"
        return Order(
            identifier=order_id,
            status=OrderStatus.OPEN,
            order_type=OrderType.LIMIT,
            side=order_side,
            price=price,
            average=price,
            amount=quantity,
            filled=0,
            remaining=quantity,
            timestamp=1695890800,
            datetime="",
            last_trade_timestamp=1,
            symbol=pair,
            time_in_force="GTC"
        )
    
    async def get_order(
        self, 
        order_id: str
    ) -> Optional[Order]:
        return Order(
            identifier=order_id,
            status=OrderStatus.OPEN,
            order_type=OrderType.LIMIT,
            side=OrderSide.BUY,
            price=100,
            average=100,
            amount=1,
            filled=1,
            remaining=0,
            timestamp=1695890800,
            datetime="111",
            last_trade_timestamp=1,
            symbol="ETH/BTC",
            time_in_force="GTC"
        )