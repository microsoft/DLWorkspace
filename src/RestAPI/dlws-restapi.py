from flask import Flask
from flask_restful import reqparse, abort, Api, Resource
from jobs import SubmitJob
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
        data = request.data
        args = json.loads(data)
        if args["cmd"] == "CreateJob":
            output = SubmitJob(json.dumps(args["params"]))
            return output, 201
        else:
            return {"msg":"No such command", "args":args}, 201

##
## Actually setup the Api resource routing here
##
api.add_resource(KubeJob, '/KubeJob')


if __name__ == '__main__':
    app.run(debug=False)
