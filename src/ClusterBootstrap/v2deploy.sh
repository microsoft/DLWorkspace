# !/bin/bash
rm -rf deploy/* cloudinit* az_complementary.yaml
# # render
./cloud_init_deploy.py clusterID
./cloud_init_aztools.py -cnf config.yaml -o az_complementary.yaml prerender
./cloud_init_aztools.py -cnf config.yaml -o scripts/deploy_framework.sh deploy
# # generate mounting.yaml, which later would be used by both `renderspecific nfs` and `renderspecific infra/worker(via mnt_fs_svc.sh)`
./cloud_init_deploy.py -cnf config.yaml -cnf az_complementary.yaml rendermount
./cloud_init_deploy.py -cnf config.yaml -cnf az_complementary.yaml renderspecific nfs
./cloud_init_deploy.py -cnf config.yaml -cnf az_complementary.yaml rendergeneric infra
./cloud_init_deploy.py -cnf config.yaml -cnf az_complementary.yaml rendergeneric worker
./cloud_init_deploy.py -cnf config.yaml -cnf az_complementary.yaml packcloud common
./cloud_init_deploy.py -cnf config.yaml -cnf az_complementary.yaml packcloud infra
./cloud_init_deploy.py -cnf config.yaml -cnf az_complementary.yaml packcloud worker
./cloud_init_deploy.py -cnf config.yaml -cnf az_complementary.yaml packcloud nfs
./cloud_init_deploy.py -cnf config.yaml -cnf az_complementary.yaml renderspecific infra
./cloud_init_deploy.py -cnf config.yaml -cnf az_complementary.yaml renderspecific worker
# # push dockers
tar -cvf cloudinit.tar cloudinit
./cloud_init_deploy.py -cnf config.yaml -cnf az_complementary.yaml docker push cloudinit
./cloud_init_deploy.py -cnf config.yaml -cnf az_complementary.yaml docker push restfulapi
# ./cloud_init_deploy.py -cnf config.yaml -cnf az_complementary.yaml docker push dashboard
./cloud_init_deploy.py -cnf config.yaml -cnf az_complementary.yaml docker push watchdog
./cloud_init_deploy.py -cnf config.yaml -cnf az_complementary.yaml docker push gpu-reporter
./cloud_init_deploy.py -cnf config.yaml -cnf az_complementary.yaml docker push reaper
./cloud_init_deploy.py -cnf config.yaml -cnf az_complementary.yaml docker push job-exporter
./cloud_init_deploy.py -cnf config.yaml -cnf az_complementary.yaml docker push init-container
./cloud_init_deploy.py -cnf config.yaml -cnf az_complementary.yaml docker push repairmanager
./cloud_init_aztools.py -cnf config.yaml -cnf az_complementary.yaml -o scripts/add_machines.sh addmachines
# # deploy
./scripts/deploy_framework.sh
./scripts/add_machines.sh
./cloud_init_aztools.py -cnf config.yaml -cnf az_complementary.yaml interconnect
# # get status
./cloud_init_aztools.py -cnf config.yaml -o brief.yaml listcluster
