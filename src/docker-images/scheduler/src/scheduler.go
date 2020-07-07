package main

import (
	"fmt"
	"k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/labels"
	"k8s.io/apimachinery/pkg/types"
	"k8s.io/apimachinery/pkg/util/wait"
	"k8s.io/client-go/kubernetes"
	listerV1 "k8s.io/client-go/listers/core/v1"
	"k8s.io/klog"
	"strconv"
	"strings"
	"sync"
	"time"
)

const SCHEDULER_NAME = "DLTS"

func IsSelectorMatchs(labels, selector map[string]string) bool {
	for k, v := range selector {
		if val, ok := labels[k]; ok && val == v {
			continue
		}
		return false
	}
	return true
}

type Scheduler struct {
	clientset *kubernetes.Clientset

	nodesMu    sync.Mutex
	nodes      map[string]*NodeInfo
	nodeLister listerV1.NodeLister

	podsMu    sync.Mutex
	pods      map[string]*PodInfo
	podLister listerV1.PodLister
}

// Not concurrency safe object
type Resource struct {
	Cpu    int64
	Memory int64
	Gpu    int64
}

func (r *Resource) Update(another *Resource) {
	r.Cpu = another.Cpu
	r.Memory = another.Memory
	r.Gpu = another.Gpu
}

func (r *Resource) CanSatisfy(request *Resource) bool {
	return r.Cpu >= request.Cpu &&
		r.Memory >= request.Memory &&
		r.Gpu >= request.Gpu
}

func (r *Resource) Sub(request *Resource) {
	r.Cpu -= request.Cpu
	r.Memory -= request.Memory
	r.Gpu -= request.Gpu
}

// Not concurrency safe object, should hold node's lock when accessing this.
// This is cache of the current resource usage, Allocatable is reported by Node
// and Allocated is resources used by pods assigned to this node.
// We will add/delete Allocated whenever we see updates from k8s or we
// assigned/preempt pods ourself. Scheduling decision is made based on this cache.
type ResourceAllocator struct {
	// Same with allocatable in node spec. These don't count used resources
	Allocatable Resource

	Allocated map[string]*Resource
}

func NewAllocator() *ResourceAllocator {
	return &ResourceAllocator{Allocated: make(map[string]*Resource)}
}

func (a *ResourceAllocator) GetFreeResource() (result *Resource) {
	result = &Resource{}
	result.Update(&a.Allocatable)

	for _, v := range a.Allocated {
		result.Sub(v)
	}
	return
}

func (a *ResourceAllocator) Use(key string, used *Resource) {
	value := &Resource{}
	value.Update(used)

	a.Allocated[key] = used
}

func (a *ResourceAllocator) Free(key string) {
	delete(a.Allocated, key)
}

type NodeInfo struct {
	mu sync.Mutex

	Name   string // assume name can not be changed
	Labels map[string]string

	allocator *ResourceAllocator

	Unschedulable bool
}

func (n *NodeInfo) GetFreeResource() *Resource {
	n.mu.Lock()
	defer n.mu.Unlock()

	return n.allocator.GetFreeResource()
}

func NewNodeInfo(node *v1.Node) *NodeInfo {
	info := &NodeInfo{
		Name:      node.Name,
		Labels:    make(map[string]string),
		allocator: NewAllocator(),

		Unschedulable: node.Spec.Unschedulable,
	}

	for k, v := range node.Labels {
		info.Labels[k] = v
	}
	allocatable := node.Status.Allocatable
	if allocatable != nil {
		cpu, memory, gpu := int64(0), int64(0), int64(0)

		if allocatable.Cpu() != nil {
			cpu = allocatable.Cpu().Value()
		}
		if allocatable.Memory() != nil {
			memory = allocatable.Memory().Value()
		}
		if val, ok := allocatable["nvidia.com/gpu"]; ok {
			gpu = val.Value()
		}
		info.allocator.Allocatable.Update(&Resource{Cpu: cpu, Memory: memory, Gpu: gpu})
	}

	return info
}

func (n *NodeInfo) Update(another *NodeInfo) {
	n.mu.Lock()
	defer n.mu.Unlock()

	n.Labels = make(map[string]string)
	for k, v := range another.Labels {
		n.Labels[k] = v
	}

	n.allocator.Allocatable.Update(&another.allocator.Allocatable)
}

func (n *NodeInfo) Use(key string, request *Resource) {
	n.mu.Lock()
	defer n.mu.Unlock()

	n.allocator.Use(key, request)
}

func (n *NodeInfo) Free(key string) {
	n.mu.Lock()
	defer n.mu.Unlock()

	n.allocator.Free(key)
}

func (n *NodeInfo) String() string {
	n.mu.Lock()
	defer n.mu.Unlock()

	free := n.allocator.GetFreeResource()

	unschedulable := "f"
	if n.Unschedulable {
		unschedulable = "t"
	}

	return fmt.Sprintf("%s[%s](c:%d,g:%d)", n.Name, unschedulable, free.Cpu, free.Gpu)
}

type PodInfo struct {
	mu sync.Mutex

	Key       string
	Name      string
	Namespace string
	UID       types.UID

	VcName   string
	UserName string
	JobId    string

	// will be empty if not scheduled
	NodeName string

	SchedulerName string

	NodeSelector map[string]string

	PreemptionAllowed bool

	// required resources
	RequiredResource Resource
}

func NewPodInfo(key string, pod *v1.Pod) *PodInfo {
	vcName := "unknown"
	userName := "unknown"
	jobId := "unknown"
	ok := true

	if vcName, ok = pod.Labels["vcName"]; !ok {
		klog.Warningf("unknown vc name for pod %s", key)
	}
	if userName, ok = pod.Labels["userName"]; !ok {
		klog.Warningf("unknown user name for pod %s", key)
	}
	if jobId, ok = pod.Labels["jobId"]; !ok {
		klog.Warningf("unknown job id for pod %s", key)
	}
	preemptionAllowedS, ok := pod.Labels["preemptionAllowed"]
	if !ok {
		preemptionAllowedS = "False"
	}
	preemptionAllowed, err := strconv.ParseBool(preemptionAllowedS)
	if err != nil {
		klog.Warningf("failed to convert preemptionAllowed %s to bool, err %v",
			preemptionAllowedS, err)
	}

	info := &PodInfo{
		Key:       key,
		Name:      pod.Name,
		Namespace: pod.Namespace,
		UID:       pod.UID,

		VcName:   vcName,
		UserName: userName,
		JobId:    jobId,
		NodeName: pod.Spec.NodeName,

		SchedulerName: pod.Spec.SchedulerName,

		NodeSelector: make(map[string]string),

		PreemptionAllowed: preemptionAllowed,
	}

	for k, v := range pod.Spec.NodeSelector {
		info.NodeSelector[k] = v
	}

	for _, container := range pod.Spec.Containers {
		requests := container.Resources.Requests
		if requests != nil {
			cpu, memory, gpu := int64(0), int64(0), int64(0)
			if requests.Cpu() != nil {
				cpu = requests.Cpu().Value()
			}
			if requests.Memory() != nil {
				memory = requests.Memory().Value()
			}
			if val, ok := requests["nvidia.com/gpu"]; ok {
				gpu = val.Value()
			}
			info.RequiredResource.Update(&Resource{Cpu: cpu, Memory: memory, Gpu: gpu})
		}
	}

	return info
}

func (p *PodInfo) String() string {
	p.mu.Lock()
	defer p.mu.Unlock()

	return fmt.Sprintf("%s(c:%d,g:%d)", p.Key, p.RequiredResource.Cpu, p.RequiredResource.Gpu)
}

func NewScheduler(clientset *kubernetes.Clientset, podLister listerV1.PodLister, nodeLister listerV1.NodeLister) *Scheduler {
	return &Scheduler{
		clientset:  clientset,
		nodes:      make(map[string]*NodeInfo),
		nodeLister: nodeLister,
		pods:       make(map[string]*PodInfo),
		podLister:  podLister,
	}
}

func (s *Scheduler) fullSync() {
	nodes, err := s.nodeLister.List(labels.Everything())
	if err != nil {
		panic(err.Error())
	}

	for _, node := range nodes {
		err := s.UpdateNode(node.Name, node)
		if err != nil {
			panic(err.Error())
		}
	}

	pods, err := s.podLister.List(labels.Everything())
	if err != nil {
		panic(err.Error())
	}

	for _, pod := range pods {
		key := fmt.Sprintf("%s/%s", pod.Namespace, pod.Name)
		err := s.UpdatePod(key, pod)
		if err != nil {
			panic(err.Error())
		}
	}
}

func (s *Scheduler) Run(stopCh <-chan struct{}) {
	s.fullSync()

	go wait.Until(s.schedule, 10*time.Second, stopCh)
	<-stopCh
}

// should treat pod as readonly
func (s *Scheduler) UpdatePod(key string, pod *v1.Pod) (returnedErr error) {
	klog.Infof("update pod %s in scheduler", key)
	s.podsMu.Lock()
	defer s.podsMu.Unlock()

	if oldPod, found := s.pods[key]; found {
		if oldPod.NodeName != "" {
			s.nodesMu.Lock()
			if oldNode, found := s.nodes[oldPod.NodeName]; found {
				oldNode.Free(oldPod.Key)
			}
			s.nodesMu.Unlock()
		}
	}

	podInfo := NewPodInfo(key, pod)
	s.pods[key] = podInfo
	if podInfo.NodeName != "" {
		s.nodesMu.Lock()
		if node, found := s.nodes[podInfo.NodeName]; found {
			node.Use(podInfo.Key, &podInfo.RequiredResource)
		}
		s.nodesMu.Unlock()
	}
	return
}

func (s *Scheduler) DeletePod(key, namespace, name string) (returnedErr error) {
	klog.Infof("delete pod %s from scheduler", key)
	s.podsMu.Lock()
	defer s.podsMu.Unlock()

	if oldPod, found := s.pods[key]; found {
		if oldPod.NodeName != "" {
			s.nodesMu.Lock()
			if oldNode, found := s.nodes[oldPod.NodeName]; found {
				oldNode.Free(oldPod.Key)
			}
			s.nodesMu.Unlock()
		}
	}

	delete(s.pods, key)
	return
}

// should treat node as readonly
func (s *Scheduler) UpdateNode(name string, node *v1.Node) (returnedErr error) {
	s.nodesMu.Lock()
	defer s.nodesMu.Unlock()

	oldNode := s.nodes[name]
	newNode := NewNodeInfo(node)

	if oldNode == nil {
		klog.Infof("add node %s to scheduler", newNode.String())
		s.nodes[name] = newNode
	} else {
		klog.Infof("update node %s -> %s in scheduler", oldNode.String(), newNode.String())
		oldNode.Update(newNode)
	}

	return
}

func (s *Scheduler) DeleteNode(name string) (returnedErr error) {
	klog.Infof("delete node %s from scheduler", name)
	s.nodesMu.Lock()
	defer s.nodesMu.Unlock()

	delete(s.nodes, name)
	return
}

func (s *Scheduler) bindPodToNode(pod *PodInfo, node *NodeInfo) {
	klog.Infof("bind pod %s to node %s", pod.String(), node.String())

	s.clientset.CoreV1().Pods(pod.Namespace).Bind(&v1.Binding{
		ObjectMeta: metav1.ObjectMeta{
			Name:      pod.Name,
			Namespace: pod.Namespace,
		},
		Target: v1.ObjectReference{
			APIVersion: "v1",
			Kind:       "Node",
			Name:       node.Name,
		},
	})

	timestamp := time.Now().UTC()

	s.clientset.CoreV1().Events(pod.Namespace).Create(&v1.Event{
		Count:          1,
		Message:        "Successfully scheduled",
		Reason:         "Scheduled",
		LastTimestamp:  metav1.NewTime(timestamp),
		FirstTimestamp: metav1.NewTime(timestamp),
		Type:           "Normal",
		Source: v1.EventSource{
			Component: SCHEDULER_NAME + " scheduler",
		},
		InvolvedObject: v1.ObjectReference{
			Kind:      "Pod",
			Name:      pod.Name,
			Namespace: pod.Namespace,
			UID:       pod.UID,
		},
		ObjectMeta: metav1.ObjectMeta{
			GenerateName: pod.Name + "-",
		},
	})
}

func (s *Scheduler) scheduleFailed(pod *PodInfo, counter *SchedulerCounter) {
	timestamp := time.Now().UTC()

	message := fmt.Sprintf("Failed to schedule: %d resource not enough nodes, %d selector mismatch nodes, unschedulable %d",
		counter.ResourceNotEnought, counter.SelectorNotMatch, counter.Unschedulable)

	s.clientset.CoreV1().Events(pod.Namespace).Create(&v1.Event{
		Count:          1,
		Message:        message,
		Reason:         "Scheduled",
		LastTimestamp:  metav1.NewTime(timestamp),
		FirstTimestamp: metav1.NewTime(timestamp),
		Type:           "Normal",
		Source: v1.EventSource{
			Component: SCHEDULER_NAME + " scheduler",
		},
		InvolvedObject: v1.ObjectReference{
			Kind:      "Pod",
			Name:      pod.Name,
			Namespace: pod.Namespace,
			UID:       pod.UID,
		},
		ObjectMeta: metav1.ObjectMeta{
			GenerateName: pod.Name + "-",
		},
	})
}

type SchedulerCounter struct {
	ResourceNotEnought int
	SelectorNotMatch   int
	Unschedulable      int
}

func (c *SchedulerCounter) String() string {
	return fmt.Sprintf("r:%d,s:%d,u:%d", c.ResourceNotEnought, c.SelectorNotMatch, c.Unschedulable)
}

// whenever want to lock pods and nodes, should always lock pods first to avoid deadlock
func (s *Scheduler) schedule() {
	startTime := time.Now()
	defer func() {
		klog.Infof("spent %v in one scheduling pass", time.Since(startTime))
	}()

	s.podsMu.Lock()
	s.nodesMu.Lock()
	defer s.podsMu.Unlock()
	defer s.nodesMu.Unlock()

	podsInfo := make([]string, 0)
	for _, pod := range s.pods {
		if pod.SchedulerName == SCHEDULER_NAME {
			podsInfo = append(podsInfo, pod.String())
		}
	}

	nodesInfo := make([]string, 0)
	for _, node := range s.nodes {
		// debug
		if node.Labels["worker"] == "active" {
			nodesInfo = append(nodesInfo, node.String())
		}
	}

	klog.Infof("start scheduling %v to %v",
		strings.Join(podsInfo, "|"), strings.Join(nodesInfo, "|"))

	// scheduling

	for _, pod := range s.pods {
		if pod.NodeName != "" || pod.SchedulerName != SCHEDULER_NAME {
			continue
		}
		scheduled := false
		schedulerCounter := &SchedulerCounter{}

		// TODO sort according to available resource to avoid fragmentation
		for _, node := range s.nodes {
			if node.Unschedulable {
				schedulerCounter.Unschedulable += 1
				continue
			}

			if !IsSelectorMatchs(node.Labels, pod.NodeSelector) {
				schedulerCounter.SelectorNotMatch += 1
				continue
			}

			// TODO cache free
			free := node.GetFreeResource()

			if !free.CanSatisfy(&pod.RequiredResource) {
				schedulerCounter.ResourceNotEnought += 1
				continue
			}

			node.Use(pod.Key, &pod.RequiredResource)

			s.bindPodToNode(pod, node)
			scheduled = true

			break
		}

		if !scheduled {
			s.scheduleFailed(pod, schedulerCounter)
			klog.Infof("failed to schedule %s in one pass: %s",
				pod.Key, schedulerCounter)
		}
	}
}
