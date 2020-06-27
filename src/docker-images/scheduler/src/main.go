package main

import (
	"k8s.io/api/core/v1"
	"k8s.io/client-go/informers"
	"k8s.io/client-go/kubernetes"
	listerV1 "k8s.io/client-go/listers/core/v1"
	"k8s.io/client-go/rest"
	"k8s.io/client-go/tools/cache"
	"k8s.io/klog"
)

const SCHEDULER_NAME = "DLTS"

type Scheduler struct {
	k8sClient  *kubernetes.Clientset
	podLister  listerV1.PodLister
	nodeLister listerV1.NodeLister
}

func NewScheduler() *Scheduler {
	config, err := rest.InClusterConfig()
	if err != nil {
		panic(err.Error())
	}

	clientset, err := kubernetes.NewForConfig(config)
	if err != nil {
		panic(err.Error())
	}

	return &Scheduler{k8sClient: clientset}
}

func (s *Scheduler) Run(stopCh chan struct{}) {
	stopListPods := make(chan struct{})
	stopListNodes := make(chan struct{})

	s.podLister = s.listPods(stopListPods)
	s.nodeLister = s.listNodes(stopListNodes)

	<-stopCh

	stopListPods <- struct{}{}
	stopListNodes <- struct{}{}
}

func (s *Scheduler) listPods(stopCh chan struct{}) listerV1.PodLister {
	factory := informers.NewSharedInformerFactory(s.k8sClient, 0)
	pods := factory.Core().V1().Pods()
	informer := pods.Informer()

	informer.AddEventHandler(cache.ResourceEventHandlerFuncs{
		AddFunc:    s.podAdded,
		UpdateFunc: s.podUpdated,
		DeleteFunc: s.podDeleted,
	})

	go informer.Run(stopCh)
	return pods.Lister()
}

func (s *Scheduler) podAdded(obj interface{}) {
	pod, ok := obj.(*v1.Pod)
	if !ok {
		klog.Warningf("failed to cast obj to pod %v", obj)
		return
	}
	klog.Infof("pod added: %s/%s", pod.Namespace, pod.Name)
}

func (s *Scheduler) podUpdated(oldObj, newObj interface{}) {
	oldPod, ok1 := oldObj.(*v1.Pod)
	newPod, ok2 := newObj.(*v1.Pod)

	if !ok1 || !ok2 {
		klog.Warningf("failed to cast obj to node %v %v", oldObj, newObj)
		return
	}
	klog.Infof("pod updated: %s/%s -> %s/%s", oldPod.Namespace, oldPod.Name,
		newPod.Namespace, newPod.Name)
}

func (s *Scheduler) podDeleted(obj interface{}) {
	pod, ok := obj.(*v1.Pod)
	if !ok {
		klog.Warningf("failed to cast obj to pod %v", obj)
		return
	}
	klog.Infof("pod deleted: %s/%s", pod.Namespace, pod.Name)
}

func (s *Scheduler) listNodes(stopCh chan struct{}) listerV1.NodeLister {
	factory := informers.NewSharedInformerFactory(s.k8sClient, 0)
	nodes := factory.Core().V1().Nodes()
	informer := nodes.Informer()

	informer.AddEventHandler(cache.ResourceEventHandlerFuncs{
		AddFunc:    s.nodeAdded,
		UpdateFunc: s.nodeUpdated,
		DeleteFunc: s.nodeDeleted,
	})

	go informer.Run(stopCh)
	return nodes.Lister()
}

func (s *Scheduler) nodeAdded(obj interface{}) {
	node, ok := obj.(*v1.Node)
	if !ok {
		klog.Warningf("failed to cast obj to node %v", obj)
		return
	}
	klog.Infof("node added: %s", node.Name)
}

func (s *Scheduler) nodeUpdated(oldObj, newObj interface{}) {
	oldNode, ok1 := oldObj.(*v1.Node)
	newNode, ok2 := newObj.(*v1.Node)

	if !ok1 || !ok2 {
		klog.Warningf("failed to cast obj to node %v %v", oldObj, newObj)
		return
	}

	klog.Infof("node updated: %s -> %s", oldNode.Name, newNode.Name)
}

func (s *Scheduler) nodeDeleted(obj interface{}) {
	node, ok := obj.(*v1.Node)
	if !ok {
		klog.Warningf("failed to cast obj to node %v", obj)
		return
	}
	klog.Infof("node deleted: %s", node.Name)
}

func main() {
	scheduler := NewScheduler()
	stopCh := make(chan struct{})

	scheduler.Run(stopCh)
}
