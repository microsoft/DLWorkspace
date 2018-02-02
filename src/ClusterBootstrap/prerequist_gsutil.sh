export CLOUD_SDK_REPO="cloud-sdk-$(lsb_release -c -s)"
echo "deb http://packages.cloud.google.com/apt $CLOUD_SDK_REPO main" | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -
sudo apt-get update && sudo apt-get install -y google-cloud-sdk
sudo apt-get install -y google-cloud-sdk-app-engine-java google-cloud-sdk-app-engine-python google-cloud-sdk-app-engine-java google-cloud-sdk-app-engine-go google-cloud-sdk-datalab google-cloud-sdk-datastore-emulator google-cloud-sdk-pubsub-emulator google-cloud-sdk-cbt google-cloud-sdk-bigtable-emulator kubectl
sudo pip install --upgrade google-api-python-client
# Please perform the command below to log into your account.
# gcloud init
