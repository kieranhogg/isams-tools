import argparse
import logging
import os
import sys

from isams_tools.register_reminder.register_reminder import run as run_register_reminder
from settings import DEBUG

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# setup logging to file
logger = logging.getLogger('root')
logging_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'isams_tools.log')
hdlr = logging.FileHandler(logging_path)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)

# log debug output when in debug mode
if DEBUG:
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)

#def my_handler(type, value, tb):
#    logger.exception("Uncaught exception: {0}".format(str(value)))

#if not DEBUG:
    # Install exception handler
#    sys.excepthook = my_handler

def dispatch(module, **kwargs):
    """Run the correct module

    :param module: name of the module to run
    :param kwargs: keyword arguments to pass to the module
    :return: None
    """
    if module == 'register_reminder':
        if 'stage' not in kwargs:
            run_register_reminder()
        else:
            run_register_reminder(kwargs['stage'])
            logger.critical("Incorrect module given")

def main():
    # check we've got a settings file
    try:
        from settings import DEBUG
    except ImportError:
        logger.critical('You have not renamed settings_example.py to settings.py')
        sys.exit(1)

    logger.info('Started isams_tools with arguments:' + str(sys.argv))

    p = argparse.ArgumentParser(description='...')
    p.add_argument('module', help='Name of the module to run')
    p.add_argument('--args', required=False, nargs=1, metavar=('arg'), help='Optional arguments for the module')

    args = p.parse_args()

    if args.module == "register_reminder":
        if args.args and int(args.args[0]) in range(1, 4):
            dispatch('register_reminder', stage=int(args.args[0]))
        else:
            exit("register_reminder needs an argument of 1-3 for the stage, e.g. isams_tools register_reminder --args 1")
    elif args.module == 'data_checks':
        dispatch('data_checks')
    elif args.module == 'sync':
        dispatch('sync')
    else:
        exit("Incorrect module given")

    return

main()
