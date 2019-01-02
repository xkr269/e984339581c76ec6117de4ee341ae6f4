#! /usr/bin/python

import os

# Retrieves current cluster name
with open('/opt/mapr/conf/mapr-clusters.conf', 'r') as f:
    first_line = f.readline()
    cluster_name = first_line.split(' ')[0]

command_line = "sudo pkill -f carwatch"
print(command_line)
os.system(command_line)

command_line = "sudo pkill -f centralprocess"
print(command_line)
os.system(command_line)

command_line = "sudo pkill -f localfront"
print(command_line)
os.system(command_line)

command_line = "sudo pkill -f globalfront"
print(command_line)
os.system(command_line)

command_line = "sudo rm -rf /mapr/" + cluster_name + "/tables"
print(command_line)
os.system(command_line)

command_line = "sudo mkdir /mapr/" + cluster_name + "/tables"
print(command_line)
os.system(command_line)

command_line = "sudo maprcli table create -path /tables/cargkm -tabletype json"
print(command_line)
os.system(command_line)

command_line = "sudo maprcli table cf edit -path /tables/cargkm -cfname default readperm p -writeperm p -traverseperm p"
print(command_line)
os.system(command_line)

command_line = "sudo mapr importJSON -src /mapr/" + cluster_name + "/demobdp2018/cargkm.json -dst /mapr/" + cluster_name + "/tables/cargkm -mapreduce false"
print(command_line)
os.system(command_line)


command_line = "sudo maprcli table create -path /tables/count -tabletype json"
print(command_line)
os.system(command_line)

command_line = "sudo maprcli table create -path /tables/raw -tabletype json"
print(command_line)
os.system(command_line)

command_line = "sudo maprcli table create -path /tables/countries -tabletype json"
print(command_line)
os.system(command_line)


command_line = "sudo rm -rf /mapr/" + cluster_name + "/streams"
print(command_line)
os.system(command_line)

command_line = "sudo mkdir /mapr/" + cluster_name + "/streams"
print(command_line)
os.system(command_line)

command_line = "sudo rm -rf /mapr/" + cluster_name + "/countries"
print(command_line)
os.system(command_line)

command_line = "sudo mkdir /mapr/" + cluster_name + "/countries"
print(command_line)
os.system(command_line)

command_line = "sudo rm -rf logs"
print(command_line)
os.system(command_line)

command_line = "sudo mkdir logs/"
print(command_line)
os.system(command_line)

