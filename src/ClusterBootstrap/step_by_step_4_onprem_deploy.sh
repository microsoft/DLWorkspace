./deploy.py nfs-server create
./deploy.py runscriptonroles infra worker ./scripts/prepare_ubuntu.sh
./deploy.py runscriptonroles infra worker ./scripts/disable_kernel_auto_updates.sh
./deploy.py runscriptonroles infra worker ./scripts/docker_network_gc_setup.sh
./deploy.py genscripts
./deploy.py runscriptonroles infra worker ./scripts/dns.sh
./deploy.py -y deploy
./deploy.py -y updateworkerinparallel
./deploy.py -y kubernetes labels
./deploy.py -y gpulabel
./deploy.py kubernetes start nvidia-device-plugin
./deploy.py kubernetes start flexvolume
./deploy.py webui
./deploy.py docker push restfulapi
./deploy.py docker push webui
./deploy.py docker push watchdog
./deploy.py docker push gpu-reporter
./deploy.py docker push reaper
./deploy.py docker push job-exporter
./deploy.py mount
./deploy.py kubernetes start mysql
./deploy.py kubernetes start jobmanager
./deploy.py kubernetes start restfulapi
./deploy.py kubernetes start webportal
./deploy.py --sudo runscriptonrandmaster ./scripts/pass_secret.sh
./deploy.py runscriptonroles worker scripts/pre_download_images.sh