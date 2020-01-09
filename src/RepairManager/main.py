import time
import sys
import yaml
import logging
import logging.config
import importlib
import traceback
from utils import rule_alert_handler

import Rules

with open('./config/logging.yaml', 'r') as log_file:
    log_config = yaml.safe_load(log_file)

logging.config.dictConfig(log_config)
logger = logging.getLogger(__name__)

alert = rule_alert_handler.RuleAlertHandler()


def refresh_rules():
    try:
        importlib.reload(Rules)

        with open('./config/rule-config.yaml', 'r') as config_file:
            config = yaml.safe_load(config_file)

        return config

    except Exception as e:
        logger.exception('Error loading modules/rule config')

def Run():
    try:        
        while True:
            config = refresh_rules()

            # execute all rules listed in config
            rules = config['rules']
            for r_key in rules.keys():
                try:
                    # retrieve module and class for given rule
                    module_name = rules[r_key]['module_name']
                    class_name = rules[r_key]['class_name']
                    r_module = sys.modules[module_name]
                    r_class = getattr(r_module, class_name)
                    rule = r_class(alert)

                    logger.debug(f'Executing {class_name} from module {module_name}')

                    if rule.check_status():
                        rule.take_action()

                    time.sleep(config['rule_wait_time'])

                except Exception as e:
                    logger.exception(f'Error executing {class_name} from module {module_name}\n')

    except Exception as e:
         logger.exception('Repair manager has stopped due to an unhandled exception.')

if __name__ == '__main__':
    Run()