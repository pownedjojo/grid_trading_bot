import time
from ..order import OrderSide, OrderType
from .order_execution_strategy import OrderExecutionStrategy

class BacktestOrderExecutionStrategy(OrderExecutionStrategy):
    async def execute_market_order(
        self, 
        order_side: OrderSide, 
        pair: str, 
        quantity: float,
        price: float
    ) -> dict:
        order_id = f"backtest-{int(time.time())}"
        return {
            'id': order_id, 
            'price': price,
            'pair': pair, 
            'side': order_side.name, 
            'type': OrderType.MARKET, 
            'filled_qty': quantity, 
            'status': 'filled'
        }
    
    async def execute_limit_order(
        self, 
        order_side: OrderSide, 
        pair: str, 
        quantity: float, 
        price: float
    ) -> dict:
        order_id = f"backtest-{int(time.time())}"
        return {
            'id': order_id, 
            'price': price,
            'pair': pair, 
            'side': order_side.name, 
            'type': OrderType.LIMIT, 
            'filled_qty': quantity, 
            'status': 'filled'
        }