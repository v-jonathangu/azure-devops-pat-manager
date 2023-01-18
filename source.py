from platform import platform
import argparse

from msal_extensions import *
from functions import *
from interactive import interactive_main


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        prog="Azure DevOps PAT Manager for python",
        description="Manage Azure DevOps Personal Access Tokens")
    # interactive mode, by default is disabled
    parser.add_argument('-i', '--interactive', action='store_true',
                        help="Interactive mode")
    # preferred flow, by default is interactive
    parser.add_argument('-f', '--flow', type=str, default="interactive",
                        # show the supported flows
                        help=f"Preferred authentication flow [{', '.join(flows.keys())}]")
    args = vars(parser.parse_args())
    # show help if no arguments are provided or help is requested
    if len(args) == 0 or 'help' in args:
        parser.print_help()
        exit()
    cache = get_access_token_cache()
    access_token = get_access_token(cache, args['flow'])
    # check if the user wants to use the interactive mode
    if parser.parse_args().interactive:
        interactive_main()
