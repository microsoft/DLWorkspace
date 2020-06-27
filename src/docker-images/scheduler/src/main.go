package main

import (
	"k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/client-go/informers"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/rest"
	"k8s.io/client-go/tools/cache"
	"k8s.io/klog"
)

const SCHEDULER_NAME = "DLTS"

type Scheduler struct {
	k8sClient *kubernetes.Clientset
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

	s.listPods(stopListPods)
	s.listNodes(stopListNodes)
	<-stopCh
	stopListPods <- struct{}{}
	stopListNodes <- struct{}{}
}

func (s *Scheduler) listPods(stopCh chan struct{}) {
	// list all pods from all namespaces and schedulerName is DLTS and nodeName is unassigned
	watch, err := s.k8sClient.CoreV1().Pods("").Watch(metav1.ListOptions{
		// FieldSelector: fmt.Sprintf("spec.schedulerName=%s,spec.nodeName=", SCHEDULER_NAME),
	})
	if err != nil {
		panic(err.Error())
	}

	go func(stopCh chan struct{}) {
		resultChan := watch.ResultChan()

		for {
			select {
			case <-stopCh:
				break
			case event := <-resultChan:
				p := event.Object.(*v1.Pod)

				switch event.Type {
				case "ADDED":
					s.podAdded(p)
				case "MODIFIED":
					s.podModified(p)
				case "DELETED":
					s.podDeleted(p)
				default:
					klog.Warningf("unknown event %s for pod %s/%s", event.Type, p.Namespace, p.Name)
				}
			}
		}
	}(stopCh)
}

func (s *Scheduler) podAdded(pod *v1.Pod) {
	klog.Infof("pod added: %s/%s", pod.Namespace, pod.Name)
}

func (s *Scheduler) podModified(pod *v1.Pod) {
	klog.Infof("pod modified: %s/%s", pod.Namespace, pod.Name)
}

func (s *Scheduler) podDeleted(pod *v1.Pod) {
	klog.Infof("pod deleted: %s/%s", pod.Namespace, pod.Name)
}

func (s *Scheduler) listNodes(stopCh chan struct{}) {
	factory := informers.NewSharedInformerFactory(s.k8sClient, 0)
	informer := factory.Core().V1().Nodes().Informer()

	informer.AddEventHandler(cache.ResourceEventHandlerFuncs{
		AddFunc:    s.nodeAdded,
		UpdateFunc: s.nodeUpdated,
		DeleteFunc: s.nodeDeleted,
	})

	go informer.Run(stopCh)
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
