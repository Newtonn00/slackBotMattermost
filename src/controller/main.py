import sys

from src.controller.containers import Containers
import logging
from logging.handlers import TimedRotatingFileHandler
from src.util.settings_parser import SettingsParser

settings = SettingsParser()
timed_handler = TimedRotatingFileHandler(settings.log_file, when='midnight', interval=1, backupCount=10)
timed_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        timed_handler,
                        logging.StreamHandler(sys.stdout)
                    ]
                    )
containers = Containers()
app_manager = containers.slack_app_manager()
app_manager.run()
