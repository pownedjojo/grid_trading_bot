import pytest
import numpy as np
from unittest.mock import Mock
from core.grid_management.grid_manager import GridManager
from core.grid_management.grid_level import GridLevel, GridCycleState

class TestGridManager:
    @pytest.fixture
    def config_manager(self):
        mock_config_manager = Mock()
        mock_config_manager.get_bottom_range.return_value = 1000
        mock_config_manager.get_top_range.return_value = 2000
        mock_config_manager.get_num_grids.return_value = 10
        mock_config_manager.get_spacing_type.return_value = 'arithmetic'
        mock_config_manager.get_percentage_spacing.return_value = 0.05
        return mock_config_manager

    @pytest.fixture
    def grid_manager(self, config_manager):
        return GridManager(config_manager)

    def test_initialize_grid_levels(self, grid_manager):
        grid_manager.initialize_grid_levels()
        assert len(grid_manager.grid_levels) == len(grid_manager.grids)
        for price, grid_level in grid_manager.grid_levels.items():
            assert isinstance(grid_level, GridLevel)
            if price <= grid_manager.central_price:
                assert grid_level.cycle_state == GridCycleState.READY_TO_BUY
            else:
                assert grid_level.cycle_state == GridCycleState.READY_TO_SELL

    def test_get_grid_level(self, grid_manager):
        grid_manager.initialize_grid_levels()
        grid_price = grid_manager.grids[0]
        grid_level = grid_manager.get_grid_level(grid_price)
        assert isinstance(grid_level, GridLevel)
        assert grid_level.price == grid_price

    def test_get_grid_level_invalid_price(self, grid_manager):
        grid_manager.initialize_grid_levels()
        assert grid_manager.get_grid_level(9999) is None

    def test_calculate_grids_and_central_price_arithmetic(self, grid_manager):
        expected_grids = np.linspace(1000, 2000, 10)
        grids, central_price = grid_manager._calculate_grids_and_central_price()
        np.testing.assert_array_equal(grids, expected_grids)
        assert central_price == 1500

    def test_calculate_grids_and_central_price_geometric(self, config_manager):
        config_manager.get_spacing_type.return_value = 'geometric'
        config_manager.get_bottom_range.return_value = 1000
        config_manager.get_top_range.return_value = 2000
        config_manager.get_percentage_spacing.return_value = 0.05
        grid_manager = GridManager(config_manager)

        expected_grids = [1000, 1050, 1102.5, 1157.625, 1215.50625, 1276.28156, 1340.09564, 1407.10043, 1477.45545, 1551.32822]
        grids, central_price = grid_manager._calculate_grids_and_central_price()
        np.testing.assert_array_almost_equal(grids, expected_grids, decimal=5)
        assert central_price == (2000 * 1000) ** 0.05

    def test_detect_grid_level_crossing_upward(self, grid_manager):
        grid_manager.sorted_sell_grids = [1500, 1600, 1700]
        current_price = 1600
        previous_price = 1400
        crossing_grid = grid_manager.detect_grid_level_crossing(current_price, previous_price, sell=True)
        assert crossing_grid == 1500

    def test_detect_grid_level_crossing_downward(self, grid_manager):
        grid_manager.sorted_buy_grids = [1300, 1400, 1500]
        current_price = 1450
        previous_price = 1600
        crossing_grid = grid_manager.detect_grid_level_crossing(current_price, previous_price)
        assert crossing_grid == 1500

    def test_detect_no_crossing_upward(self, grid_manager):
        grid_manager.sorted_sell_grids = [1500, 1600, 1700]
        current_price = 1490
        previous_price = 1400
        crossing_grid = grid_manager.detect_grid_level_crossing(current_price, previous_price, sell=True)
        assert crossing_grid is None

    def test_detect_no_crossing_downward(self, grid_manager):
        grid_manager.sorted_buy_grids = [1300, 1400, 1500]
        current_price = 1510
        previous_price = 1600
        crossing_grid = grid_manager.detect_grid_level_crossing(current_price, previous_price)
        assert crossing_grid is None

    def test_detect_exact_crossing_upward(self, grid_manager):
        grid_manager.sorted_sell_grids = [1500, 1600, 1700]
        current_price = 1500
        previous_price = 1400
        crossing_grid = grid_manager.detect_grid_level_crossing(current_price, previous_price, sell=True)
        assert crossing_grid == 1500

    def test_detect_exact_crossing_downward(self, grid_manager):
        grid_manager.sorted_buy_grids = [1300, 1400, 1500]
        current_price = 1500
        previous_price = 1600
        crossing_grid = grid_manager.detect_grid_level_crossing(current_price, previous_price)
        assert crossing_grid == 1500

    def test_detect_no_grid_levels(self, grid_manager):
        grid_manager.sorted_sell_grids = []
        current_price = 1500
        previous_price = 1400
        crossing_grid = grid_manager.detect_grid_level_crossing(current_price, previous_price, sell=True)
        assert crossing_grid is None

    def test_detect_crossing_from_above(self, grid_manager):
        grid_manager.sorted_sell_grids = [1500, 1600, 1700]
        current_price = 1600
        previous_price = 1550
        crossing_grid = grid_manager.detect_grid_level_crossing(current_price, previous_price, sell=True)
        assert crossing_grid == 1600

    def test_detect_crossing_from_below(self, grid_manager):
        grid_manager.sorted_buy_grids = [1300, 1400, 1500]
        current_price = 1450
        previous_price = 1500
        crossing_grid = grid_manager.detect_grid_level_crossing(current_price, previous_price)
        assert crossing_grid == 1500

    def test_find_lowest_completed_buy_grid(self, grid_manager):
        grid_manager.initialize_grid_levels()
        mock_grid_level = Mock()
        mock_grid_level.can_place_sell_order.return_value = True
        grid_manager.grid_levels[1000] = mock_grid_level

        lowest_completed_grid = grid_manager.find_lowest_completed_buy_grid()
        assert lowest_completed_grid == mock_grid_level

    def test_find_lowest_completed_buy_grid_no_completed(self, grid_manager):
        grid_manager.initialize_grid_levels()
        lowest_completed_grid = grid_manager.find_lowest_completed_buy_grid()
        assert lowest_completed_grid is None