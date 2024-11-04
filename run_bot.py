import logging
from utils.arg_parser import parse_and_validate_console_args
from utils.performance_results_saver import save_or_append_performance_results
from main import run_bot_with_config
from concurrent.futures import ThreadPoolExecutor

def main():
    args = parse_and_validate_console_args()
    
    with ThreadPoolExecutor() as executor:
        futures = []
        for config_path in args.config:
            futures.append(executor.submit(run_bot_with_config, config_path, args.profile, args.save_performance_results, args.no_plot))
        
        for future in futures:
            result = future.result()
            if result and args.save_performance_results:
                save_or_append_performance_results(result, args.save_performance_results)

if __name__ == "__main__":
    main()