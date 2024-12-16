import pytest, logging
import pandas as pd
import numpy as np
from unittest.mock import AsyncMock, Mock
from config.config_manager import ConfigManager
from core.bot_management.event_bus import EventBus, Events
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
        event_bus = Mock(spec=EventBus)

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
                event_bus=event_bus,
                exchange_service=exchange_service,
                grid_manager=grid_manager,
                order_manager=order_manager,
                balance_tracker=balance_tracker,
                trading_performance_analyzer=trading_performance_analyzer,
                plotter=plotter
            )

        return create_strategy, config_manager, exchange_service, grid_manager, order_manager, balance_tracker, trading_performance_analyzer, plotter, event_bus
    
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
    async def test_restart_live_trading(self, setup_strategy):
        create_strategy, config_manager, exchange_service, grid_manager, _, _, _, _, _ = setup_strategy
        config_manager.get_trading_mode.return_value = TradingMode.LIVE
        strategy = create_strategy()
        grid_manager.get_trigger_price.return_value = 10500
        exchange_service.listen_to_ticker_updates = AsyncMock()
        strategy._running = False

        await strategy.restart()

        # Assert that the strategy started and `listen_to_ticker_updates` was called
        assert strategy._running is True, "Expected strategy to be running after restart in LIVE mode."

        # Extract the actual callback passed to `listen_to_ticker_updates`
        actual_call_args = exchange_service.listen_to_ticker_updates.call_args
        actual_callback = actual_call_args[0][1]  # Extract the callback argument

        # Verify `listen_to_ticker_updates` was called with the correct parameters
        assert actual_call_args[0][0] == strategy.pair, "Expected the trading pair to be passed."
        assert actual_call_args[0][2] == strategy.TICKER_REFRESH_INTERVAL, "Expected the correct ticker refresh interval."
        assert callable(actual_callback), "Expected a callable callback for on_ticker_update."

    @pytest.mark.asyncio
    async def test_run_backtest(self, setup_strategy):
        create_strategy, config_manager, _, grid_manager, order_manager, balance_tracker, *_ = setup_strategy
        config_manager.get_trading_mode.return_value = TradingMode.BACKTEST
        config_manager.get_initial_balance.return_value = 9000
        balance_tracker.get_total_balance_value = Mock()

        strategy = create_strategy()

        strategy.data = pd.DataFrame(
            {
                'close': [10000, 10500, 11000],
                'high': [10100, 10600, 11100],
                'low': [9900, 10400, 10900],
                'account_value': [np.nan, np.nan, np.nan],
            },
            index=pd.to_datetime(['2024-01-01', '2024-01-02', '2024-01-03'])
        )

        balance_tracker.get_total_balance_value.side_effect = [9000, 9500, 10000]
        grid_manager.get_trigger_price.return_value = 8900
        order_manager.simulate_order_fills = AsyncMock()
        order_manager.initialize_grid_orders = AsyncMock()
        strategy._initialize_grid_orders_once = AsyncMock(side_effect=[False, True, True])
        strategy._check_take_profit_stop_loss = AsyncMock(side_effect=[False, False, False])

        await strategy.run()

        expected_account_values = pd.Series([9000, 9000, 9500], index=strategy.data.index, name='account_value')
        pd.testing.assert_series_equal(strategy.data['account_value'], expected_account_values.astype('float64'))
        strategy._check_take_profit_stop_loss.assert_awaited()

    @pytest.mark.asyncio
    async def test_run_live_trading(self, setup_strategy):
        create_strategy, config_manager, exchange_service, *_ = setup_strategy
        config_manager.get_trading_mode.return_value = TradingMode.LIVE
        strategy = create_strategy()
        exchange_service.listen_to_ticker_updates = AsyncMock()

        await strategy.run()

        exchange_service.listen_to_ticker_updates.assert_called_once()

    def test_generate_performance_report(self, setup_strategy):
        create_strategy, _, _, _, _, balance_tracker, trading_performance_analyzer, _, _ = setup_strategy
        strategy = create_strategy()
        strategy.data = pd.DataFrame({'close': [10000, 10500, 11000]})
        strategy.close_prices = strategy.data['close'].values
        final_price = strategy.data['close'].iloc[-1]
        balance_tracker.get_adjusted_fiat_balance.return_value = 5000
        balance_tracker.get_adjusted_crypto_balance.return_value = 1
        balance_tracker.total_fees = 10
        trading_performance_analyzer.generate_performance_summary = Mock()

        strategy.generate_performance_report()

        trading_performance_analyzer.generate_performance_summary.assert_called_once_with(
            strategy.data,
            balance_tracker.get_adjusted_fiat_balance(),
            balance_tracker.get_adjusted_crypto_balance(),
            final_price,
            balance_tracker.total_fees
        )

    def test_plot_results(self, setup_strategy):
        create_strategy, config_manager, _, _, _, _, _, plotter, _ = setup_strategy
        config_manager.get_trading_mode.return_value = TradingMode.BACKTEST
        strategy = create_strategy()
        strategy.data = pd.DataFrame({'close': [10000, 10500, 11000]})

        strategy.plot_results()

        plotter.plot_results.assert_called_once_with(strategy.data)

    def test_plot_results_not_available_in_live_mode(self, setup_strategy, caplog):
        create_strategy, config_manager, _, _, _, _, _, plotter, _ = setup_strategy
        config_manager.get_trading_mode.return_value = TradingMode.LIVE
        strategy = create_strategy()

        with caplog.at_level(logging.INFO):
            strategy.plot_results()

        assert "Plotting is not available for live/paper trading mode." in [record.message for record in caplog.records]
        plotter.plot_results.assert_not_called()