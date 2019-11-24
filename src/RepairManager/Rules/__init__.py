import os
import importlib

dirpath = os.path.dirname(__file__)
dirname = os.path.basename(dirpath)

# rules interface needs to be imported before dynamically importing all rules
importlib.import_module(dirname + ".rules_abc")

for module in os.listdir(dirpath):
    if module != '__init__.py' and module != 'rules_abc.py' and  module[-3:] == '.py':
        try:
            importlib.import_module(dirname + "." + module[:-3])
        except Exception as e:
            print("Could not import " + module)
            print(e)
