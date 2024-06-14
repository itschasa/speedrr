import argparse
import os
import logging



def is_valid_file(parser: argparse.ArgumentParser, arg) -> str:
    if not os.path.exists(arg):
        parser.error(f"invalid path {arg}")
    else:
        return str(arg)


def load_args() -> argparse.Namespace:
    argparser = argparse.ArgumentParser()
    argparser.add_argument(
        '--config_path',
        dest='config',
        help='Path to the config file',
        type=lambda x: is_valid_file(argparser, x),
        default=os.environ.get('SPEEDRR_CONFIG')
    )
    argparser.add_argument(
        '--log_level',
        dest='log_level',
        help='Python logging level to stdout, use 10, 20, 30, 40, 50. Default is 20 (INFO)',
        type=int,
        default=os.environ.get('SPEEDRR_LOG_LEVEL', logging.INFO)
    )
    argparser.add_argument(
        '--log_file_level',
        dest='log_file_level',
        help='Python logging level to file, use 10, 20, 30, 40, 50. Default is 30 (WARNING)',
        type=int,
        default=os.environ.get('SPEEDRR_LOG_FILE_LEVEL', logging.WARNING)
    )
    return argparser.parse_args()
