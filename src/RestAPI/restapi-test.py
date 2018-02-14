import requests
url = 'http://localhost:5000/KubeJob'

with open("../Jobs_Templete/RegularTrainingJob/tensorflow_cpu.json","r") as f:
    jobParamsJsonStr = f.read()
f.close()

data = {"cmd":"CreateJob", "params":jobParamsJsonStr}
response = requests.post(url, data=data)
print response.content