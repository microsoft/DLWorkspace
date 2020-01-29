import time
import sys
import yaml
import logging
import logging.config
import importlib
import traceback
from utils import rule_alert_handler

import rules

with open('./config/logging.yaml', 'r') as log_file:
    log_config = yaml.safe_load(log_file)

logging.config.dictConfig(log_config)
logger = logging.getLogger(__name__)

alert = rule_alert_handler.RuleAlertHandler()


def Run():
    try:        
        while True:
            with open('./config/rule-config.yaml', 'r') as config_file:
                config = yaml.safe_load(config_file)

            # execute all rules listed in config
            rules_config = config['rules']
            for r_key in rules_config.keys():
                try:
                    # retrieve module and class for given rule
                    module_name = rules_config[r_key]['module_name']
                    class_name = rules_config[r_key]['class_name']
                    rule_module = importlib.import_module(module_name)
                    r_class = getattr(rule_module, class_name)
                    rule = r_class(alert, config)

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