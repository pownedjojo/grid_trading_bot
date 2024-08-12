# Grid Trading Bot

Open-source Grid Trading Bot implemented in Python, allowing you to backtest and execute grid trading strategies on cryptocurrency markets. The bot is highly customizable and works with various exchanges using the CCXT library.

## Features

- **Backtesting**: Simulate your grid trading strategy using historical data.
- **Grid Trading**: Automatically place buy and sell orders based on grid levels.
- **Customizable Grid Settings**: Define grid levels, spacing type, and more.
- **Support for Multiple Exchanges**: Load data and execute trades on multiple exchanges via CCXT.
- **Take Profit & Stop Loss**: Set take profit and stop loss thresholds to manage risk.
- **Performance Metrics**: Track key metrics like ROI, drawdown, run-up, and more.
- **Detailed Configuration**: Configure the bot’s behavior through a JSON file.
- **Logging**: Monitor bot activity and debug effectively with detailed logs.

## What is Grid Trading?

Grid trading is a type of trading strategy that involves placing buy and sell orders at predefined intervals above and below a set price. The goal is to capitalize on normal price volatility in the market, buying low and selling high.

### Simple Example

Suppose the price of a cryptocurrency is $3000, and you set up a grid with the following parameters:

- **Grid levels**: $2900, $2950, $3000, $3050, $3100
- **Buy orders**: Set at $2900 and $2950
- **Sell orders**: Set at $3050 and $3100

As the price fluctuates, the bot will automatically execute buy orders as the price decreases and sell orders as the price increases, allowing you to profit from market swings.

## Installation

### Prerequisites

Ensure you have [Conda](https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html) installed on your machine.

### Setting Up the Environment

1. **Clone the repository**:
   ```sh
   git clone https://github.com/yourusername/grid_trading_bot.git
   cd grid_trading_bot
   ```

2.  **Create the Conda environment**:
```sh
    conda env create -f environment.yml
```

3.	**Activate the environment**: 
```sh
    conda activate grid_trading_bot
```

### Configuration

Configure the bot by editing the `config/config.json` file to your needs. Here is an example configuration:

```json
{
  "exchange": {
    "name": "binance",
    "trading_fee": 0.001
  },
  "pair": {
    "base_currency": "ETH",
    "quote_currency": "USDT"
  },
  "timeframe": "1h",
  "period": {
    "start_date": "2024-06-01T00:00:00Z",
    "end_date": "2024-06-30T00:00:00Z"
  },
  "initial_balance": 10000,
  "take_profit": {
    "is_active": true,
    "threshold": 3700
  },
  "stop_loss": {
    "is_active": true,
    "threshold": 3100
  },
  "grid": {
    "num_grids": 20,
    "top_range": 3600,
    "bottom_range": 3200,
    "spacing_type": "arithmetic",
    "grid_spacing": 200,
    "percentage_spacing": 0.05,
    "trigger_price": null
  },
  "limits": {
    "max_orders": 10
  },
  "logging": {
    "log_level": "INFO"
  }
}
```

## Parameters

- **exchange**: Defines the exchange and trading fee to be used.
  - **name**: The name of the exchange (e.g., binance).
  - **trading_fee**: The trading fee percentage.
- **pair**: Specifies the trading pair.
  - **base_currency**: The base currency (e.g., ETH).
  - **quote_currency**: The quote currency (e.g., USDT).
- **timeframe**: Time interval for the data (e.g., 1h for one hour).
- **period**: The start and end dates for the backtest or trading period.
  - **start_date**: The start date of the trading or backtest period.
  - **end_date**: The end date of the trading or backtest period.
- **initial_balance**: Starting balance for the bot.
- **grid**: Defines the grid trading parameters.
  - **num_grids**: The number of grid levels.
  - **top_range**: The upper price limit of the grid.
  - **bottom_range**: The lower price limit of the grid.
  - **spacing_type**: The type of spacing (arithmetic or geometric).
  - **grid_spacing**: The spacing between grids (used for arithmetic spacing).
  - **percentage_spacing**: The percentage spacing between grids (used for geometric spacing).
  - **trigger_price**: The price at which to start trading.
- **limits**: Configurations for risk management.
  - **take_profit**: Settings for taking profit.
    - **is_active**: Whether the take profit is active.
    - **threshold**: The price at which to take profit.
  - **stop_loss**: Settings for stopping loss.
    - **is_active**: Whether the stop loss is active.
    - **threshold**: The price at which to stop loss.
- **logging**: Configures logging.
  - **log_level**: The level of logging (e.g., INFO, DEBUG).

## Running the Bot

To run the bot, use the following command:
```sh 
    grid_trading_bot --config config/config.json
```

## Contributing

Contributions are welcome! If you have suggestions or want to improve the bot, feel free to fork the repository and submit a pull request.

### Reporting Issues

If you encounter any issues or have feature requests, please create a new issue on the [GitHub Issues](https://github.com/pownedjojo/grid_trading_bot/issues) page.

## Donations

If you find this project helpful and would like to support its development, consider buying me a coffee! Your support is greatly appreciated and motivates me to continue improving and adding new features.

[![Buy Me A Coffee](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/pownedj)

Thank you for your support!

## License

This project is licensed under the MIT License. See the [LICENSE](./LICENSE.txt) file for more details.

## Disclaimer

This project is intended for educational purposes only. The authors and contributors are not responsible for any financial losses incurred while using this bot. Trading cryptocurrencies involves significant risk and can result in the loss of all invested capital. Please do your own research and consult with a licensed financial advisor before making any trading decisions. Use this software at your own risk.