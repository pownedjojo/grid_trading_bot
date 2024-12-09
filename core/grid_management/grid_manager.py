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
        """
        Initializes the grid levels and assigns their respective states based on the chosen strategy.

        For the `SIMPLE_GRID` strategy:
        - Buy orders are placed on grid levels below the central price.
        - Sell orders are placed on grid levels above the central price.
        - Levels are initialized with `READY_TO_BUY` or `READY_TO_SELL` states.

        For the `HEDGED_GRID` strategy:
        - Grid levels are divided into buy levels (all except the top grid) and sell levels (all except the bottom grid).
        - Buy grid levels are initialized with `READY_TO_BUY`, except for the topmost grid.
        - Sell grid levels are initialized with `READY_TO_SELL`.
        """
        self.price_grids, self.central_price = self._calculate_price_grids_and_central_price()

        if self.strategy_type == StrategyType.SIMPLE_GRID:
            self.sorted_buy_grids = [price_grid for price_grid in self.price_grids if price_grid <= self.central_price]
            self.sorted_sell_grids = [price_grid for price_grid in self.price_grids if price_grid > self.central_price]
            self.grid_levels = {price: GridLevel(price, GridCycleState.READY_TO_BUY if price <= self.central_price else GridCycleState.READY_TO_SELL) for price in self.price_grids}
        
        elif self.strategy_type == StrategyType.HEDGED_GRID:
            self.sorted_buy_grids = self.price_grids[:-1]  # All except the top grid
            self.sorted_sell_grids = self.price_grids[1:]  # All except the bottom grid
            self.grid_levels = {
                price: GridLevel(
                    price,
                    GridCycleState.READY_TO_BUY if price != self.price_grids[-1] else GridCycleState.READY_TO_SELL
                )
                for price in self.price_grids
            }
        self.logger.info(f"Grids and levels initialized. Central price: {self.central_price}")

    def get_order_size_for_grid_level(
        self,
        current_price: float
    ) -> float:
        """
        Calculates the order size for a grid level based on the initial balance, total grids, and current price.

        The order size is determined by evenly distributing the initial balance across all grid levels and adjusting 
        it to reflect the current price.

        Args:
            current_price: The current price of the trading pair.

        Returns:
            The calculated order size as a float.
        """
        total_grids = len(self.grid_levels)
        order_size = self.initial_balance / total_grids / current_price
        return order_size

    def pair_grid_levels(
        self, 
        buy_grid_level: GridLevel, 
        sell_grid_level: GridLevel
    ):
        """
        Dynamically pairs a buy grid level with a sell grid level.
        This method ensures that grid levels are paired correctly, updating their `paired_grid_level` attributes.

        Args:
            buy_grid_level: The `GridLevel` object representing the buy grid level.
            sell_grid_level: The `GridLevel` object representing the sell grid level.
        """
        if buy_grid_level.paired_grid_level or sell_grid_level.paired_grid_level:
            raise ValueError(f"Grid levels {buy_grid_level} or {sell_grid_level} are already paired.")

        buy_grid_level.paired_grid_level = sell_grid_level
        sell_grid_level.paired_grid_level = buy_grid_level
        self.logger.info(f"Paired buy level {buy_grid_level.price} with sell level {sell_grid_level.price}.")
    
    def unpair_grid_levels(
        self, 
        buy_grid_level: GridLevel, 
        sell_grid_level: GridLevel
    ):
        """
        Removes the pairing between a buy grid level and a sell grid level.
        This method resets the `paired_grid_level` attribute for both grid levels, allowing them to be re-paired 
        dynamically if needed.

        Args:
            buy_grid_level: The `GridLevel` object representing the buy grid level.
            sell_grid_level: The `GridLevel` object representing the sell grid level.
        """
        buy_grid_level.paired_grid_level = None
        sell_grid_level.paired_grid_level = None
        self.logger.info(f"Unpaired buy level {buy_grid_level.price} with sell level {sell_grid_level.price}.")

    def get_paired_sell_level(
        self, 
        buy_grid_level: GridLevel
    ) -> Optional[GridLevel]:
        """
        Determines the paired sell level for a given buy grid level based on the strategy type.

        Args:
            buy_grid_level: The buy grid level for which the paired sell level is required.

        Returns:
            The paired sell grid level, or None if no valid level exists.
        """
        if self.strategy_type == StrategyType.SIMPLE_GRID:
            for sell_price in self.sorted_sell_grids:
                sell_level = self.grid_levels[sell_price]

                if sell_level and not sell_level.can_place_sell_order():
                    self.logger.debug(f"Skipping sell level {sell_price} - already has a pending sell order.")
                    continue

                if sell_price > buy_grid_level.price:
                    self.logger.info(f"Paired sell level found at {sell_price} for buy level {buy_grid_level.price}.")
                    return sell_level

            self.logger.warning(f"No paired sell level found for buy level {buy_grid_level.price}.")
            return None
    
        elif self.strategy_type == StrategyType.HEDGED_GRID:
            sorted_prices = sorted(self.price_grids)
            current_index = sorted_prices.index(buy_grid_level.price)

            if current_index + 1 < len(sorted_prices):
                paired_sell_price = sorted_prices[current_index + 1]
                return self.grid_levels[paired_sell_price]
            return None

        else:
            self.logger.error(f"Unsupported strategy type: {self.strategy_type}")
            return None
    
    def mark_buy_order_pending(
        self, 
        grid_level: GridLevel, 
        order: Order
    ) -> None:
        """
        Marks a grid level as having a pending buy order.

        Args:
            grid_level: The grid level to update.
            order: The Order object representing the pending buy order.
        """
        grid_level.place_buy_order(order)
        self.logger.info(f"Buy order placed and marked as pending at grid level {grid_level.price}.")

    def mark_sell_order_pending(
        self, 
        grid_level: GridLevel, 
        order: Order
    ) -> None:
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