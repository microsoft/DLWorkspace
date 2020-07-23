package main

import (
	"fmt"
	"os"
	"os/exec"
	"os/signal"
	"syscall"
	"time"
)

func main() {
	if len(os.Args) == 1 {
		fmt.Fprintf(os.Stderr, "[init] Usage: %s cmd to run\n", os.Args[0])
		os.Exit(1)
	}

	stopCh := make(chan bool, 1)
	go waitOrphans(stopCh)

	err := run(os.Args[1:]...)

	stopCh <- true

	if exiterr, ok := err.(*exec.ExitError); ok {
		if status, ok := exiterr.Sys().(syscall.WaitStatus); ok {
			now := time.Now()
			fmt.Fprintf(os.Stderr, "[init] %v exit code: %d\n", now.UTC(), status.ExitStatus())
			os.Exit(status.ExitStatus())
		} else {
			now := time.Now()
			fmt.Fprintf(os.Stderr, "[init] %v unknown exiterr %v\n", now.UTC(), exiterr)
			os.Exit(2)
		}
	} else if err == nil {
		now := time.Now()
		fmt.Fprintf(os.Stderr, "[init] %v success\n", now.UTC())
		os.Exit(0)
	} else {
		fmt.Fprintf(os.Stderr, "[init] failed to run %v with error %v\n", os.Args[1:], err)
		os.Exit(2)
	}
}

func waitOrphans(stopCh chan bool) {
	for {
		var status syscall.WaitStatus

		pid, _ := syscall.Wait4(-1, &status, syscall.WNOHANG, nil)

		if pid <= 0 {
			// no orphan
			time.Sleep(1 * time.Second)
		} else {
			// reap orphan
			continue
		}

		select {
		case <-stopCh:
			return
		default:
		}
	}
}

func run(command ...string) error {
	sigs := make(chan os.Signal, 1)
	defer close(sigs)
	signal.Notify(sigs)
	defer signal.Reset()

	cmd := exec.Command(command[0], command[1:]...)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	cmd.SysProcAttr = &syscall.SysProcAttr{Setpgid: true}

	go func() {
		for sig := range sigs {
			if sig != syscall.SIGCHLD {
				fmt.Fprintf(os.Stderr, "[init] received signal %d\n", sig)
				syscall.Kill(-cmd.Process.Pid, sig.(syscall.Signal))
			}
		}
	}()

	return cmd.Run()
}
