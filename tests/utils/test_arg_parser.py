import pytest, sys, os
from unittest.mock import patch
from argparse import ArgumentError
from utils.arg_parser import parse_and_validate_console_args

@pytest.mark.parametrize("args, expected_config", [
    (["--config", "config1.json"], ["config1.json"]),
    (["--config", "config1.json", "config2.json"], ["config1.json", "config2.json"]),
])
def test_parse_and_validate_console_args_required(args, expected_config):
    with patch.object(sys, 'argv', ["program_name"] + args):
        result = parse_and_validate_console_args()
        assert result.config == expected_config


@patch("os.path.exists", return_value=True)
def test_parse_and_validate_console_args_save_performance_results_exists(mock_exists):
    with patch.object(sys, 'argv', ["program_name", "--config", "config.json", "--save_performance_results", "results.json"]):
        result = parse_and_validate_console_args()
        assert result.save_performance_results == "results.json"


@patch("os.path.exists", return_value=False)
def test_parse_and_validate_console_args_save_performance_results_dir_does_not_exist(mock_exists):
    with patch.object(sys, 'argv', ["program_name", "--config", "config.json", "--save_performance_results", "non_existent_dir/results.json"]), \
        pytest.raises(SystemExit), \
        patch("utils.arg_parser.logging.error") as mock_log:
        parse_and_validate_console_args()
        mock_log.assert_called_once_with("Validation error: The directory for saving performance results does not exist: non_existent_dir")


def test_parse_and_validate_console_args_no_plot():
    with patch.object(sys, 'argv', ["program_name", "--config", "config.json", "--no-plot"]):
        result = parse_and_validate_console_args()
        assert result.no_plot is True


def test_parse_and_validate_console_args_profile():
    with patch.object(sys, 'argv', ["program_name", "--config", "config.json", "--profile"]):
        result = parse_and_validate_console_args()
        assert result.profile is True


@patch("utils.arg_parser.logging.error")
def test_parse_and_validate_console_args_argument_error(mock_log):
    with patch.object(sys, 'argv', ["program_name", "--config"]), \
        pytest.raises(SystemExit):
        parse_and_validate_console_args()
        mock_log.assert_called_once_with("Argument parsing error: ")


@patch("utils.arg_parser.logging.error")
def test_parse_and_validate_console_args_unexpected_error(mock_log):
    with patch.object(sys, 'argv', ["program_name", "--config", "config.json", "--save_performance_results", "results.json"]), \
        patch("os.path.dirname", side_effect=Exception("Unexpected error")), \
        pytest.raises(SystemExit):
        parse_and_validate_console_args()
        mock_log.assert_any_call("An unexpected error occurred while parsing arguments: Unexpected error")