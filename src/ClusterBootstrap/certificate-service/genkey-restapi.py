
import sys
import json

from flask import Flask
from flask_restful import reqparse, abort, Api, Resource
from flask import request

import os.path
from subprocess import call
import base64


app = Flask(__name__)
api = Api(app)



parser = reqparse.RequestParser()


class GenKey(Resource):
    def get(self):
        # ToDo: Return information on how to use the submission of training job for kubenete cluster 
        parser.add_argument('workerId')
        parser.add_argument('workerIP')
        args = parser.parse_args()
        worker_ip = args["workerIP"]
        worker_id = args["workerId"]
        client_ip = ""
        try:
            client_ip = request.environ['HTTP_X_FORWARDED_FOR'].split(',')[-1].strip()
        except KeyError:
            client_ip = request.environ['REMOTE_ADDR']

        ca_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),"ca/ca.pem")
        worker_cert_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),"workers/%s/%s-worker.pem" % (worker_ip,worker_id))
        worker_key_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),"workers/%s/%s-worker-key.pem" % (worker_ip,worker_id))
        args = "%s %s %s" %(worker_id,worker_ip,client_ip)
        print args
        if len(worker_id) > 0 and len(worker_ip) > 0 and len(client_ip) > 0:
            exec_cmd=os.path.join(os.path.dirname(os.path.abspath(__file__)),"genworkerkey.sh")
            call([exec_cmd, worker_id, worker_ip,client_ip])
            if os.path.isfile(worker_cert_path) and os.path.isfile(worker_key_path):
                f = open(ca_path,'r')
                ca = base64.b64encode(f.read())
                f.close()

                f = open(worker_cert_path,'r')
                worker_cert = base64.b64encode(f.read())
                f.close()

                f = open(worker_key_path,'r')
                worker_key_path = base64.b64encode(f.read())
                f.close()
                print [b"%s,%s,%s" %(ca,worker_cert,worker_key_path)] 
                return str("%s,%s,%s" %(ca,worker_cert,worker_key_path) )
        return [b"Cannot generate client key for worker: %s, with IP (%s, %s)" % (worker_id, worker_ip, client_ip)]



##
## Actually setup the Api resource routing here
##
api.add_resource(GenKey, '/genkey')

if __name__ == '__main__':
    app.run(debug=True,host='0.0.0.0')

