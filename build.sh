#!/bin/bash
commit_id=${BUILD_ID}-$(git rev-parse --short HEAD)
echo $commit_id> commit_id.txt
#remove aai4b-nmt-inference image(s) from build server to avoid space issues
#docker images | grep aai4b-nmt-inference | awk '{print $3}' | xargs docker rmi
#docker build --build-arg D_F=$DEBUG_FLUSH -t anuvaadio/$image_name:$commit_id .
docker build -t anuvaadio/$image_name:$commit_id .
docker login -u $dockerhub_user -p $dockerhub_pass
docker push anuvaadio/$image_name:$commit_id
