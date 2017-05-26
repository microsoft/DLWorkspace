import yaml
import os
f = open(os.path.join(os.path.dirname(os.path.realpath(__file__)),"config.yaml"))
config = yaml.load(f)
