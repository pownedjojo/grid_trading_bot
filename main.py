import cProfile, asyncio, os, logging
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from utils.arg_parser import parse_and_validate_console_args
from utils.performance_results_saver import save_or_append_performance_results
from core.bot_management.bot_controller.bot_controller import BotController
from core.bot_management.event_bus import EventBus
from config.trading_mode import TradingMode
from core.bot_management.notification.notification_handler import NotificationHandler
from core.bot_management.grid_trading_bot import GridTradingBot
from core.bot_management.health_check import HealthCheck
from config.config_manager import ConfigManager
from config.config_validator import ConfigValidator
from config.exceptions import ConfigError
from utils.logging_config import setup_logging
from utils.config_name_generator import generate_config_name

def initialize_config(config_path: str) -> ConfigManager:
    load_dotenv()
    try:
        return ConfigManager(config_path, ConfigValidator())

    except ConfigError as e:
        logging.error(f"An error occured during the initialization of ConfigManager {e}")
        exit(1)

def initialize_notification_handler(config_manager: ConfigManager, event_bus: EventBus) -> NotificationHandler:
    notification_urls = os.getenv("APPRISE_NOTIFICATION_URLS", "").split(",")
    trading_mode = config_manager.get_trading_mode()
    return NotificationHandler(event_bus, notification_urls, trading_mode)

async def run_bot(
    config_path: str,
    profile: bool = False, 
    save_performance_results_path: Optional[str] = None, 
    no_plot: bool = False
) -> Optional[Dict[str, Any]]:
    config_manager = initialize_config(config_path)
    config_name = generate_config_name(config_manager)
    setup_logging(config_manager.get_logging_level(), config_manager.should_log_to_file(), config_name)
    event_bus = EventBus()
    notification_handler = initialize_notification_handler(config_manager, event_bus)
    bot = GridTradingBot(config_path, config_manager, notification_handler, event_bus, save_performance_results_path, no_plot)
    bot_controller = BotController(bot, event_bus)
    health_check = HealthCheck(bot, notification_handler, event_bus)
    
    if profile:
        cProfile.runctx("asyncio.run(bot.run())", globals(), locals(), "profile_results.prof")
        return None

    try:
        if bot.trading_mode in {TradingMode.LIVE, TradingMode.PAPER_TRADING}:
            bot_task = asyncio.create_task(bot.run(), name="BotTask")
            bot_controller_task = asyncio.create_task(bot_controller.command_listener(), name="BotControllerTask")
            health_check_task = asyncio.create_task(health_check.start(), name="HealthCheckTask")
            await asyncio.gather(bot_task, bot_controller_task, health_check_task)
        else:
            await bot.run()
    
    except asyncio.CancelledError:
        logging.info("Cancellation received. Shutting down gracefully.")

    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}", exc_info=True)
    
    finally:
        if bot.trading_mode in {TradingMode.LIVE, TradingMode.PAPER_TRADING}:
            await cleanup_tasks(vent_bus)

async def cleanup_tasks(event_bus: EventBus):
    logging.info("Shutting down bot and cleaning up tasks...")
    await event_bus.shutdown()
    tasks = [task for task in asyncio.all_tasks() if task is not asyncio.current_task()]

    for task in tasks:
        task.cancel()

    await asyncio.gather(*tasks, return_exceptions=True)
    logging.info("All tasks have been cleaned up.")

if __name__ == "__main__":
    args = parse_and_validate_console_args()
    
    async def main():
        tasks = [
            run_bot(config_path, args.profile, args.save_performance_results, args.no_plot)
            for config_path in args.config
        ]
        
        results = await asyncio.gather(*tasks)
        if args.save_performance_results:
            for result in results:
                save_or_append_performance_results(result, args.save_performance_results)

    asyncio.run(main())