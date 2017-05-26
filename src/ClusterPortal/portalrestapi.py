import sys
import json

from flask import Flask
from flask_restful import reqparse, abort, Api, Resource
from flask import request
import uuid

import DataHandler

app = Flask(__name__)
api = Api(app)



parser = reqparse.RequestParser()


class Report(Resource):
    def get(self):
        # ToDo: Return information on how to use the submission of training job for kubenete cluster
        parser.add_argument('hostIP')
        parser.add_argument('clusterId')
        parser.add_argument('role')
        parser.add_argument('sysId')



        args = parser.parse_args()
        hostIP = args["hostIP"]
        clusterId = args["clusterId"]
        role = args["role"]
        if "sysId" not in args or args["sysId"] is None:
            sysId= str(uuid.uuid4())
        else:
            sysId=args["sysId"]

        client_ip = ""
        try:
            client_ip = request.environ['HTTP_X_FORWARDED_FOR'].split(',')[-1].strip()
        except KeyError:
            client_ip = request.environ['REMOTE_ADDR']

        node = {}
        node["hostIP"] = hostIP
        node["clusterId"] = clusterId
        node["role"] = role
        node["clientIP"] = client_ip
        node["sysId"] = sysId

        datahandler = DataHandler.DataHandler()
        datahandler.AddNode(node)
        datahandler.Close()
        print "hostIP:%s,clusterId:%s,role:%s,clientIP:%s, sysId:%s" % (hostIP,clusterId,role,client_ip,sysId)

        return "hostIP:%s,clusterId:%s,role:%s,clientIP:%s, sysId:%s" % (hostIP,clusterId,role,client_ip,sysId), 200



##
## Actually setup the Api resource routing here
##
api.add_resource(Report, '/Report')



class GetNodes(Resource):
    def get(self):
        # ToDo: Return information on how to use the submission of training job for kubenete cluster
        parser.add_argument('role')
        parser.add_argument('clusterId')

        args = parser.parse_args()
        clusterId = args["clusterId"]
        role = args["role"]


        datahandler = DataHandler.DataHandler()
        nodes = datahandler.GetNodes(role,clusterId)
        datahandler.Close()
        ret = {}
        ret["nodes"] = nodes
        return json.dumps(ret), 200



##
## Actually setup the Api resource routing here
##
api.add_resource(GetNodes, '/GetNodes')



class SetClusterInfo(Resource):
    def get(self):
        # ToDo: Return information on how to use the submission of training job for kubenete cluster
        parser.add_argument('key')
        parser.add_argument('clusterId')
        parser.add_argument('value')

        args = parser.parse_args()
        key = args["key"]
        clusterId = args["clusterId"]
        value = args["value"]

        node = {}
        node["value"] = value
        node["clusterId"] = clusterId
        node["key"] = key

        datahandler = DataHandler.DataHandler()
        datahandler.AddClusterInfo(node)
        datahandler.Close()
        print "Insert to cluster_info: clusterId:%s,key:%s,value:%s" % (clusterId,key,value)

        return "clusterId:%s,key:%s,value:%s" % (clusterId,key,value), 200

##
## Actually setup the Api resource routing here
##
api.add_resource(SetClusterInfo, '/SetClusterInfo')



class GetClusterInfo(Resource):
    def get(self):
        # ToDo: Return information on how to use the submission of training job for kubenete cluster
        parser.add_argument('key')
        parser.add_argument('clusterId')

        args = parser.parse_args()
        clusterId = args["clusterId"]
        key = args["key"]


        datahandler = DataHandler.DataHandler()
        value = datahandler.GetClusterInfo(clusterId,key)
        datahandler.Close()
        print value
        return value, 200



##
## Actually setup the Api resource routing here
##
api.add_resource(GetClusterInfo, '/GetClusterInfo')


class DeleteCluster(Resource):
    def get(self):
        # ToDo: Return information on how to use the submission of training job for kubenete cluster
        parser.add_argument('clusterId')

        args = parser.parse_args()
        clusterId = args["clusterId"]


        datahandler = DataHandler.DataHandler()
        datahandler.DeleteCluster(clusterId)
        datahandler.Close()
        return "Done", 200



##
## Actually setup the Api resource routing here
##
api.add_resource(DeleteCluster, '/DeleteCluster')


if __name__ == '__main__':
    app.run(debug=True,host='0.0.0.0')
