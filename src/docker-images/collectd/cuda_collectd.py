#!/usr/bin/env python

import collectd
import subprocess
import xml.etree.ElementTree as ET
import json
import re 
import sys, traceback

def configure(conf):
        collectd.info('Configured with')


def read(data=None):
    gpumap = {}
    try:
        #curl --silent --unix-socket /var/run/docker.sock "http:/containers/9c27d99634f3/json"
        dockerIds = subprocess.Popen(['curl', '--silent', '--unix-socket', '/var/run/docker.sock', 'http:/containers/json'], stdout=subprocess.PIPE).communicate()[0].strip()
        dockerIds = json.loads(dockerIds)
        for dockerId in dockerIds:
            out = subprocess.Popen(['curl', '--silent', '--unix-socket', '/var/run/docker.sock', 'http:/containers/%s/json' % (dockerId["Id"])], stdout=subprocess.PIPE).communicate()[0].strip()
            dockerinfo = json.loads(out)
            devices = dockerinfo["HostConfig"]["Devices"]
            if devices is not None and len(devices) >0:
                jobid = dockerinfo["Config"]["Hostname"]
                for device in devices:
                    m = re.search('/dev/nvidia[0-9]',device["PathOnHost"])
                    if m is not None:
                        gpuId = m.group(0).replace("/dev/nvidia","")
                        gpumap[gpuId] = jobid
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        print("*** print_tb:")
        traceback.print_tb(exc_traceback, limit=1, file=sys.stdout)
        print("*** print_exception:")
        traceback.print_exception(exc_type, exc_value, exc_traceback,
                                  limit=2, file=sys.stdout)
        print("*** print_exc:")
        traceback.print_exc()

    print("container - gpu mapping:" + str(gpumap))

    try:
        vl = collectd.Values(type='gauge')
        vl.plugin = 'cuda'

        out = subprocess.Popen(['nvidia-smi', '-q', '-x'], stdout=subprocess.PIPE).communicate()[0]
        root = ET.fromstring(out)

        # Changed root.iter() to root.getiterator() for Python 2.6 compatibility

        for gpu in root.getiterator('gpu'):
                # GPU id
                gpuNum = gpu.find('minor_number').text

                vl.plugin_instance = 'gpu%s' % (gpuNum)

                print("Reporting GPU information #" + gpuNum)
                print("gpu_util %s" % str(gpu.find('utilization/gpu_util').text.split()[0]))
                print("gpu_temp %s" % str(gpu.find('temperature/gpu_temp').text.split()[0]))
                print("power_draw %s" % str(gpu.find('power_readings/power_draw').text.split()[0]))
                print("mem_util %s" % str(gpu.find('utilization/memory_util').text.split()[0]))
                print("enc_util %s" % str(gpu.find('utilization/encoder_util').text.split()[0]))
                print("dec_util %s" % str(gpu.find('utilization/decoder_util').text.split()[0]))
                print("mem_used %s" % str(gpu.find('fb_memory_usage/used').text.split()[0]))
                print("mem_total %s" % str(gpu.find('fb_memory_usage/total').text.split()[0]))
                print("gpu_clock %s" % str(gpu.find('clocks/graphics_clock').text.split()[0]))
                print("mem_clock %s" % str(gpu.find('clocks/mem_clock').text.split()[0]))


                # GPU utilization
                vl.dispatch(type='percent', type_instance='gpu_util',
                            values=[float(gpu.find('utilization/gpu_util').text.split()[0])])
                # GPU temperature
                vl.dispatch(type='temperature',
                            values=[float(gpu.find('temperature/gpu_temp').text.split()[0])])
                # GPU power draw
                vl.dispatch(type='power', type_instance='power_draw',
                            values=[float(gpu.find('power_readings/power_draw').text.split()[0])])
                # GPU memory utilization
                vl.dispatch(type='percent', type_instance='mem_util',
                            values=[float(gpu.find('utilization/memory_util').text.split()[0])])
                # GPU encoder utilization
                vl.dispatch(type='percent', type_instance='enc_util',
                            values=[float(gpu.find('utilization/encoder_util').text.split()[0])])
                # GPU decoder utilization
                vl.dispatch(type='percent', type_instance='dec_util',
                            values=[float(gpu.find('utilization/decoder_util').text.split()[0])])
                # GPU memory usage
                vl.dispatch(type='memory', type_instance='used',
                            values=[1e6 * float(gpu.find('fb_memory_usage/used').text.split()[0])])
                # GPU total memory
                vl.dispatch(type='memory', type_instance='total',
                            values=[1e6 * float(gpu.find('fb_memory_usage/total').text.split()[0])])
                # GPU frequency
                vl.dispatch(type='cpufreq', type_instance='gpu_clock',
                            values=[1e6 * float(gpu.find('clocks/graphics_clock').text.split()[0])])
                # GPU memory frequency
                vl.dispatch(type='cpufreq', type_instance='mem_clock',
                            values=[1e6 * float(gpu.find('clocks/mem_clock').text.split()[0])])

    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        print("*** print_tb:")
        traceback.print_tb(exc_traceback, limit=1, file=sys.stdout)
        print("*** print_exception:")
        traceback.print_exception(exc_type, exc_value, exc_traceback,
                                  limit=2, file=sys.stdout)
        print("*** print_exc:")
        traceback.print_exc()


    try:
        vl = collectd.Values(type='gauge')
        vl.plugin = 'jobcuda'

        out = subprocess.Popen(['nvidia-smi', '-q', '-x'], stdout=subprocess.PIPE).communicate()[0]
        root = ET.fromstring(out)

        # Changed root.iter() to root.getiterator() for Python 2.6 compatibility
        gpuNumCounter={}
        for gpu in root.getiterator('gpu'):
                # GPU id
                gpuNum = gpu.find('minor_number').text

                if gpuNum in gpumap:
                    jobId = gpumap[gpuNum]

                    vl.host = jobId
                    
                    if jobId not in gpuNumCounter:
                        gpuNumCounter[jobId] = 0


                    vl.plugin_instance = 'gpu%s' % (str(gpuNumCounter[jobId]))
                    gpuNumCounter[jobId] = gpuNumCounter[jobId] + 1

                    # GPU utilization
                    vl.dispatch(type='percent', type_instance='gpu_util',
                                values=[float(gpu.find('utilization/gpu_util').text.split()[0])])
                    # GPU temperature
                    vl.dispatch(type='temperature',
                                values=[float(gpu.find('temperature/gpu_temp').text.split()[0])])
                    # GPU power draw
                    vl.dispatch(type='power', type_instance='power_draw',
                                values=[float(gpu.find('power_readings/power_draw').text.split()[0])])
                    # GPU memory utilization
                    vl.dispatch(type='percent', type_instance='mem_util',
                                values=[float(gpu.find('utilization/memory_util').text.split()[0])])
                    # GPU encoder utilization
                    vl.dispatch(type='percent', type_instance='enc_util',
                                values=[float(gpu.find('utilization/encoder_util').text.split()[0])])
                    # GPU decoder utilization
                    vl.dispatch(type='percent', type_instance='dec_util',
                                values=[float(gpu.find('utilization/decoder_util').text.split()[0])])
                    # GPU memory usage
                    vl.dispatch(type='memory', type_instance='used',
                                values=[1e6 * float(gpu.find('fb_memory_usage/used').text.split()[0])])
                    # GPU total memory
                    vl.dispatch(type='memory', type_instance='total',
                                values=[1e6 * float(gpu.find('fb_memory_usage/total').text.split()[0])])
                    # GPU frequency
                    vl.dispatch(type='cpufreq', type_instance='gpu_clock',
                                values=[1e6 * float(gpu.find('clocks/graphics_clock').text.split()[0])])
                    # GPU memory frequency
                    vl.dispatch(type='cpufreq', type_instance='mem_clock',
                                values=[1e6 * float(gpu.find('clocks/mem_clock').text.split()[0])])

    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        print("*** print_tb:")
        traceback.print_tb(exc_traceback, limit=1, file=sys.stdout)
        print("*** print_exception:")
        traceback.print_exception(exc_type, exc_value, exc_traceback,
                                  limit=2, file=sys.stdout)
        print("*** print_exc:")
        traceback.print_exc()

collectd.register_config(configure)
collectd.register_read(read)
