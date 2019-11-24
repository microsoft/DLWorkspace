import time
import sys
import yaml
import logging
import logging.config
import importlib

import Rules


with open('logging.yaml', 'r') as log_file:
    log_config = yaml.safe_load(log_file)

logging.config.dictConfig(log_config)
logger = logging.getLogger(__name__)

logger.debug('Repair manager controller has started')

try:
    while True:
        try:
            #reload module
            importlib.reload(Rules)

            # refresh config
            with open('rule-config.yaml', 'r') as rule_file:
                rule_config = yaml.safe_load(rule_file)

            rules = rule_config['rules']
    
        except Exception as e:
                logger.exception('Error loading modules/rule config')

        # execute all rules listed in config
        for r_key in rules.keys():
            try:
                module_name = rules[r_key]['module_name']
                class_name = rules[r_key]['class_name']

                r_module = sys.modules[module_name]
                r_class = getattr(r_module, class_name)
                rule = r_class()

                logger.debug('Executing ' + class_name + ' from module ' + module_name)
                                
                if rule.check_status():
                    rule.take_action()

                time.sleep(rule_config['wait_time'])

            except Exception as e:
                logger.exception('Error executing ' + class_name + ' from module ' +  module_name)
                #TODO: send email alert?

except KeyboardInterrupt:
    pass
