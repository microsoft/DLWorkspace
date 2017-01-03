from flask import Flask
from flask_restful import reqparse, abort, Api, Resource
from jobs import SubmitJob
from jobs_dist import SubmitDistJob
from flask import request
import json

app = Flask(__name__)
api = Api(app)



parser = reqparse.RequestParser()




# TodoList
# shows a list of all todos, and lets you POST to add new tasks
class KubeJob(Resource):
    def get(self):
        return {}

    def post(self):
        #parser.add_argument('cmd')
        #parser.add_argument('params')
        #args = parser.parse_args()
        data = dict(request.form)
        args = {}
        for key, value in data.iteritems():
            if len(value) > 0 and len(value[0]) > 0:
                args[key] = value[0]
        print args
        if args["apicmd"] == "CreateJob":
            output = SubmitJob(json.dumps(args))
            return output, 201
        else:
            return {"msg":"No such command", "args":args}, 201

##
## Actually setup the Api resource routing here
##
api.add_resource(KubeJob, '/KubeJob')

# TodoList
# shows a list of all todos, and lets you POST to add new tasks
class KubeDistJob(Resource):
    def get(self):
        return {}

    def post(self):
        #parser.add_argument('cmd')
        #parser.add_argument('params')
        #args = parser.parse_args()
        data = dict(request.form)
        args = {}
        for key, value in data.iteritems():
            if len(value) > 0 and len(value[0]) > 0:
                args[key] = value[0]
        print args
        if args["apicmd"] == "CreateJob":
            output = SubmitDistJob(json.dumps(args))
            return output, 201
        else:
            return {"msg":"No such command", "args":args}, 201

##
## Actually setup the Api resource routing here
##
api.add_resource(KubeDistJob, '/KubeDistJob')


if __name__ == '__main__':
    app.run(debug=True)
