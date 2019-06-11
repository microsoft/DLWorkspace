from functools import wraps
import threading
from datetime import datetime
from datetime import timedelta
import time
import Queue
import copy

# decorator (with different TTL for each function)
# No removal of entries (designed for small number of entries to be always kept in memory)
# option to invalidate specific entries
# non-blocking (updates done by background thread; stale data returned while fetching in progress) : avoids thundering herd for data source
def fcache(TTLInSec=30):
    def fcache_decorator(func):
        @wraps(func)
        def wrapped_function(*args, **kwargs):
            val = CacheManager.GetValue(func, TTLInSec, args)
            if (None == val):               
                return func(*args)
            return copy.deepcopy(val[0])           
        return wrapped_function
    return fcache_decorator



class CacheManager(object):
    data = {}
    taskQueue = Queue.Queue()
    pendingTasks = set()

    @staticmethod
    def Invalidate(funcName, *args):
        key = CacheManager._GetKey(funcName, args)
        if key in CacheManager.data:
            val = CacheManager.data[key]
            CacheManager.data[key] = [val[0], datetime.now()]
            print("Cache invalidated " + key)

    @staticmethod
    def GetValue(func, ttl, args):
        val = None
        key = CacheManager._GetKey(func.__name__, args)
        needUpdate = False
        if key not in CacheManager.data:
            print("Cache miss " + key)
            needUpdate = True
        else:           
            val = CacheManager.data[key]
            print("Cache hit " + key + " " + str(val[1]) + " " + str(len(CacheManager.data)) + " " + str(CacheManager.taskQueue.qsize()))
            if CacheManager._Invalid(val):
                needUpdate = True

        if needUpdate and key not in CacheManager.pendingTasks:
            CacheManager.taskQueue.put((func, ttl, args))
            CacheManager.pendingTasks.add(key)
        
        return val

    
    @staticmethod
    def _GetKey(funcName, args):
        key = funcName
        for arg in args:
            key += "__"
            key += str(arg)
        return key

    @staticmethod
    def _Invalid(value):
        if value[1] < datetime.now():
            return True
        return False

    @staticmethod
    def _WorkerThreadFunc():
        while (True):
            while not CacheManager.taskQueue.empty():
                task = CacheManager.taskQueue.get()
                key = CacheManager._GetKey(task[0].__name__, task[2])
                if key not in CacheManager.data or CacheManager._Invalid(CacheManager.data[key]):
                    result = task[0](*(task[2]))
                    CacheManager.data[key] = [result, datetime.now() + timedelta(seconds=int(task[1]))]
                    print("Cache inserted " + key)
                CacheManager.pendingTasks.remove(key)
            time.sleep(0.001)

workerThread = threading.Thread(target=CacheManager._WorkerThreadFunc, args=())
workerThread.daemon = True
workerThread.start()

