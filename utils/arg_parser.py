import argparse, logging, os, traceback

def parse_and_validate_console_args():
    try:
        parser = argparse.ArgumentParser(description="Spot Grid Trading Strategy.")
        parser.add_argument('--config', type=str, nargs='+', required=True, help='Path(s) to config file(s).')
        parser.add_argument('--save_performance_results', type=str, help='Path to save simulation results (e.g., results.json)')
        parser.add_argument('--no-plot', action='store_true', help='Disable the display of plots at the end of the simulation')
        parser.add_argument('--profile', action='store_true', help='Enable profiling')
        args = parser.parse_args()
        
        if args.save_performance_results:
            save_performance_dir = os.path.dirname(args.save_performance_results)
            if save_performance_dir and not os.path.exists(save_performance_dir):
                raise ValueError(f"The directory for saving performance results does not exist: {save_performance_dir}")
        
        return args

    except argparse.ArgumentError as e:
        logging.error(f"Argument parsing error: {e}")
        exit(1)

    except ValueError as e:
        logging.error(f"Validation error: {e}")
        exit(1)

    except Exception as e:
        logging.error(f"An unexpected error occurred while parsing arguments: {e}")
        logging.error(traceback.format_exc())
        exit(1)