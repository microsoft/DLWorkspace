package main

import (
	"fmt"
	"k8s.io/api/core/v1"
	apiErrors "k8s.io/apimachinery/pkg/api/errors"
	"k8s.io/apimachinery/pkg/util/wait"
	"k8s.io/client-go/informers"
	"k8s.io/client-go/kubernetes"
	listerV1 "k8s.io/client-go/listers/core/v1"
	"k8s.io/client-go/rest"
	"k8s.io/client-go/tools/cache"
	"k8s.io/client-go/util/workqueue"
	"k8s.io/klog"
	"strings"
	"time"
)

// Syncer is mostly boilerplate code of k8s controller. It watches and list pods
// and nodes from api server.
// To understand these boilerplate code, please refer
// https://engineering.bitnami.com/articles/a-deep-dive-into-kubernetes-controllers.html
type Syncer struct {
	podWorkerNum  int32
	nodeWorkerNum int32

	clientset *kubernetes.Clientset

	podInformer cache.SharedIndexInformer
	podLister   listerV1.PodLister
	// use queue here to unblock informer
	podQueue workqueue.RateLimitingInterface

	nodeInformer cache.SharedIndexInformer
	nodeLister   listerV1.NodeLister
	nodeQueue    workqueue.RateLimitingInterface

	scheduler *Scheduler
}

func NewSyncer(podWorkerNum, nodeWorkerNum int32) *Syncer {
	config, err := rest.InClusterConfig()
	if err != nil {
		panic(err.Error())
	}

	clientset := kubernetes.NewForConfigOrDie(config)

	podListerInformer := informers.NewSharedInformerFactory(clientset, 0).Core().V1().Pods()
	podInformer := podListerInformer.Informer()
	podLister := podListerInformer.Lister()
	podQueue := workqueue.NewRateLimitingQueue(workqueue.DefaultControllerRateLimiter())

	nodeListerInformer := informers.NewSharedInformerFactory(clientset, 0).Core().V1().Nodes()
	nodeInformer := nodeListerInformer.Informer()
	nodeLister := nodeListerInformer.Lister()
	nodeQueue := workqueue.NewRateLimitingQueue(workqueue.DefaultControllerRateLimiter())

	s := &Syncer{
		podWorkerNum:  podWorkerNum,
		nodeWorkerNum: nodeWorkerNum,

		clientset: clientset,

		podInformer: podInformer,
		podLister:   podLister,
		podQueue:    podQueue,

		nodeInformer: nodeInformer,
		nodeLister:   nodeLister,
		nodeQueue:    nodeQueue,

		scheduler: NewScheduler(clientset, podLister, nodeLister),
	}

	podInformer.AddEventHandler(cache.ResourceEventHandlerFuncs{
		AddFunc:    s.podAdded,
		UpdateFunc: s.podUpdated,
		DeleteFunc: s.podDeleted,
	})

	nodeInformer.AddEventHandler(cache.ResourceEventHandlerFuncs{
		AddFunc:    s.nodeAdded,
		UpdateFunc: s.nodeUpdated,
		DeleteFunc: s.nodeDeleted,
	})

	return s
}

// should not return until the cache is fully synced
func (s *Syncer) Run(stopCh <-chan struct{}) {
	go s.nodeInformer.Run(stopCh)
	go s.podInformer.Run(stopCh)

	if !cache.WaitForCacheSync(
		stopCh,
		s.nodeInformer.HasSynced,
		s.podInformer.HasSynced) {
		panic(fmt.Errorf("failed to WaitForCacheSync"))
	}

	for i := int32(0); i < s.nodeWorkerNum; i++ {
		id := i
		go wait.Until(func() { s.nodeWorker(id) }, time.Second, stopCh)
	}

	for i := int32(0); i < s.podWorkerNum; i++ {
		id := i
		go wait.Until(func() { s.podWorker(id) }, time.Second, stopCh)
	}

	go s.scheduler.Run(stopCh)

	<-stopCh
}

func (s *Syncer) castToPod(obj interface{}) *v1.Pod {
	pod, ok := obj.(*v1.Pod)
	if !ok {
		panic(fmt.Errorf("failed to cast obj to pod %v", obj))
	}
	return pod
}

func (s *Syncer) enqueuePod(obj interface{}, event string) {
	pod := s.castToPod(obj)

	key := fmt.Sprintf("%s/%s", pod.Namespace, pod.Name)
	klog.Infof("pod %s: %s", event, key)

	s.podQueue.Add(key)
}

func (s *Syncer) podAdded(obj interface{}) {
	s.enqueuePod(obj, "added")
}

func (s *Syncer) podUpdated(oldObj, newObj interface{}) {
	s.enqueuePod(newObj, "updated")
}

func (s *Syncer) podDeleted(obj interface{}) {
	s.enqueuePod(obj, "deleted")
}

func (s *Syncer) podWorker(id int32) {
	defer klog.Errorf("Stopping podWorker-%v", id)
	klog.Infof("Running podWorker-%v", id)

	for s.processPod(id) {
	}
}

func (s *Syncer) processPod(id int32) bool {
	// block get
	key, quit := s.podQueue.Get()
	if quit {
		return false
	}

	defer s.podQueue.Done(key)

	klog.Infof("worker-%v get pod %s", id, key)

	err := s.syncPod(key.(string))
	if err == nil {
		s.podQueue.Forget(key)
	} else {
		// add back to retry
		klog.Errorf("worker-%v failed to sync pod %s", id, key)
		s.podQueue.AddRateLimited(key)
	}

	return true
}

func (s *Syncer) syncPod(key string) (returnedErr error) {
	parts := strings.Split(key, "/")
	if len(parts) != 2 {
		panic(fmt.Errorf("unknown pod key %s", key))
	}
	namespace := parts[0]
	podName := parts[1]

	localPod, err := s.podLister.Pods(namespace).Get(podName)
	if err != nil {
		if apiErrors.IsNotFound(err) {
			returnedErr = s.scheduler.DeletePod(key, namespace, podName)
			return
		} else {
			return fmt.Errorf("failed to get pod %s from local cache: %v", key, err)
		}
	} else {
		returnedErr = s.scheduler.UpdatePod(key, localPod)
	}
	return
}

func (s *Syncer) castToNode(obj interface{}) *v1.Node {
	node, ok := obj.(*v1.Node)
	if !ok {
		panic(fmt.Errorf("failed to cast obj to node %v", obj))
	}
	return node
}

func (s *Syncer) enqueueNode(obj interface{}, event string) {
	node := s.castToNode(obj)

	key := node.Name
	klog.Infof("node %s: %s", event, key)
	s.nodeQueue.Add(key)
}

func (s *Syncer) nodeAdded(obj interface{}) {
	s.enqueueNode(obj, "added")
}

func (s *Syncer) nodeUpdated(oldObj, newObj interface{}) {
	s.enqueueNode(newObj, "updated")
}

func (s *Syncer) nodeDeleted(obj interface{}) {
	s.enqueueNode(obj, "deleted")
}

func (s *Syncer) nodeWorker(id int32) {
	defer klog.Infof("Stopping nodeWorker-%v", id)
	klog.Infof("Running nodeWorker-%v", id)

	for s.processNode(id) {
	}
}

func (s *Syncer) processNode(id int32) bool {
	// block get
	key, quit := s.nodeQueue.Get()
	if quit {
		return false
	}

	defer s.nodeQueue.Done(key)

	klog.Infof("worker-%v get node %s", id, key)

	err := s.syncNode(key.(string))
	if err == nil {
		s.nodeQueue.Forget(key)
	} else {
		// add back to retry
		klog.Errorf("worker-%v failed to sync pod %s", id, key)
		s.nodeQueue.AddRateLimited(key)
	}

	return true
}

func (s *Syncer) syncNode(key string) (returnedErr error) {
	localNode, err := s.nodeLister.Get(key)
	if err != nil {
		if apiErrors.IsNotFound(err) {
			returnedErr = s.scheduler.DeleteNode(key)
			return
		} else {
			return fmt.Errorf("failed to get node %s from local cache: %v", key, err)
		}
	} else {
		returnedErr = s.scheduler.UpdateNode(key, localNode)
	}
	return
}
