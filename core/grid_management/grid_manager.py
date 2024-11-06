import logging
from typing import List, Optional, Tuple, Union
import numpy as np
from .grid_level import GridLevel, GridCycleState

class GridManager:
    def __init__(self, config_manager):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config_manager = config_manager
        self.initial_balance: float = self.config_manager.get_initial_balance()
        self.grids: List[float]
        self.central_price: float
        self.grids, self.central_price = self._calculate_grids_and_central_price()
        self.sorted_buy_grids: List[float] = [grid for grid in self.grids if grid <= self.central_price]
        self.sorted_sell_grids: List[float] = [grid for grid in self.grids if grid > self.central_price]
        self.grid_levels: dict[float, GridLevel] = {}
    
    def initialize_grid_levels(self) -> None:
        self.grid_levels = {price: GridLevel(price, GridCycleState.READY_TO_BUY if price <= self.central_price else GridCycleState.READY_TO_SELL) for price in self.grids}
    
    def get_grid_level(self, price: float) -> Optional[GridLevel]:
        return self.grid_levels.get(price)
    
    def detect_grid_level_crossing(self, current_price: float, previous_price: float, sell: bool = False):
        grid_list = self.sorted_sell_grids if sell else self.sorted_buy_grids
        for grid_price in grid_list:
            if (sell and previous_price < grid_price <= current_price) or (not sell and previous_price >= grid_price >= current_price):
                return grid_price
        return None

    def find_lowest_completed_buy_grid(self) -> Optional[GridLevel]:
        for price in self.sorted_buy_grids:
            grid_level = self.grid_levels.get(price)
            if grid_level and grid_level.can_place_sell_order():
                return grid_level
        return None

    def get_order_size_per_grid(self, current_price: float) -> float:
        total_grids = len(self.grid_levels)
        order_size = self.initial_balance / total_grids / current_price
        return order_size
    
    async def reset_grid_cycle(self, buy_grid_level: GridLevel) -> None:
        buy_grid_level.reset_buy_level_cycle()
        self.logger.debug(f"Buy Grid level at price {buy_grid_level.price} is reset and ready for the next buy/sell cycle.")

    def _extract_grid_config(self) -> Tuple[float, float, int, str, float]:
        bottom_range = self.config_manager.get_bottom_range()
        top_range = self.config_manager.get_top_range()
        num_grids = self.config_manager.get_num_grids()
        spacing_type = self.config_manager.get_spacing_type()
        percentage_spacing =  self.config_manager.get_percentage_spacing()
        return bottom_range, top_range, num_grids, spacing_type, percentage_spacing

    def _calculate_grids_and_central_price(self) -> Tuple[List[float], float]:
        bottom_range, top_range, num_grids, spacing_type, percentage_spacing = self._extract_grid_config()
        if spacing_type == 'arithmetic':
            grids = np.linspace(bottom_range, top_range, num_grids)
            central_price = (top_range + bottom_range) / 2
        elif spacing_type == 'geometric':
            grids = []
            ratio = (top_range / bottom_range) ** (1 / (num_grids - 1))
            current_price = bottom_range

            for _ in range(num_grids):
                grids.append(current_price)
                current_price *= ratio
                
            central_index = len(grids) // 2
            if num_grids % 2 == 0:
                central_price = (grids[central_index - 1] + grids[central_index]) / 2
            else:
                central_price = grids[central_index]
        return grids, central_price