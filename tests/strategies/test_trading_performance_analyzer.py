import pytest, logging
from pytest import approx
from unittest.mock import Mock
import pandas as pd
from core.order_handling.order import Order, OrderType, OrderSide
from core.grid_management.grid_level import GridLevel
from strategies.trading_performance_analyzer import TradingPerformanceAnalyzer

@pytest.fixture
def setup_performance_analyzer():
    config_manager = Mock()
    config_manager.get_initial_balance.return_value = 10000
    config_manager.get_base_currency.return_value = "BTC"
    config_manager.get_quote_currency.return_value = "USDT"
    config_manager.get_trading_fee.return_value = 0.001
    order_book = Mock()
    analyzer = TradingPerformanceAnalyzer(config_manager, order_book)
    return analyzer, config_manager, order_book

@pytest.fixture
def mock_account_data():
    data = pd.DataFrame({
        "close": [100, 105, 110, 90, 95],
        "account_value": [10000, 10250, 10500, 9500, 9800]
    }, index=pd.to_datetime(['2024-01-01', '2024-01-02', '2024-01-03', '2024-01-04', '2024-01-05']))
    return data

class TestPerformanceAnalyzer:
    def test_calculate_roi(self, setup_performance_analyzer):
        analyzer, config_manager, _ = setup_performance_analyzer
        roi = analyzer._calculate_roi(11000)
        assert roi == 10.0  # Expected 10% ROI given a 10000 initial balance
    
    def test_calculate_roi_zero_balance(self, setup_performance_analyzer):
        analyzer, _, _ = setup_performance_analyzer
        roi = analyzer._calculate_roi(10000)
        assert roi == 0.0  # Expected 0% ROI when final balance matches initial balance

    def test_calculate_drawdown(self, setup_performance_analyzer, mock_account_data):
        analyzer, _, _ = setup_performance_analyzer
        max_drawdown = analyzer._calculate_drawdown(mock_account_data)
        assert max_drawdown == approx(9.52, rel=1e-3)

    def test_calculate_runup(self, setup_performance_analyzer, mock_account_data):
        analyzer, _, _ = setup_performance_analyzer
        max_runup = analyzer._calculate_runup(mock_account_data)
        assert max_runup == 5.0  # Expected max runup from 10000 to 10500 (5%)

    def test_calculate_trading_gains(self, setup_performance_analyzer):
        analyzer, _, order_book = setup_performance_analyzer


        order_book.get_all_buy_orders.return_value = [Order(identifier="123", price=1000, quantity=1, order_side= OrderSide.BUY, order_type=OrderType.MARKET, timestamp="2024-01-01T00:00:00Z")]
        order_book.get_all_sell_orders.return_value = [Order(identifier="321", price=1200, quantity=1, order_side= OrderSide.BUY, order_type=OrderType.MARKET, timestamp="2024-01-02T00:00:00Z")]

        trading_gains = analyzer._calculate_trading_gains()
        assert trading_gains == "197.80"

    def test_calculate_trading_gains_zero_trades(self, setup_performance_analyzer):
        analyzer, _, order_book = setup_performance_analyzer
        order_book.get_all_buy_orders.return_value = []
        order_book.get_all_sell_orders.return_value = []

        trading_gains = analyzer._calculate_trading_gains()
        assert trading_gains == "N/A"

    def test_calculate_sharpe_ratio(self, setup_performance_analyzer, mock_account_data):
        analyzer, _, _ = setup_performance_analyzer
        sharpe_ratio = analyzer._calculate_sharpe_ratio(mock_account_data)
        assert isinstance(sharpe_ratio, float)

    def test_calculate_sharpe_ratio_no_volatility(self, setup_performance_analyzer):
        analyzer, _, _ = setup_performance_analyzer
        data = pd.DataFrame({"account_value": [10000, 10000, 10000]}, index=pd.to_datetime(['2024-01-01', '2024-01-02', '2024-01-03']))
        sharpe_ratio = analyzer._calculate_sharpe_ratio(data)
        assert sharpe_ratio == 0.0  # Expected Sharpe ratio to be 0 when there is no volatility

    def test_get_formatted_orders(self, setup_performance_analyzer):
        analyzer, _, order_book = setup_performance_analyzer

        buy_order = Order(identifier="123", price=1000, quantity=1, order_side= OrderSide.BUY, order_type=OrderType.MARKET, timestamp="2024-01-01T00:00:00Z")
        sell_order = Order(identifier="321", price=1200, quantity=1, order_side= OrderSide.SELL, order_type=OrderType.MARKET, timestamp="2024-01-02T00:00:00Z")
        grid_level = GridLevel(price=1000, cycle_state="active")

        order_book.get_buy_orders_with_grid.return_value = [(buy_order, grid_level)]
        order_book.get_sell_orders_with_grid.return_value = [(sell_order, grid_level)]

        formatted_orders = analyzer.get_formatted_orders()

        assert len(formatted_orders) == 2
        assert formatted_orders[0][0] == "BUY"
        assert formatted_orders[0][1] == "MARKET"
        assert formatted_orders[0][2] == 1000
        assert formatted_orders[0][3] == 1
        assert formatted_orders[0][4] == "2024-01-01T00:00:00Z"
        assert formatted_orders[0][5] == 1000  # Grid level price
        assert "N/A" not in formatted_orders[0][6]  # Slippage calculated

        assert formatted_orders[1][0] == "SELL"
        assert formatted_orders[1][1] == "MARKET"
        assert formatted_orders[1][2] == 1200
        assert formatted_orders[1][3] == 1
        assert formatted_orders[1][4] == "2024-01-02T00:00:00Z"
        assert formatted_orders[1][5] == 1000  # Grid level price
        assert "N/A" not in formatted_orders[1][6]  # Slippage calculated
    
    def test_get_formatted_orders_empty(self, setup_performance_analyzer):
        analyzer, _, order_book = setup_performance_analyzer
        order_book.get_buy_orders_with_grid.return_value = []
        order_book.get_sell_orders_with_grid.return_value = []

        formatted_orders = analyzer.get_formatted_orders()
        assert formatted_orders == []

    def test_generate_performance_summary(self, setup_performance_analyzer, mock_account_data, caplog):
        analyzer, config_manager, order_book = setup_performance_analyzer
        
        balance = 10500
        crypto_balance = 0.5
        final_crypto_price = 20000
        total_fees = 50

        buy_order = Order(identifier="123", price=1000, quantity=1, order_side= OrderSide.BUY, order_type=OrderType.MARKET, timestamp="2024-01-01T00:00:00Z")
        sell_order = Order(identifier="321", price=1200, quantity=1, order_side= OrderSide.SELL, order_type=OrderType.MARKET, timestamp="2024-01-02T00:00:00Z")
        grid_level = GridLevel(price=1000, cycle_state="completed")

        order_book.get_all_buy_orders.return_value = [buy_order]
        order_book.get_all_sell_orders.return_value = [sell_order]
        order_book.get_buy_orders_with_grid.return_value = [(buy_order, grid_level)]
        order_book.get_sell_orders_with_grid.return_value = [(sell_order, grid_level)]
        
        with caplog.at_level(logging.INFO):
            performance_summary, formatted_orders = analyzer.generate_performance_summary(
                mock_account_data, balance, crypto_balance, final_crypto_price, total_fees
            )

        assert performance_summary["Pair"] == f"{config_manager.get_base_currency()}/{config_manager.get_quote_currency()}"
        assert performance_summary["Start Date"] == mock_account_data.index[0]
        assert performance_summary["End Date"] == mock_account_data.index[-1]
        assert performance_summary["Duration"] == mock_account_data.index[-1] - mock_account_data.index[0]
        assert "ROI" in performance_summary
        assert "Max Drawdown" in performance_summary
        assert "Max Runup" in performance_summary
        assert "Time in Profit %" in performance_summary
        assert "Time in Loss %" in performance_summary
        assert "Buy and Hold Return %" in performance_summary
        assert "Grid Trading Gains" in performance_summary
        assert performance_summary["Grid Trading Gains"] == "197.80"
        assert performance_summary["Total Fees"] == f"{total_fees:.2f}"
        assert performance_summary["Final Balance (Fiat)"] == f"{balance + crypto_balance * final_crypto_price:.2f}"
        assert performance_summary["Final Crypto Balance"] == f"{crypto_balance:.4f} {config_manager.get_base_currency()}"
        assert performance_summary["Remaining Fiat Balance"] == f"{balance:.2f} {config_manager.get_quote_currency()}"
        assert performance_summary["Number of Buy Trades"] == 1
        assert performance_summary["Number of Sell Trades"] == 1
        assert "Sharpe Ratio" in performance_summary
        assert "Sortino Ratio" in performance_summary

        # Assertions for formatted_orders structure and values
        assert isinstance(formatted_orders, list)
        assert len(formatted_orders) == 2  # One for each order type (buy and sell)
        
        buy_formatted = formatted_orders[0]
        sell_formatted = formatted_orders[1]
        
        # Check structure and content for buy order
        assert buy_formatted[0] == "BUY"
        assert buy_formatted[1] == "MARKET"
        assert buy_formatted[2] == 1000  # Price of the buy order
        assert buy_formatted[3] == 1  # Quantity of the buy order
        assert buy_formatted[4] == "2024-01-01T00:00:00Z"  # Timestamp
        assert buy_formatted[5] == 1000  # Grid level price
        assert buy_formatted[6] == "0.00%"  # Slippage

        # Check structure and content for sell order
        assert sell_formatted[0] == "SELL"
        assert sell_formatted[1] == "MARKET"
        assert sell_formatted[2] == 1200  # Price of the sell order
        assert sell_formatted[3] == 1  # Quantity of the sell order
        assert sell_formatted[4] == "2024-01-02T00:00:00Z"  # Timestamp
        assert sell_formatted[5] == 1000  # Grid level price
        assert sell_formatted[6] == "20.00%"  # Slippage calculated as (1200 - 1000) / 1000 * 100

        # Logging output assertions
        log_messages = [record.message for record in caplog.records]
        assert any("Formatted Orders" in message for message in log_messages)
        assert any("Performance Summary" in message for message in log_messages)

    def test_calculate_sortino_ratio(self, setup_performance_analyzer, mock_account_data):
        analyzer, _, _ = setup_performance_analyzer
        sortino_ratio = analyzer._calculate_sortino_ratio(mock_account_data)
        assert isinstance(sortino_ratio, float)

    def test_calculate_sortino_ratio_no_downside(self, setup_performance_analyzer):
        analyzer, _, _ = setup_performance_analyzer
        data = pd.DataFrame({"account_value": [10000, 10050, 10100]}, index=pd.to_datetime(['2024-01-01', '2024-01-02', '2024-01-03']))
        sortino_ratio = analyzer._calculate_sortino_ratio(data)
        assert sortino_ratio > 0  # Expected positive Sortino ratio with no downside volatility

    def test_calculate_trade_counts(self, setup_performance_analyzer):
        analyzer, _, order_book = setup_performance_analyzer
        order_book.get_all_buy_orders.return_value = [Mock(), Mock()]
        order_book.get_all_sell_orders.return_value = [Mock()]

        num_buy_trades, num_sell_trades = analyzer._calculate_trade_counts()
        assert num_buy_trades == 2
        assert num_sell_trades == 1

    def test_calculate_buy_and_hold_return(self, setup_performance_analyzer, mock_account_data):
        analyzer, _, _ = setup_performance_analyzer
        final_price = 200
        buy_and_hold_return = analyzer._calculate_buy_and_hold_return(mock_account_data, final_price)
        initial_price = mock_account_data['close'].iloc[0]
        expected_return = ((final_price - initial_price) / initial_price) * 100
        assert buy_and_hold_return == expected_return