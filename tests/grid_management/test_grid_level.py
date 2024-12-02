import pytest
from unittest.mock import Mock
from core.grid_management.grid_level import GridLevel, GridLevelState

class TestGridLevel:

    def test_grid_level_initialization(self):
        grid_level = GridLevel(price=1000, state=GridLevelState.READY_TO_BUY)
        
        assert grid_level.price == 1000
        assert grid_level.state == GridLevelState.READY_TO_BUY
        assert grid_level.buy_orders == []
        assert grid_level.sell_orders == []

    def test_place_buy_order(self):
        grid_level = GridLevel(price=1000, state=GridLevelState.READY_TO_BUY)
        buy_order = Mock()
        
        grid_level.place_buy_order(buy_order)
        
        assert len(grid_level.buy_orders) == 1
        assert grid_level.buy_orders[0] == buy_order
        assert grid_level.state == GridLevelState.READY_TO_SELL

    def test_place_sell_order(self):
        grid_level = GridLevel(price=1000, state=GridLevelState.READY_TO_SELL)
        sell_order = Mock()
        
        grid_level.place_sell_order(sell_order)
        
        assert len(grid_level.sell_orders) == 1
        assert grid_level.sell_orders[0] == sell_order

    def test_can_place_buy_order(self):
        grid_level = GridLevel(price=1000, state=GridLevelState.READY_TO_BUY)
        
        assert grid_level.can_place_buy_order() == True
        
        grid_level.place_buy_order(Mock())
        
        assert grid_level.can_place_buy_order() == False

    def test_can_place_sell_order(self):
        grid_level = GridLevel(price=1000, state=GridLevelState.READY_TO_SELL)
        
        assert grid_level.can_place_sell_order() == True
        
        grid_level.place_sell_order(Mock())
        
        assert grid_level.can_place_sell_order() == True  # Placing sell order doesn't change state

    def test_reset_buy_level_cycle(self):
        grid_level = GridLevel(price=1000, state=GridLevelState.READY_TO_SELL)
        
        grid_level.reset_buy_level_cycle()
        
        assert grid_level.state == GridLevelState.READY_TO_BUY