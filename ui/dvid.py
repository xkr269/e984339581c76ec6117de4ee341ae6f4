import tellopy, av, time, cv2, numpy
from confluent_kafka import Producer

VIDEO_STREAM = '/mapr/' + cluster_name + '/video_stream'   # Video stream path
p = Producer({'streams.producer.default.stream': VIDEO_STREAM})


drone = tellopy.Tello()
try:
    # Connect to the drone
    drone.connect()
    drone.wait_for_connection(600.0)
    drone.set_video_encoder_rate(1)
    # Init a video stream
    container = av.open(drone.get_video_stream())
    # Loop until timeout
    while True:
        for frame in container.decode(video=0):
            # Store Image name
            img_name_str = 'frame-%06d.jpg' % frame.index
            # Convert frame to image
            frameIMG = cv2.cvtColor(numpy.array(frame.to_image()), cv2.COLOR_RGB2BGR)
            ret, jpeg = cv2.imencode('.png', frameIMG)

            # If streaming
            if stream_args:
                print('  ###  Streaming frame : ' + img_name_str)
                p.produce("raw", jpeg.tobytes())

            # Time control
            elapsed_time = int(time.time() - start_time)
            print('  ##  Elapsed:' + str(elapsed_time) + ' seconds / Image name:' + img_name_str)


# Catch exceptions
except Exception as ex:
    #exc_type, exc_value, exc_traceback = sys.exc_info()
    #traceback.print_exception(exc_type, exc_value, exc_traceback)
    print(ex)

# Clean exit w/landing + disconnect
finally:
    print('Disconnecting...')
    drone.quit()
