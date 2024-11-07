import pytest, logging
import pandas as pd
from unittest.mock import AsyncMock, Mock
from config.config_manager import ConfigManager
from core.services.exchange_interface import ExchangeInterface
from core.grid_management.grid_manager import GridManager
from core.order_handling.order_manager import OrderManager
from core.order_handling.balance_tracker import BalanceTracker
from strategies.trading_performance_analyzer import TradingPerformanceAnalyzer
from strategies.plotter import Plotter
from strategies.grid_trading_strategy import GridTradingStrategy
from config.trading_mode import TradingMode

class TestGridTradingStrategy:
    @pytest.fixture
    def setup_strategy(self):
        config_manager = Mock(spec=ConfigManager)
        exchange_service = Mock(spec=ExchangeInterface)
        grid_manager = Mock(spec=GridManager)
        order_manager = Mock(spec=OrderManager)
        balance_tracker = Mock(spec=BalanceTracker)
        trading_performance_analyzer = Mock(spec=TradingPerformanceAnalyzer)
        plotter = Mock(spec=Plotter)

        config_manager.get_trading_mode.return_value = TradingMode.BACKTEST
        config_manager.get_base_currency.return_value = "BTC"
        config_manager.get_quote_currency.return_value = "USDT"
        config_manager.get_pair.return_value = "BTC/USDT"
        config_manager.get_timeframe.return_value = "1d"
        config_manager.is_take_profit_enabled.return_value = True
        config_manager.is_stop_loss_enabled.return_value = True
        config_manager.get_take_profit_threshold.return_value = 20000
        config_manager.get_stop_loss_threshold.return_value = 10000
        balance_tracker.crypto_balance = 1
        balance_tracker.get_total_balance_value = AsyncMock(return_value=10500)

        def create_strategy():
            return GridTradingStrategy(
                config_manager=config_manager,
                exchange_service=exchange_service,
                grid_manager=grid_manager,
                order_manager=order_manager,
                balance_tracker=balance_tracker,
                trading_performance_analyzer=trading_performance_analyzer,
                plotter=plotter
            )

        return create_strategy, config_manager, exchange_service, grid_manager, order_manager, balance_tracker, trading_performance_analyzer, plotter
    
    @pytest.mark.asyncio
    async def test_initialize_strategy(self, setup_strategy):
        create_strategy, _, _, grid_manager, *_ = setup_strategy
        strategy = create_strategy()

        strategy.initialize_strategy()

        grid_manager.initialize_grids_and_levels.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_trading(self, setup_strategy):
        create_strategy, _, exchange_service, *_ = setup_strategy
        strategy = create_strategy()
        exchange_service.close_connection = AsyncMock()

        await strategy.stop()

        assert strategy._running is False
        exchange_service.close_connection.assert_called_once()

    @pytest.mark.asyncio
    async def test_restart_trading(self, setup_strategy):
        create_strategy, _, _, _, _, _, *_ = setup_strategy
        strategy = create_strategy()
        strategy.run = AsyncMock()
        strategy._running = False

        await strategy.restart()

        assert strategy._running is True
        strategy.run.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_run_backtest(self, setup_strategy):
        create_strategy, config_manager, _, _, _, balance_tracker, *_ = setup_strategy
        config_manager.is_stop_loss_enabled.return_value = False

        strategy = create_strategy()

        config_manager.get_trading_mode.return_value = TradingMode.BACKTEST
        strategy.data = pd.DataFrame(
            {'close': [10000, 10500, 11000]},
            index=pd.to_datetime(['2024-01-01', '2024-01-02', '2024-01-03'])
        )

        balance_tracker.get_total_balance_value = AsyncMock(side_effect=[10000, 10500, 11000, 11000])
        strategy.data.loc[strategy.data.index[0], 'account_value'] = await balance_tracker.get_total_balance_value(10000)

        await strategy.run()

        assert "account_value" in strategy.data.columns, "Expected 'account_value' column to be present in data"
        assert strategy.data['account_value'].notna().all(), "Expected all 'account_value' entries to be populated."

        expected_account_values = pd.Series([10500, 11000, 11000], index=strategy.data.index, name='account_value')
        pd.testing.assert_series_equal(strategy.data['account_value'], expected_account_values.astype('float64'))

    @pytest.mark.asyncio
    async def test_run_live_trading(self, setup_strategy):
        create_strategy, config_manager, exchange_service, *_ = setup_strategy
        config_manager.get_trading_mode.return_value = TradingMode.LIVE
        strategy = create_strategy()
        exchange_service.listen_to_ticker_updates = AsyncMock()

        await strategy.run()

        exchange_service.listen_to_ticker_updates.assert_called_once()

    # async def test_execute_take_profit(self, setup_strategy):
    #     strategy, config_manager, _, order_manager, balance_tracker, *_ = setup_strategy
    #     config_manager.get_take_profit_threshold.return_value = 12000
    #     balance_tracker.crypto_balance = 1

    #     order_manager.execute_take_profit_or_stop_loss_order = AsyncMock()
    #     await strategy._check_take_profit_stop_loss(12000, "2024-01-01T00:00:00Z")
    #     order_manager.execute_take_profit_or_stop_loss_order.assert_awaited_once_with(
    #         current_price=12000,
    #         timestamp="2024-01-01T00:00:00Z",
    #         take_profit_order=True
    #     )

    # async def test_execute_stop_loss(self, setup_strategy):
    #     create_strategy, config_manager, _, order_manager, balance_tracker, *_ = setup_strategy
    #     strategy = create_strategy()
    #     config_manager.get_stop_loss_threshold.return_value = 8000
    #     order_manager.execute_take_profit_or_stop_loss_order = AsyncMock()

    #     await strategy._check_take_profit_stop_loss(8000, "2024-01-01T00:00:00Z")

    #     order_manager.execute_take_profit_or_stop_loss_order.assert_awaited_once_with(
    #         current_price=8000,
    #         timestamp="2024-01-01T00:00:00Z",
    #         stop_loss_order=True
    #     )

    # async def test_execute_orders_called_with_correct_parameters(self, setup_strategy):
    #     # Unpack strategy and dependencies from setup_strategy
    #     strategy, _, _, _, order_manager, _, _, _ = setup_strategy, order_manager

    #     # Mock the execute_order method on the order_manager
    #     strategy.order_manager.execute_order = AsyncMock()

    #     # Run _execute_orders and assert the calls
    #     await strategy._execute_orders(10000, 9500, "2024-01-01T00:00:00Z")
    #     strategy.order_manager.execute_order.assert_has_calls([
    #         call(OrderType.BUY, 10000, 9500, "2024-01-01T00:00:00Z"),
    #         call(OrderType.SELL, 10000, 9500, "2024-01-01T00:00:00Z")
    #     ])

    def test_generate_performance_report(self, setup_strategy):
        create_strategy, _, _, _, _, balance_tracker, trading_performance_analyzer, _ = setup_strategy
        strategy = create_strategy()

        strategy.data = pd.DataFrame({'close': [10000, 10500, 11000]})
        strategy.close_prices = strategy.data['close'].values
        balance_tracker.balance = 5000
        balance_tracker.crypto_balance = 1
        balance_tracker.total_fees = 10
        trading_performance_analyzer.generate_performance_summary = Mock()

        strategy.generate_performance_report()
        
        final_price = strategy.data['close'].iloc[-1]        
        trading_performance_analyzer.generate_performance_summary.assert_called_once_with(
            strategy.data,
            balance_tracker.balance,
            balance_tracker.crypto_balance,
            final_price,
            balance_tracker.total_fees
        )

    def test_plot_results(self, setup_strategy):
        create_strategy, config_manager, _, _, _, _, _, plotter = setup_strategy
        config_manager.get_trading_mode.return_value = TradingMode.BACKTEST
        strategy = create_strategy()
        strategy.data = pd.DataFrame({'close': [10000, 10500, 11000]})

        strategy.plot_results()

        plotter.plot_results.assert_called_once_with(strategy.data)

    def test_plot_results_not_available_in_live_mode(self, setup_strategy, caplog):
        create_strategy, config_manager, _, _, _, _, _, plotter = setup_strategy
        config_manager.get_trading_mode.return_value = TradingMode.LIVE
        strategy = create_strategy()

        with caplog.at_level(logging.INFO):
            strategy.plot_results()

        assert "Plotting is not available for live/paper trading mode." in [record.message for record in caplog.records]
        plotter.plot_results.assert_not_called()