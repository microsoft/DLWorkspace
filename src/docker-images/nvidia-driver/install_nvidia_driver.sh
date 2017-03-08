#!/bin/bash

#other environment variables are setup in Dockerfile
CURRENT_DRIVER=/opt/nvidia-driver/current

function nvidiaPresent {
  [[ -f /proc/driver/nvidia/version ]] || return 1
  grep -q $NVIDIA_VERSION /proc/driver/nvidia/version || return 2
  lsmod | grep -qE "^nvidia" || return 3
  [[ -e /dev/nvidia0 ]] || return 4
  [[ -e $NV_DRIVER/lib64/libnvidia-ml.so ]] || return 5
  return 0
}

echo ======== If NVIDIA present exit early =========
nvidiaPresent && [[ -L $CURRENT_DRIVER ]] && exit 0

echo ======== If NVIDIA driver already running uninstall it =========
lsmod | grep -qE "^nvidia" &&
{
    DEP_MODS=`lsmod | tr -s " " | grep -E "^nvidia" | cut -f 4 -d " "`
    for mod in ${DEP_MODS//,/ }
    do
        rmmod $mod ||
        {
            echo "The driver $mod is still in use, can't unload it."
            exit 1
        }
    done
    rmmod nvidia ||
    {
        echo "The driver nvidia is still in use, can't unload it."
        exit 1
    }
}


cd /opt/kernels/linux 
git checkout v`uname -r | sed "s/-.*//"`-coreos || exit $?
/opt/kernels/linux/scripts/config --disable CC_STACKPROTECTOR_STRONG || exit $?
make modules_prepare || exit $?
echo "#define UTS_RELEASE \""$(uname -r)"\"" > /opt/kernels/linux/include/generated/utsrelease.h 
echo `uname -r` > /opt/kernels/linux/include/config/kernel.release 

echo $NV_DRIVER/lib > /etc/ld.so.conf.d/nvidia-drivers.conf
echo $NV_DRIVER/lib64 >> /etc/ld.so.conf.d/nvidia-drivers.conf
mkdir -p $NV_DRIVER/lib $NV_DRIVER/lib64 $NV_DRIVER/bin || exit $?

cd /opt/nvidia/nvidia_installers 
./NVIDIA-Linux-x86_64-$NVIDIA_VERSION/nvidia-installer -q -a -n -s --kernel-source-path=/opt/kernels/linux/ \
    --utility-prefix=$NV_DRIVER \
    --opengl-prefix=$NV_DRIVER \
    --x-prefix=$NV_DRIVER \
    --compat32-prefix=$NV_DRIVER \
    --opengl-libdir=lib64 \
    --utility-libdir=lib64 \
    --x-library-path=lib64 \
    --compat32-libdir=lib \
    -N || exit $?


echo === Loading NVIDIA UVM module
modprobe nvidia-uvm || exit $?

echo === Creating /dev entries
UVM_MAJOR=`grep nvidia-uvm /proc/devices | awk '{print $1}'`
FRONTEND_MAJOR=`grep nvidia-frontend /proc/devices | awk '{print $1}'`
rm -f /dev/nvidia* 2>/dev/null
mknod -m 666 /dev/nvidia-uvm c $UVM_MAJOR 0 || exit $?
mknod -m 666 /dev/nvidiactl c $FRONTEND_MAJOR 255 || exit $?
GPU_COUNT=`ls /proc/driver/nvidia/gpus | wc -l`
echo === Number of GPUS: $GPU_COUNT
for ((GPU=0; GPU<$GPU_COUNT; GPU++)); do
  mknod -m 666 /dev/nvidia$GPU c $FRONTEND_MAJOR $GPU || exit $?
done

ls -la /dev/nvidia*

echo === Check if everything is loaded
nvidiaPresent || exit $?

echo === Checking the driver
nvidia-smi || exit $?

cp /usr/bin/nvidia-modprobe $NV_DRIVER/bin
rm -r /opt/bin/nvidia*
cp -r $NV_DRIVER/bin/* /opt/bin

echo === Updating current driver
# Remove previous soft link for current driver
[[ -L $CURRENT_DRIVER ]] &&
{
    rm -f $CURRENT_DRIVER || exit $?
}

# Remove benign issue where "current" exists as directory
[[ -d $CURRENT_DRIVER ]] &&
{
    echo === Removing current driver as directory, should be soft link
    rm -rf $CURRENT_DRIVER || exit $?
}

ln -s -f $NV_DRIVER $CURRENT_DRIVER || exit $?

[[ -L $CURRENT_DRIVER ]] ||
{
    echo ======== Current drivers link not updated =========
    exit 1
}

echo NVIDIA driver installed successfully



#insmod /opt/nvidia/nvidia_installers/NVIDIA-Linux-x86_64-375.20/kernel/nvidia.ko && \
#insmod /opt/nvidia/nvidia_installers/NVIDIA-Linux-x86_64-375.20/kernel/nvidia-uvm.ko && \


