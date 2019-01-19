#!/bin/sh

docker build --force-rm --pull -t maprtech/pacc:6.1.0_6.0.0_ubuntu16_yarn_fuse_streams /mapr/demo.mapr.com/teits/e984339581c76ec6117de4ee341ae6f4/Containers/count-people/docker_images/client
