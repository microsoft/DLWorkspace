package main

import (
	"k8s.io/klog"
	"os"
	"os/signal"
	"syscall"
)

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
	syncer := NewSyncer(10, 3)

	stopCh := stopOnSignal()

	syncer.Run(stopCh)

	<-stopCh
}
