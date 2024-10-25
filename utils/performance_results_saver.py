import json, os, logging
import pandas as pd
from datetime import datetime, timedelta

def save_or_append_performance_results(new_results, file_path):
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r') as json_file:
                try:
                    all_results = json.load(json_file)
                    if not isinstance(all_results, list):
                        logging.error(f"Existing file {file_path} is not a valid JSON list. Overwriting the file.")
                        all_results = []
                except json.JSONDecodeError:
                    logging.warning(f"Could not decode JSON from {file_path}. Overwriting the file.")
                    all_results = []
        else:
            all_results = []
        
        cleaned_performance_summary = {
            key: (
                value.isoformat() if isinstance(value, (datetime, pd.Timestamp)) else 
                str(value) if isinstance(value, timedelta) else 
                value
            )
            for key, value in new_results.get("performance_summary").items()
        }
        
        order_keys = ["Order Type", "Price", "Quantity", "Timestamp", "Grid Level", "Slippage"]
        cleaned_orders = [
            {key: (value.isoformat() if isinstance(value, (datetime, pd.Timestamp)) else value)
            for key, value in zip(order_keys, order)}
            for order in new_results.get("orders")
        ]

        cleaned_results = {
            "config": new_results.get("config"),
            "performance_summary": cleaned_performance_summary,
            "orders": cleaned_orders
        }
        all_results.append(cleaned_results)

        with open(file_path, 'w') as json_file:
            json.dump(all_results, json_file, indent=4)

        logging.info(f"Performance metrics saved to {file_path}")
    except (OSError, IOError) as e:
        logging.error(f"Failed to save performance metrics to {file_path}: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred while saving performance metrics: {e}")