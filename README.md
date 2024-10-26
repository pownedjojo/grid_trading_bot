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

Grid trading is a trading strategy that places buy and sell orders at predefined intervals above and below a set price. The goal is to capitalize on market volatility by buying low and selling high at different price points. There are two primary types of grid trading: **arithmetic** and **geometric**.

### **Arithmetic Grid Trading**

In an arithmetic grid, the grid levels (price intervals) are spaced **equally**. The distance between each buy and sell order is constant, providing a more straightforward strategy for fluctuating markets.

#### **Simple Example**

Suppose the price of a cryptocurrency is $3000, and you set up a grid with the following parameters:

- **Grid levels**: $2900, $2950, $3000, $3050, $3100
- **Buy orders**: Set at $2900 and $2950
- **Sell orders**: Set at $3050 and $3100

As the price fluctuates, the bot will automatically execute buy orders as the price decreases and sell orders as the price increases. This method profits from small, predictable price fluctuations, as the intervals between buy/sell orders are consistent (in this case, $50).

### **Geometric Grid Trading**

In a geometric grid, the grid levels are spaced **proportionally** or by a percentage. The intervals between price levels increase or decrease exponentially based on a set percentage, making this grid type more suited for assets with higher volatility.

#### **Simple Example**

Suppose the price of a cryptocurrency is $3000, and you set up a geometric grid with a 5% spacing between levels. The price intervals will not be equally spaced but will grow or shrink based on the percentage.

- **Grid levels**: $2700, $2835, $2975, $3125, $3280
- **Buy orders**: Set at $2700 and $2835
- **Sell orders**: Set at $3125 and $3280

As the price fluctuates, buy orders are executed at lower levels and sell orders at higher levels, but the grid is proportional. This strategy is better for markets that experience exponential price movements.

### **When to Use Each Type?**

- **Arithmetic grids** are ideal for assets with more stable, linear price fluctuations.
- **Geometric grids** are better for assets with significant, unpredictable volatility, as they adapt more flexibly to market swings.

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
    "base_currency": "SOL",
    "quote_currency": "USDT"
  },
  "trading_settings": {
    "timeframe": "1m",
    "period": {
      "start_date": "2024-08-01T00:00:00Z",
      "end_date": "2024-10-20T00:00:00Z"
    },
    "initial_balance": 10000,
    "historical_data_file": "data/SOL_USDT/2024/1m.csv"
  },
  "grid_strategy": {
    "num_grids": 15,
    "range": {
      "top": 130,
      "bottom": 120
    },
    "spacing": {
      "type": "geometric",
      "percentage_spacing": 0.05
    }
  },
  "risk_management": {
    "take_profit": {
      "enabled": false,
      "threshold": 200
    },
    "stop_loss": {
      "enabled": false,
      "threshold": 110
    }
  },
  "logging": {
    "log_level": "INFO",
    "log_to_file": true,
    "log_file_path": "logs/trading_SOL_120_130.log"
  }
}
```

## Parameters

- **exchange**: Defines the exchange and trading fee to be used.
  - **name**: The name of the exchange (e.g., binance).
  - **trading_fee**: The trading fee should be in decimal format (e.g., 0.001 for 0.1%).

- **pair**: Specifies the trading pair.
  - **base_currency**: The base currency (e.g., ETH).
  - **quote_currency**: The quote currency (e.g., USDT).

- **trading_settings**: General trading settings.
  - **timeframe**: Time interval for the data (e.g., `1m` for one minute).
  - **period**: The start and end dates for the backtest or trading period.
    - **start_date**: The start date of the trading or backtest period.
    - **end_date**: The end date of the trading or backtest period.
  - **initial_balance**: Starting balance for the bot.
  - **historical_data_file**: Path to a local historical data file for offline testing (optional).

- **grid_strategy**: Defines the grid trading parameters.
  - **num_grids**: The number of grid levels.
  - **range**: Defines the price range of the grid.
    - **top**: The upper price limit of the grid.
    - **bottom**: The lower price limit of the grid.
  - **spacing**: Defines the grid spacing type and parameters.
    - **type**: Type of spacing (`arithmetic` or `geometric`).
    - **grid_spacing**: The spacing between grids (used for arithmetic spacing).
    - **percentage_spacing**: Percentage spacing between grids (used for geometric spacing).
  
- **risk_management**: Configurations for risk management.
  - **take_profit**: Settings for taking profit.
    - **enabled**: Whether the take profit is active.
    - **threshold**: The price at which to take profit.
  - **stop_loss**: Settings for stopping loss.
    - **enabled**: Whether the stop loss is active.
    - **threshold**: The price at which to stop loss.

- **logging**: Configures logging settings.
  - **log_level**: The logging level (e.g., `INFO`, `DEBUG`).
  - **log_to_file**: Enables logging to a file.
  - **log_file_path**: The file path for log storage.

## Running the Bot

To run the bot, use the following command:

### Basic Usage:
  ```sh
  grid_trading_bot --config config/config.json
  ```

### Multiple Configurations:
If you want to run the bot with multiple configuration files simultaneously, you can specify them all:
  ```sh
  grid_trading_bot --config config/config1.json config/config2.json config/config3.json
  ```

### Saving Performance Results:
To save the performance results to a file, use the **--save_performance_results** option:
  ```sh
  grid_trading_bot --config config/config.json --save_performance_results results.json
  ```

### Disabling Plots:
To run the bot without displaying the end-of-simulation plots, use the **--no-plot** flag:
  ```sh
  grid_trading_bot --config config/config.json --no-plot
  ```

### Combining Options:
You can combine multiple options to customize how the bot runs. For example:
  ```sh
  grid_trading_bot --config config/config1.json config/config2.json --save_performance_results combined_results.json --no-plot
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