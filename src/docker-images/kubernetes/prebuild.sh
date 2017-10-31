# Build Kubernetes core
python ../kubernetes-build/build.py
# Copy binaries here
cp ../../bin/hyperkube .
cp ../../bin/kubelet .
cp ../../bin/kubectl .
