import pytest
from unittest.mock import Mock, patch
import pandas as pd
from plotly.graph_objects import Figure
from core.grid_management.grid_manager import GridManager
from core.order_handling.order_book import OrderBook
from core.order_handling.order import Order, OrderType
from strategies.plotter import Plotter

class TestPlotter:
    @pytest.fixture
    def setup_plotter(self):
        grid_manager = Mock(spec=GridManager)
        order_book = Mock(spec=OrderBook)
        plotter = Plotter(grid_manager=grid_manager, order_book=order_book)
        return plotter, grid_manager, order_book

    @pytest.mark.parametrize("close_prices", [[100, 105, 110, 115, 120], [120, 115, 110, 105, 100]])
    def test_create_base_figure(self, setup_plotter, close_prices):
        plotter, _, _ = setup_plotter
        data = pd.DataFrame({"close": close_prices}, index=pd.date_range("2024-01-01", periods=len(close_prices)))
        
        fig = plotter.create_base_figure(data)
        assert isinstance(fig, Figure)
        assert fig.data[0].name == "Close Price"
        assert fig.data[0].mode == "lines"
        assert fig.data[0].y.tolist() == close_prices

    def test_add_grid_lines(self, setup_plotter):
        plotter, grid_manager, _ = setup_plotter
        data = pd.DataFrame({"close": [100, 105, 110]}, index=[1, 2, 3])
        fig = plotter.create_base_figure(data)
        
        grid_manager.grids = [90, 110, 130]
        grid_manager.central_price = 100

        plotter.add_grid_lines(fig, grid_manager.grids, grid_manager.central_price)

        assert len(fig.data) == 4  # 1 close price line + 3 grid lines
        assert fig.data[1].line.color == "green"
        assert fig.data[2].line.color == "red"
        assert fig.data[3].line.color == "red"

    def test_add_orders(self, setup_plotter):
        plotter, _, order_book = setup_plotter
        fig = Figure()

        buy_order = Order(price=100, quantity=1, order_type=OrderType.BUY, timestamp="2024-01-01T00:00:00Z")
        sell_order = Order(price=120, quantity=1, order_type=OrderType.SELL, timestamp="2024-01-02T00:00:00Z")
        
        order_book.get_all_buy_orders.return_value = [buy_order]
        order_book.get_all_sell_orders.return_value = [sell_order]

        plotter.add_orders(fig, order_book.get_all_buy_orders(), order_book.get_all_sell_orders())

        assert len(fig.data) == 2  # One marker for each order
        assert fig.data[0].marker.color == "green"  # Buy order
        assert fig.data[1].marker.color == "red"    # Sell order
        assert fig.data[0].text == "Buy\nPrice: 100\nQty: 1\nDate: 2024-01-01T00:00:00Z"
        assert fig.data[1].text == "Sell\nPrice: 120\nQty: 1\nDate: 2024-01-02T00:00:00Z"

    @patch("plotly.graph_objects.Figure.show")
    def test_plot_results(self, mock_show, setup_plotter):
        plotter, grid_manager, order_book = setup_plotter
        data = pd.DataFrame({"close": [100, 105, 110]}, index=pd.date_range("2024-01-01", periods=3))

        grid_manager.grids = [90, 110]
        grid_manager.central_price = 100
        order_book.get_all_buy_orders.return_value = [Order(price=95, quantity=1, order_type=OrderType.BUY, timestamp="2024-01-01T00:00:00Z")]
        order_book.get_all_sell_orders.return_value = [Order(price=105, quantity=1, order_type=OrderType.SELL, timestamp="2024-01-02T00:00:00Z")]

        plotter.plot_results(data)
        
        mock_show.assert_called_once()

    def test_finalize_figure(self, setup_plotter):
        plotter, _, _ = setup_plotter
        fig = Figure()
        plotter.finalize_figure(fig)

        assert fig.layout.title.text == "Grid Trading Strategy Results"
        assert fig.layout.xaxis.title.text == "Time"
        assert fig.layout.yaxis.title.text == "Price (USDT)"
        assert fig.layout.showlegend is False