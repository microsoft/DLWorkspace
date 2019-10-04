./deploy.py -y build
./az_tools.py create
./az_tools.py genconfig
./deploy.py runscriptonroles infra worker ./scripts/prepare_vm_disk.sh
./deploy.py nfs-server create
./deploy.py runscriptonroles infra worker ./scripts/prepare_ubuntu.sh
./deploy.py runscriptonroles infra worker ./scripts/disable_kernel_auto_updates.sh
./deploy.py genscripts
./deploy.py runscriptonroles infra worker ./scripts/dns.sh
./deploy.py -y deploy
./deploy.py -y updateworker
./deploy.py -y kubernetes labels
./deploy.py -y gpulabel
./deploy.py kubernetes start nvidia-device-plugin
./deploy.py webui
./deploy.py docker push restfulapi
./deploy.py docker push webui
./deploy.py mount
./deploy.py kubernetes start mysql
./deploy.py kubernetes start jobmanager
./deploy.py kubernetes start restfulapi
./deploy.py kubernetes start webportal
# ./deploy.py kubernetes start cloudmonitor
# ./deploy.py -y kubernetes patchprovider aztools
./deploy.py --sudo runscriptonrandmaster ./scripts/pass_secret.sh
./deploy.py runscriptonroles worker scripts/pre_download_images.sh