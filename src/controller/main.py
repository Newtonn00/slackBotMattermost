import sys

from src.controller.containers import Containers
import logging
from src.util.settings_parser import SettingsParser

settings = SettingsParser()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers= [
                        logging.FileHandler(settings.log_file, mode='a'),
                        logging.StreamHandler(sys.stdout)
                    ]
)

logger_bot = logging.getLogger(__name__)


containers = Containers()
app_manager = containers.slack_app_manager()
app_manager.run()