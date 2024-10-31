import time
from ..order import OrderType
from .order_execution_strategy import OrderExecutionStrategy

class BacktestOrderExecutionStrategy(OrderExecutionStrategy):
    async def execute_order(self, order_type: OrderType, pair: str, quantity: float, price: float) -> dict:
        # Simulate immediate order execution
        order_id = f"backtest-{int(time.time())}"
        return {'id': order_id, 'pair': pair, 'type': order_type.name, 'filled_qty': quantity, 'price': price, 'status': 'filled'}