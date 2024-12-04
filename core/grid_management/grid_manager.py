import logging
from typing import List, Optional, Tuple
import numpy as np
from strategies.strategy_type import StrategyType
from strategies.spacing_type import SpacingType
from .grid_level import GridLevel, GridCycleState
from ..order_handling.order import Order

class GridManager:
    def __init__(self, config_manager):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config_manager = config_manager
        self.initial_balance: float = self.config_manager.get_initial_balance()
        self.strategy_type: StrategyType = self.config_manager.get_strategy_type()
        self.price_grids: List[float]
        self.central_price: float
        self.sorted_buy_grids: List[float]
        self.sorted_sell_grids: List[float]
        self.grid_levels: dict[float, GridLevel] = {}
    
    def initialize_grids_and_levels(self) -> None:
        self.price_grids, self.central_price = self._calculate_price_grids_and_central_price()

        if self.strategy_type == StrategyType.SIMPLE_GRID:
            self.sorted_buy_grids = [price_grid for price_grid in self.price_grids if price_grid <= self.central_price]
            self.sorted_sell_grids = [price_grid for price_grid in self.price_grids if price_grid > self.central_price]
            self.grid_levels = {price: GridLevel(price, GridCycleState.READY_TO_BUY if price <= self.central_price else GridCycleState.READY_TO_SELL) for price in self.price_grids}
        
        elif self.strategy_type == StrategyType.HEDGED_GRID:
            self.sorted_buy_grids = self.price_grids[:-1]  # Buy from all except the top grid
            self.sorted_sell_grids = self.price_grids[1:]  # Sell on all except the bottom grid
            self.grid_levels = {price: GridLevel(price, GridCycleState.READY_TO_BUY_SELL) for price in self.price_grids}
    
    def get_crossed_grid_level(
        self, 
        current_price: float, 
        previous_price: float, 
        sell: bool = False
    ) -> Optional[GridLevel]:
        grid_list = self.sorted_sell_grids if sell else self.sorted_buy_grids
        for grid_price in grid_list:
            if (sell and previous_price < grid_price <= current_price) or (not sell and previous_price >= grid_price >= current_price):
                return self._get_grid_level(grid_price)
        return None

    def find_lowest_completed_buy_grid(self) -> Optional[GridLevel]:
        for price in self.sorted_buy_grids:
            grid_level = self.grid_levels.get(price)
            if grid_level and grid_level.can_place_sell_order():
                return grid_level
        return None

    def get_order_size_per_grid(
        self,
        current_price: float
    ) -> float:
        total_grids = len(self.grid_levels)
        order_size = self.initial_balance / total_grids / current_price
        return order_size
    
    def reset_grid_cycle(
        self, 
        buy_grid_level: GridLevel
    ) -> None:
        # buy_grid_level.reset_buy_level_cycle()
        self.logger.debug(f"Buy Grid level at price {buy_grid_level.price} is reset and ready for the next buy/sell cycle.")
    
    def _get_grid_level(
        self, 
        price: float
    ) -> Optional[GridLevel]:
        return self.grid_levels.get(price)
    
    def get_paired_sell_level(self, buy_grid_level: GridLevel) -> Optional[GridLevel]:
        """
        Retrieves the grid level immediately above the provided buy grid level.

        Args:
            buy_grid_level: The GridLevel for which the paired sell level is needed.

        Returns:
            The paired sell grid level, or None if no paired level exists.
        """
        current_index = self.sorted_buy_grids.index(buy_grid_level.price)
        if current_index + 1 < len(self.sorted_sell_grids):
            next_price = self.sorted_sell_grids[current_index + 1]
            return self._get_grid_level(next_price)
        return None
    
    def mark_buy_order_pending(self, grid_level: GridLevel, order: Order) -> None:
        """
        Marks a grid level as having a pending buy order.

        Args:
            grid_level: The grid level to update.
            order: The Order object representing the pending buy order.
        """
        grid_level.place_buy_order(order)
        self.logger.info(f"Buy order placed and marked as pending at grid level {grid_level.price}.")

    def mark_sell_order_pending(self, grid_level: GridLevel, order: Order) -> None:
        """
        Marks a grid level as having a pending sell order.

        Args:
            grid_level: The grid level to update.
            order: The Order object representing the pending sell order.
        """
        grid_level.place_sell_order(order)
        self.logger.info(f"Sell order placed and marked as pending at grid level {grid_level.price}.")
    
    def complete_buy_order(self, grid_level: GridLevel) -> None:
        """
        Marks the pending buy order as filled and transitions the grid level to READY_TO_SELL.

        Args:
            grid_level: The grid level where the buy order was completed.
        """
        grid_level.complete_buy_order()
        self.logger.info(f"Buy order completed at grid level {grid_level.price}.")
    
    def complete_sell_order(self, grid_level: GridLevel) -> None:
        """
        Marks the pending sell order as filled and resets the grid level.

        Args:
            grid_level: The grid level where the sell order was completed.
        """
        grid_level.complete_sell_order()
        self.logger.info(f"Sell order completed and grid level reset at {grid_level.price}.")

    def _extract_grid_config(self) -> Tuple[float, float, int, str]:
        """
        Extracts grid configuration parameters from the configuration manager.
        """
        bottom_range = self.config_manager.get_bottom_range()
        top_range = self.config_manager.get_top_range()
        num_grids = self.config_manager.get_num_grids()
        spacing_type = self.config_manager.get_spacing_type()
        return bottom_range, top_range, num_grids, spacing_type

    def _calculate_price_grids_and_central_price(self) -> Tuple[List[float], float]:
        """
        Calculates price grids and the central price based on the configuration.

        Returns:
            Tuple[List[float], float]: A tuple containing:
                - grids (List[float]): The list of calculated grid prices.
                - central_price (float): The central price of the grid.
        """
        bottom_range, top_range, num_grids, spacing_type = self._extract_grid_config()
        
        if spacing_type == SpacingType.ARITHMETIC:
            grids = np.linspace(bottom_range, top_range, num_grids)
            central_price = (top_range + bottom_range) / 2
        elif spacing_type == SpacingType.GEOMETRIC:
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