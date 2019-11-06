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
logger = logging.getLogger('basic')
logger.setLevel(logging.DEBUG)

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
            wait_time = rule_config['wait_time']
    
        except Exception as e:
                logger.error('Error loading modules/rule config')
                logger.error(e)

        # execute all rules listed in config
        for module_name in rules:
            try:
                module = sys.modules[module_name]
                class_name = rules[module_name]
                rule_class = getattr(module, class_name)
                rule = rule_class()

                logger.debug('Executing ' + class_name+ ' from module ' + module_name)
                                
                if (rule.check_status()):
                    rule.take_action()

                time.sleep(wait_time)

            except Exception as e:
                logger.error('Error executing ' + class_name + ' from modul e' + module_name)
                logger.error(e)
                #TODO: send email alert?

except KeyboardInterrupt:
    pass
