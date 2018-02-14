import sys
import json
import os
import logging
from logging.config import dictConfig

from flask import Flask
from flask_cors import CORS
from flask_restful import reqparse, abort, Api, Resource
from flask import request, jsonify
import base64
import yaml
import argparse
import textwrap

sys.path.append("/BingServer/src/RestAPI/utils")
import hashlib
import jinja2
from jinja2 import Template

from bs4 import BeautifulSoup
import requests
import re
import sys
import os
import http.cookiejar
import json
import uuid
import urllib.request, urllib.error, urllib.parse
import subprocess

def get_soup(url,header):
    #return BeautifulSoup(urllib2.urlopen(urllib2.Request(url,headers=header)),
    # 'html.parser')
    return BeautifulSoup(urllib.request.urlopen(
        urllib.request.Request(url,headers=header)),
        'html.parser')

def query_image(query_input):
    query= query_input.split()
    query='+'.join(query)
    query = query.encode('utf-8').decode('ascii','ignore')
    url="http://www.bing.com/images/search?q=" + query + "&FORM=HDRSC2"

    #add the directory for your image here
    DIR="Pictures"
    header={'User-Agent':"Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/43.0.2357.134 Safari/537.36"}
    soup = get_soup(url,header)

    ActualImages=[]# contains the link for Large original images, type of  image
    for a in soup.find_all("a",{"class":"iusc"}):
        #print a
        mad = json.loads(a["mad"])
        turl = mad["turl"]
        m = json.loads(a["m"])
        murl = m["murl"]

        image_name = urllib.parse.urlsplit(murl).path.split("/")[-1]
        print(image_name)

        ActualImages.append({ "imgname": image_name, "turl" : turl, "murl": murl})

    logger.info("Query", query_input, " returns ", len(ActualImages),"images: ", ActualImages )
    return ActualImages

def query_image2(query_input):
    query= query_input.split()
    query='+'.join(query)
    query = query.encode('utf-8').decode('ascii','ignore')
    url="http://www.bing.com/images/search?q=" + query + "&qft=+filterui:imagesize-medium"+ "&FORM=HDRSC2"

    #add the directory for your image here
    DIR="Pictures"
    header={'User-Agent':"Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/43.0.2357.134 Safari/537.36"}
    soup = get_soup(url,header)

    ActualImages=[]# contains the link for Large original images, type of  image
    for a in soup.find_all("a",{"class":"iusc"}):
        #print a
        mad = json.loads(a["mad"])
        turl = mad["turl"]
        m = json.loads(a["m"])
        murl = m["murl"]

        image_name = urllib.parse.urlsplit(murl).path.split("/")[-1]
        print(image_name)

        ActualImages.append({ "imgname": image_name, "turl" : turl, "murl": murl})

    logger.info("Query", query_input, " returns ", len(ActualImages),"images: ", ActualImages )
    return ActualImages

datadir = "/var/lib/bingserver"
dir_path = os.path.dirname(os.path.realpath(__file__))

def exec_cmd_local(execmd, supressWarning = False):
    if supressWarning:
        cmd += " 2>/dev/null"
    try:
        logger.info("Executing ... %s" % execmd  )
        output = subprocess.check_output( execmd, shell=True )
    except subprocess.CalledProcessError as e:
        output = "Return code: %s, output: %s " % (e.returncode,  e.output.strip())
    # print output
    return output


with open('/BingServer/src/RestAPI/logging.yaml', 'r') as f:
    logging_config = yaml.load(f)
    dictConfig(logging_config)
    logger = logging.getLogger("bingserver")
logger = logging.getLogger("bingserver")
logger.info("-------------------- bingserver Started -----------------")

#sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)),"../utils"))

app = Flask(__name__)
CORS(app)
api = Api(app)

parser = reqparse.RequestParser()

class Info(Resource):
    def get(self):
        return "This is a server v2 help to execute and parse bing seach results."
api.add_resource(Info, '/Info')

class BingImageSearch(Resource):
    def get(self, query):
        ActualImages = query_image(query)
        return jsonify(images=ActualImages)
api.add_resource(BingImageSearch, '/api/BingImageSearch/<string:query>')

class BingImageSearch2(Resource):
    def get(self, query):
        ActualImages = query_image(query)
        return jsonify(images=ActualImages)
api.add_resource(BingImageSearch2, '/api/BingImageSearch2/<string:query>')

class receiveImg (Resource):
    def post(self):
        logger.info("Received image request %s" % request)
        name = str(uuid.uuid4()) 
        dirname = "/var/log/apache2"
        savename = os.path.join(dirname, name + ".jpg")
        logger.info("To save image to to %s" % savename)
        file =  request.files['file']
        extension = os.path.splitext(file.filename)[1]
        f_name = str(uuid.uuid4()) + extension
        full_filename = os.path.join(dirname, f_name)
        file.save(full_filename)
        logger.info("Image saves to %s" % full_filename)

        recognCmd = "sudo /usr/bin/python3 /root/models/tutorials/image/imagenet/classify_image.py --image_file " + full_filename
        output = exec_cmd_local(recognCmd)
        logger.info("Recognition result: %s" % output)

        return jsonify( imgname = output)
api.add_resource(receiveImg, "/api/receiveImg")

if __name__ == '__main__':
    dirpath = os.path.dirname(os.path.abspath(os.path.realpath(__file__)))
    # print "Directory: " + dirpath
    os.chdir(dirpath)
    parser = argparse.ArgumentParser( prog='restapi.py',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent('''\
A rest API for the bing server. Without any argument, run API server. 

  ''') )
    parser.add_argument("-i", "--image", 
        help="Query for images", 
        action="store", 
        default=None )

    args = parser.parse_args()
    if args.image is not None:
        query_image( args.image )
    else:
        logging.info( "Main program starts")
        app.run(debug=False,host="0.0.0.0",port=180, threaded=True)