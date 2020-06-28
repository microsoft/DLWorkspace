package main

import (
	"k8s.io/klog"
	"os"
	"os/signal"
	"syscall"
)

const SCHEDULER_NAME = "DLTS"

func stopOnSignal() <-chan struct{} {
	stopCh := make(chan struct{})

	signalCh := make(chan os.Signal, 1)
	signal.Notify(signalCh, syscall.SIGINT, syscall.SIGTERM)
	go func() {
		s := <-signalCh
		klog.Warningf("Received signal: %v", s)
		close(stopCh)
	}()

	return stopCh
}

func main() {
	syncer := NewSyncer(int32(3), int32(3))

	syncer.Run(stopOnSignal())
}
