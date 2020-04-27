# Frequently asked questions (FAQ) on GlustserFS deployment. 

* Glusterd fail to start. 

    * Checking log of tail -n 100 /var/log/glusterfs/etc-glusterfs-glusterd.vol.log
        with failure: "0-socket.management: binding to  failed: Address already in use"
      
      You may have start a glusterfs pod before the prior glusterfs pod is shutdown. The port used by glusterd is still occupied, so that it can't be used for the new pod. Please make sure that you shutdown the glusterfs service via:
      ```
      ./deploy.py kubernetes stop glusterfs
      ```
      check and make sure all glusterfs pods have been shotdown:
      ```
      ./deploy.py kubectl get pods
      ```
      before launch a new glusterfs service. 

* Volume fail to start
    Check log of tail -n 100 /var/log/glusterfs/launch/launch.log, we have failure "Commit failed on localhost. Please check log file for details."

    Sometime, when you are formatting the volume, it is put in a bad state. Please do follows:
    
    1. go to one of the glusterfs node, and do a force volume start. 
      ```
      gluster volume start [VOLUME_NAME] force
      ```
    2. Shutdown glusterfs pod 
    3. Restart the pod to resume operation. 
    

      

  