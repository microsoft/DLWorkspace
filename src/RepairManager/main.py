import time
import sys
import yaml
import logging
import logging.config
import importlib
import datetime
import util
import traceback

import Rules

with open('logging.yaml', 'r') as log_file:
    log_config = yaml.safe_load(log_file)

logging.config.dictConfig(log_config)
logger = logging.getLogger(__name__)


def handle_email_alert(config, monitor_alerts, class_name, e):
    email_params = config['email_alerts']
    traceback_str = ''.join(traceback.format_exception(etype=type(e), value=e, tb=e.__traceback__))
    subject = f'Repair Manager Alert [Exception executing {class_name}]'

    # to avoid email clutter, send email based on configured alert wait time
    if class_name in monitor_alerts:
        time_now = datetime.datetime.now()
        time_start = monitor_alerts[class_name]
        time_delta = datetime.timedelta(hours=config['alert_wait_time'])

        if time_now - time_start > time_delta:
            util.smtp_send_email(**email_params, subject=subject, body=traceback_str)
            monitor_alerts[class_name] = datetime.datetime.now()                  

    else:
        monitor_alerts[class_name] = datetime.datetime.now()
        util.smtp_send_email(**email_params, subject=subject, body=traceback_str)

    return monitor_alerts

def refresh_rules():
    try:
        importlib.reload(Rules)

        with open('rule-config.yaml', 'r') as config_file:
            config = yaml.safe_load(config_file)

        return config

    except Exception as e:
        logger.exception('Error loading modules/rule config')

def Run():
    try:        
        monitor_alerts = {}
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
                    rule = r_class()

                    logger.debug(f'Executing {class_name} from module {module_name}')

                    if rule.check_status():
                        rule.take_action()

                    time.sleep(config['rule_wait_time'])

                except Exception as e:
                    logger.exception(f'Error executing {class_name} from module {module_name}\n')
                    monitor_alerts = handle_email_alert(config, monitor_alerts, class_name, e)

    except Exception as e:
         logger.exception('Repair manager has stopped due to an unhandled exception:')
         email_params = config['email_alerts']
         traceback_str = ''.join(traceback.format_exception(etype=type(e), value=e, tb=e.__traceback__))
         subject = '[Repair Manager Alert] Repair manager has stopped'
         body = f'Repair manager has stopped unexpectedly due to an unhandled exception:\n{traceback_str}'
         util.smtp_send_email(**email_params, subject=subject, body=body)

if __name__ == '__main__':
    Run()