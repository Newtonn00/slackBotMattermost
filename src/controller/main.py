import logging
import sys
from logging.handlers import TimedRotatingFileHandler

from src.controller.containers import Containers
from src.controller.slack_app_manager import SlackAppManager
from src.controller.slack_load_messages import SlackLoadMessages
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
container = Containers()
app_manager = container.slack_app_manager()
SlackLoadMessages.set_container_instance(container)
SlackAppManager.set_container_instance(container)
app_manager.run()
