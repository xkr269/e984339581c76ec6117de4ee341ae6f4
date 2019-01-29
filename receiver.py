import time
from mapr.ojai.storage.ConnectionFactory import ConnectionFactory
import traceback
import sys
import base64
import settings


DRONE_ID = sys.argv[1]

DATA_FOLDER = settings.DATA_FOLDER
BUFFER_TABLE = DATA_FOLDER + "{}_buffer".format(DRONE_ID)
CLUSTER_IP = settings.CLUSTER_IP

# Create database connection
connection_str = CLUSTER_IP + ":5678?auth=basic;user=mapr;password=mapr;ssl=false"
connection = ConnectionFactory().get_connection(connection_str=connection_str)
buffer_table = connection.get_or_create_store(BUFFER_TABLE)


print("Receiving ... ")

if len(sys.argv)>2:
    if sys.argv[2] == "reset":
        buffer_table.insert_or_replace({"_id":"first_id","first_id":"0"})
        buffer_table.insert_or_replace({"_id":"last_id","last_id":"-1"})
        print("Table reset")

try:
    first_id = int(buffer_table.find_by_id("first_id")["first_id"])
except KeyError:
    first_id = 0

try:
    last_id = int(buffer_table.find_by_id("last_id")["last_id"])
except KeyError:
    last_id = first_id - 1


print("first id : {}".format(first_id))
print("last id : {}".format(last_id))


while True:
    if first_id <= last_id:
        message = buffer_table.find_by_id(str(first_id))
        encoded_image = message["image_bytes"]
        image_name = message["image_name"]
        image = base64.b64decode(encoded_image)
        with open(image_name, 'wb') as f_output:
            f_output.write(image)
        buffer_table.delete({"_id":str(first_id)})
        print("{} received and saved".format(image_name))
        first_id += 1
        buffer_table.insert_or_replace({"_id":"first_id","first_id":"{}".format(first_id)})
    else:
        last_id = int(buffer_table.find_by_id("last_id")["last_id"])
        time.sleep(0.1)
            


