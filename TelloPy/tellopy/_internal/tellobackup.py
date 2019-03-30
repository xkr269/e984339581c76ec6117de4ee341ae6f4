# import threading
# import socket
# import time
# import datetime
# import struct
# import sys
# import os

# from . import crc
# from . import logger
# from . import event
# from . import state
# from . import error
# from . import video_stream
# from . utils import *
# from . protocol import *
# from . import dispatcher

# log = logger.Logger('Tello')


# class Tello(object):
#     EVENT_CONNECTED = event.Event('connected')
#     EVENT_WIFI = event.Event('wifi')
#     EVENT_LIGHT = event.Event('light')
#     EVENT_FLIGHT_DATA = event.Event('fligt_data')
#     EVENT_LOG_HEADER = event.Event('log_header')
#     EVENT_LOG = EVENT_LOG_HEADER
#     EVENT_LOG_RAWDATA = event.Event('log_rawdata')
#     EVENT_LOG_DATA = event.Event('log_data')
#     EVENT_LOG_CONFIG = event.Event('log_config')
#     EVENT_TIME = event.Event('time')
#     EVENT_VIDEO_FRAME = event.Event('video frame')
#     EVENT_VIDEO_DATA = event.Event('video data')
#     EVENT_DISCONNECTED = event.Event('disconnected')
#     EVENT_FILE_RECEIVED = event.Event('file received')
#     # internal events
#     __EVENT_CONN_REQ = event.Event('conn_req')
#     __EVENT_CONN_ACK = event.Event('conn_ack')
#     __EVENT_TIMEOUT = event.Event('timeout')
#     __EVENT_QUIT_REQ = event.Event('quit_req')

#     # for backward comaptibility
#     CONNECTED_EVENT = EVENT_CONNECTED
#     WIFI_EVENT = EVENT_WIFI
#     LIGHT_EVENT = EVENT_LIGHT
#     FLIGHT_EVENT = EVENT_FLIGHT_DATA
#     LOG_EVENT = EVENT_LOG
#     TIME_EVENT = EVENT_TIME
#     VIDEO_FRAME_EVENT = EVENT_VIDEO_FRAME

#     STATE_DISCONNECTED = state.State('disconnected')
#     STATE_CONNECTING = state.State('connecting')
#     STATE_CONNECTED = state.State('connected')
#     STATE_QUIT = state.State('quit')

#     LOG_ERROR = logger.LOG_ERROR
#     LOG_WARN = logger.LOG_WARN
#     LOG_INFO = logger.LOG_INFO
#     LOG_DEBUG = logger.LOG_DEBUG
#     LOG_ALL = logger.LOG_ALL

#     def __init__(self, port=9000):
#         self.tello_addr = ('192.168.10.1', 8889)
#         self.debug = False
#         self.pkt_seq_num = 0x01e4
#         self.port = port
#         self.udpsize = 2000
#         self.left_x = 0.0
#         self.left_y = 0.0
#         self.right_x = 0.0
#         self.right_y = 0.0
#         self.sock = None
#         self.state = self.STATE_DISCONNECTED
#         self.lock = threading.Lock()
#         self.connected = threading.Event()
#         self.video_enabled = False
#         self.prev_video_data_time = None
#         self.video_data_size = 0
#         self.video_data_loss = 0
#         self.log = log
#         self.exposure = 0
#         self.video_encoder_rate = 4
#         self.video_stream = None
#         self.wifi_strength = 0
#         self.log_data = LogData(log)
#         self.log_data_file = None
#         self.log_data_header_recorded = False
#         self.ready= False

#         # video zoom state
#         self.zoom = False

#         # File recieve state.
#         self.file_recv = {}  # Map filenum -> protocol.DownloadedFile

#         # Create a UDP socket
#         self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#         self.sock.bind(('', self.port))
#         self.sock.settimeout(2.0)

#         dispatcher.connect(self.__state_machine, dispatcher.signal.All)
#         threading.Thread(target=self.__recv_thread).start()
#         threading.Thread(target=self.__video_thread).start()

#     def set_loglevel(self, level):
#         """
#         Set_loglevel controls the output messages. Valid levels are
#         LOG_ERROR, LOG_WARN, LOG_INFO, LOG_DEBUG and LOG_ALL.
#         """
#         log.set_level(level)

#     def get_video_stream(self):
#         """
#         Get_video_stream is used to prepare buffer object which receive video data from the drone.
#         """
#         newly_created = False
#         self.lock.acquire()
#         log.info('get video stream')
#         try:
#             if self.video_stream is None:
#                 self.video_stream = video_stream.VideoStream(self)
#                 newly_created = True
#             res = self.video_stream
#         finally:
#             self.lock.release()
#         # if newly_created:
#         #     self.__send_exposure()
#         #     self.__send_video_encoder_rate()
#         #     self.start_video()

#         return res

#     def connect(self):
#         """Connect is used to send the initial connection request to the drone."""
#         self.__publish(event=self.__EVENT_CONN_REQ)

#     def wait_for_connection(self, timeout=None):
#         """Wait_for_connection will block until the connection is established."""
#         if not self.connected.wait(timeout):
#             raise error.TelloError('timeout')

#     def __send_conn_req(self):
#         port = 9617
#         port0 = (int(port/1000) % 10) << 4 | (int(port/100) % 10)
#         port1 = (int(port/10) % 10) << 4 | (int(port/1) % 10)
#         buf = 'conn_req:%c%c' % (chr(port0), chr(port1))
#         log.info('send connection request (cmd="%s%02x%02x")' % (str(buf[:-2]), port0, port1))
#         return self.send_packet(Packet(buf))

#     def subscribe(self, signal, handler):
#         """Subscribe a event such as EVENT_CONNECTED, EVENT_FLIGHT_DATA, EVENT_VIDEO_FRAME and so on."""
#         dispatcher.connect(handler, signal)

#     def __publish(self, event, data=None, **args):
#         args.update({'data': data})
#         if 'signal' in args:
#             del args['signal']
#         if 'sender' in args:
#             del args['sender']
#         log.debug('publish signal=%s, args=%s' % (event, args))
#         dispatcher.send(event, sender=self, **args)

#     def takeoff(self):
#         """Takeoff tells the drones to liftoff and start flying."""
#         log.info('set altitude limit 30m')
#         pkt = Packet(SET_ALT_LIMIT_CMD)
#         pkt.add_byte(0x1e)  # 30m
#         pkt.add_byte(0x00)
#         self.send_packet(pkt)
#         log.info('takeoff (cmd=0x%02x seq=0x%04x)' % (TAKEOFF_CMD, self.pkt_seq_num))
#         pkt = Packet(TAKEOFF_CMD)
#         pkt.fixup()
#         return self.send_packet(pkt)

#     def land(self):
#         """Land tells the drone to come in for landing."""
#         log.info('land (cmd=0x%02x seq=0x%04x)' % (LAND_CMD, self.pkt_seq_num))
#         pkt = Packet(LAND_CMD)
#         pkt.add_byte(0x00)
#         pkt.fixup()
#         return self.send_packet(pkt)

#     def palm_land(self):
#         """Tells the drone to wait for a hand underneath it and then land."""
#         log.info('palmland (cmd=0x%02x seq=0x%04x)' % (PALM_LAND_CMD, self.pkt_seq_num))
#         pkt = Packet(PALM_LAND_CMD)
#         pkt.add_byte(0x00)
#         pkt.fixup()
#         return self.send_packet(pkt)

#     def quit(self):
#         """Quit stops the internal threads."""
#         log.info('quit')
#         self.__publish(event=self.__EVENT_QUIT_REQ)

#     def __send_time_command(self):
#         log.info('send_time (cmd=0x%02x seq=0x%04x)' % (TIME_CMD, self.pkt_seq_num))
#         pkt = Packet(TIME_CMD, 0x50)
#         pkt.add_byte(0)
#         pkt.add_time()
#         pkt.fixup()
#         return self.send_packet(pkt)

#     def __send_start_video(self):
#         pkt = Packet(VIDEO_START_CMD, 0x60)
#         pkt.fixup()
#         return self.send_packet(pkt)

#     def __send_video_mode(self, mode):
#         pkt = Packet(VIDEO_MODE_CMD)
#         pkt.add_byte(mode)
#         pkt.fixup()
#         return self.send_packet(pkt)

#     def set_video_mode(self, zoom=False):
#         """Tell the drone whether to capture 960x720 4:3 video, or 1280x720 16:9 zoomed video.
#         4:3 has a wider field of view (both vertically and horizontally), 16:9 is crisper."""
#         log.info('set video mode zoom=%s (cmd=0x%02x seq=0x%04x)' % (
#             zoom, VIDEO_START_CMD, self.pkt_seq_num))
#         self.zoom = zoom
#         return self.__send_video_mode(int(zoom))

#     def start_video(self):
#         """Start_video tells the drone to send start info (SPS/PPS) for video stream."""
#         log.info('start video (cmd=0x%02x seq=0x%04x)' % (VIDEO_START_CMD, self.pkt_seq_num))
#         self.video_enabled = True
#         self.__send_exposure()
#         self.__send_video_encoder_rate()
#         return self.__send_start_video()

#     def set_exposure(self, level):
#         """Set_exposure sets the drone camera exposure level. Valid levels are 0, 1, and 2."""
#         if level < 0 or 2 < level:
#             raise error.TelloError('Invalid exposure level')
#         log.info('set exposure (cmd=0x%02x seq=0x%04x)' % (EXPOSURE_CMD, self.pkt_seq_num))
#         self.exposure = level
#         return self.__send_exposure()

#     def __send_exposure(self):
#         pkt = Packet(EXPOSURE_CMD, 0x48)
#         pkt.add_byte(self.exposure)
#         pkt.fixup()
#         return self.send_packet(pkt)

#     def set_video_encoder_rate(self, rate):
#         """Set_video_encoder_rate sets the drone video encoder rate."""
#         log.info('set video encoder rate (cmd=0x%02x seq=%04x)' %
#                  (VIDEO_ENCODER_RATE_CMD, self.pkt_seq_num))
#         self.video_encoder_rate = rate
#         return self.__send_video_encoder_rate()

#     def __send_video_encoder_rate(self):
#         pkt = Packet(VIDEO_ENCODER_RATE_CMD, 0x68)
#         pkt.add_byte(self.video_encoder_rate)
#         pkt.fixup()
#         return self.send_packet(pkt)

#     def take_picture(self):
#         log.info('take picture')
#         return self.send_packet_data(TAKE_PICTURE_COMMAND, type=0x68)


# ############     DRONE CUSTOM COMMANDS    ##############

#     def custom_command(self,cmd,param=None):
#         """Send a custom command to the drone."""
#         self.ready = False
#         if param :
#             pkt = Packet(cmd + ' ' + param)
#             log.info('Custom command sent : {} {}'.format(cmd,param))
#         else:
#             pkt = Packet(cmd)
#             log.info('Custom command sent   : {}'.format(cmd,param))
#         pkt.fixup()
#         return self.send_packet(pkt)
# # 
#     def forward_d(self,distance): # in meters
#         distance = int(distance * 100)
#         msg = "forward " + str(distance)
#         print(msg)
#         return self.custom_command(msg)
# # 
#     def backward_d(self,distance): # in meters
#         distance = int(distance * 100)
#         msg = "back " + str(distance)
#         print(msg)
#         return self.custom_command(msg)
# # 
#     def turn(self,angle): # in degrees
#         angle = int(angle)
#         if angle > 0:
#             msg = "cw " + str(angle)
#             return self.custom_command(msg)
#         else :
#             msg = "ccw " + str(abs(angle))
#             return self.custom_command(msg)
# # 
#     def up_d(self,distance): # in meter
#         distance = int(distance * 100)
#         msg = "up " + str(distance)
#         return self.custom_command(msg)
# # 
#     def down_d(self,distance): # in meter
#         distance = int(distance * 100)
#         msg = "up " + str(distance)
#         return self.custom_command(msg)
# # 
#     def left_d(self,distance): # in meter
#         distance = int(distance * 100)
#         msg = "left " + str(distance)
#         return self.custom_command(msg)
# # 
#     def right_d(self,distance): # in meter
#         distance = int(distance * 100)
#         msg = "right " + str(distance)
#         return self.custom_command(msg)


#     def up(self, val):
#         """Up tells the drone to ascend. Pass in an int from 0-100."""
#         log.info('up(val=%d)' % val)
#         self.left_y = val / 100.0

#     def down(self, val):
#         """Down tells the drone to descend. Pass in an int from 0-100."""
#         log.info('down(val=%d)' % val)
#         self.left_y = val / 100.0 * -1

#     def forward(self, val):
#         """Forward tells the drone to go forward. Pass in an int from 0-100."""
#         log.info('forward(val=%d)' % val)
#         self.right_y = val / 100.0

#     def backward(self, val):
#         """Backward tells the drone to go in reverse. Pass in an int from 0-100."""
#         log.info('backward(val=%d)' % val)
#         self.right_y = val / 100.0 * -1

#     def right(self, val):
#         """Right tells the drone to go right. Pass in an int from 0-100."""
#         log.info('right(val=%d)' % val)
#         self.right_x = val / 100.0

#     def left(self, val):
#         """Left tells the drone to go left. Pass in an int from 0-100."""
#         log.info('left(val=%d)' % val)
#         self.right_x = val / 100.0 * -1

#     def clockwise(self, val):
#         """
#         Clockwise tells the drone to rotate in a clockwise direction.
#         Pass in an int from 0-100.
#         """
#         log.info('clockwise(val=%d)' % val)
#         self.left_x = val / 100.0

#     def counter_clockwise(self, val):
#         """
#         CounterClockwise tells the drone to rotate in a counter-clockwise direction.
#         Pass in an int from 0-100.
#         """
#         log.info('counter_clockwise(val=%d)' % val)
#         self.left_x = val / 100.0 * -1

#     # def flip_forward(self):
#     #     """flip_forward tells the drone to perform a forwards flip"""
#     #     log.info('flip_forward (cmd=0x%02x seq=0x%04x)' % (FLIP_CMD, self.pkt_seq_num))
#     #     pkt = Packet(FLIP_CMD, 0x70)
#     #     pkt.add_byte(FlipFront)
#     #     pkt.fixup()
#     #     return self.send_packet(pkt)

#     def flip_back(self):
#         """flip_back tells the drone to perform a backwards flip"""
#         log.info('flip_back (cmd=0x%02x seq=0x%04x)' % (FLIP_CMD, self.pkt_seq_num))
#         pkt = Packet(FLIP_CMD, 0x70)
#         pkt.add_byte(FlipBack)
#         pkt.fixup()
#         return self.send_packet(pkt)

#     # def flip_right(self):
#     #     """flip_right tells the drone to perform a right flip"""
#     #     log.info('flip_right (cmd=0x%02x seq=0x%04x)' % (FLIP_CMD, self.pkt_seq_num))
#     #     pkt = Packet(FLIP_CMD, 0x70)
#     #     pkt.add_byte(FlipRight)
#     #     pkt.fixup()
#     #     return self.send_packet(pkt)

#     # def flip_left(self):
#     #     """flip_left tells the drone to perform a left flip"""
#     #     log.info('flip_left (cmd=0x%02x seq=0x%04x)' % (FLIP_CMD, self.pkt_seq_num))
#     #     pkt = Packet(FLIP_CMD, 0x70)
#     #     pkt.add_byte(FlipLeft)
#     #     pkt.fixup()
#     #     return self.send_packet(pkt)

#     # def flip_forwardleft(self):
#     #     """flip_forwardleft tells the drone to perform a forwards left flip"""
#     #     log.info('flip_forwardleft (cmd=0x%02x seq=0x%04x)' % (FLIP_CMD, self.pkt_seq_num))
#     #     pkt = Packet(FLIP_CMD, 0x70)
#     #     pkt.add_byte(FlipForwardLeft)
#     #     pkt.fixup()
#     #     return self.send_packet(pkt)

#     # def flip_backleft(self):
#     #     """flip_backleft tells the drone to perform a backwards left flip"""
#     #     log.info('flip_backleft (cmd=0x%02x seq=0x%04x)' % (FLIP_CMD, self.pkt_seq_num))
#     #     pkt = Packet(FLIP_CMD, 0x70)
#     #     pkt.add_byte(FlipBackLeft)
#     #     pkt.fixup()
#     #     return self.send_packet(pkt)

#     # def flip_forwardright(self):
#     #     """flip_forwardright tells the drone to perform a forwards right flip"""
#     #     log.info('flip_forwardright (cmd=0x%02x seq=0x%04x)' % (FLIP_CMD, self.pkt_seq_num))
#     #     pkt = Packet(FLIP_CMD, 0x70)
#     #     pkt.add_byte(FlipForwardRight)
#     #     pkt.fixup()
#     #     return self.send_packet(pkt)

#     # def flip_backright(self):
#     #     """flip_backleft tells the drone to perform a backwards right flip"""
#     #     log.info('flip_backright (cmd=0x%02x seq=0x%04x)' % (FLIP_CMD, self.pkt_seq_num))
#     #     pkt = Packet(FLIP_CMD, 0x70)
#     #     pkt.add_byte(FlipBackRight)
#     #     pkt.fixup()
#     #     return self.send_packet(pkt)

#     def __fix_range(self, val, min=-1.0, max=1.0):
#         if val < min:
#             val = min
#         elif val > max:
#             val = max
#         return val

#     def set_throttle(self, throttle):
#         """
#         Set_throttle controls the vertical up and down motion of the drone.
#         Pass in an int from -1.0 ~ 1.0. (positive value means upward)
#         """
#         if self.left_y != self.__fix_range(throttle):
#             log.info('set_throttle(val=%4.2f)' % throttle)
#         self.left_y = self.__fix_range(throttle)

#     def set_yaw(self, yaw):
#         """
#         Set_yaw controls the left and right rotation of the drone.
#         Pass in an int from -1.0 ~ 1.0. (positive value will make the drone turn to the right)
#         """
#         if self.left_x != self.__fix_range(yaw):
#             log.info('set_yaw(val=%4.2f)' % yaw)
#         self.left_x = self.__fix_range(yaw)

#     def set_pitch(self, pitch):
#         """
#         Set_pitch controls the forward and backward tilt of the drone.
#         Pass in an int from -1.0 ~ 1.0. (positive value will make the drone move forward)
#         """
#         if self.right_y != self.__fix_range(pitch):
#             log.info('set_pitch(val=%4.2f)' % pitch)
#         self.right_y = self.__fix_range(pitch)

#     def set_roll(self, roll):
#         """
#         Set_roll controls the the side to side tilt of the drone.
#         Pass in an int from -1.0 ~ 1.0. (positive value will make the drone move to the right)
#         """
#         if self.right_x != self.__fix_range(roll):
#             log.info('set_roll(val=%4.2f)' % roll)
#         self.right_x = self.__fix_range(roll)

#     def __send_stick_command(self):
#         pkt = Packet(STICK_CMD, 0x60)

#         axis1 = int(1024 + 660.0 * self.right_x) & 0x7ff
#         axis2 = int(1024 + 660.0 * self.right_y) & 0x7ff
#         axis3 = int(1024 + 660.0 * self.left_y) & 0x7ff
#         axis4 = int(1024 + 660.0 * self.left_x) & 0x7ff
#         '''
#         11 bits (-1024 ~ +1023) x 4 axis = 44 bits
#         44 bits will be packed in to 6 bytes (48 bits)
#                     axis4      axis3      axis2      axis1
#              |          |          |          |          |
#                  4         3         2         1         0
#         98765432109876543210987654321098765432109876543210
#          |       |       |       |       |       |       |
#              byte5   byte4   byte3   byte2   byte1   byte0
#         '''
#         log.debug("stick command: yaw=%4d thr=%4d pit=%4d rol=%4d" %
#                   (axis4, axis3, axis2, axis1))
#         log.debug("stick command: yaw=%04x thr=%04x pit=%04x rol=%04x" %
#                   (axis4, axis3, axis2, axis1))
#         pkt.add_byte(((axis2 << 11 | axis1) >> 0) & 0xff)
#         pkt.add_byte(((axis2 << 11 | axis1) >> 8) & 0xff)
#         pkt.add_byte(((axis3 << 11 | axis2) >> 5) & 0xff)
#         pkt.add_byte(((axis4 << 11 | axis3) >> 2) & 0xff)
#         pkt.add_byte(((axis4 << 11 | axis3) >> 10) & 0xff)
#         pkt.add_byte(((axis4 << 11 | axis3) >> 18) & 0xff)
#         pkt.add_time()
#         pkt.fixup()
#         log.debug("stick command: %s" % byte_to_hexstring(pkt.get_buffer()))
#         return self.send_packet(pkt)

#     def __send_ack_log(self, id):
#         pkt = Packet(LOG_HEADER_MSG, 0x50)
#         pkt.add_byte(0x00)
#         b0, b1 = le16(id)
#         pkt.add_byte(b0)
#         pkt.add_byte(b1)
#         pkt.fixup()
#         return self.send_packet(pkt)

#     def send_packet(self, pkt):
#         """Send_packet is used to send a command packet to the drone."""
#         try:
#             cmd = pkt.get_buffer()
#             self.sock.sendto(cmd, self.tello_addr)
#             log.debug("send_packet: %s" % byte_to_hexstring(cmd))
#         except socket.error as err:
#             if self.state == self.STATE_CONNECTED:
#                 log.error("send_packet: %s" % str(err))
#             else:
#                 log.info("send_packet: %s" % str(err))
#             return False

#         return True

#     def send_packet_data(self, command, type=0x68, payload=[]):
#         pkt = Packet(command, type, payload)
#         pkt.fixup()
#         return self.send_packet(pkt)

#     def __process_packet(self, data):
#         if isinstance(data, str):
#             data = bytearray([x for x in data])

#         if str(data[0:9]) == 'conn_ack:' or data[0:9] == b'conn_ack:':
#             log.info('connected. (port=%2x%2x)' % (data[9], data[10]))
#             log.debug('    %s' % byte_to_hexstring(data))
#             # if self.video_enabled:
#             #     self.__send_exposure()
#             #     self.__send_video_encoder_rate()
#             #     self.__send_start_video()
#             self.__publish(self.__EVENT_CONN_ACK, data)

#             return True

#         if data[0] != START_OF_PACKET:
#             log.info('start of packet != %02x (%02x) (ignored)' % (START_OF_PACKET, data[0]))
#             log.info('    %s' % byte_to_hexstring(data))
#             log.info('    %s' % str(map(chr, data))[1:-1])
#             print(data)
#             if data == "OK":
#                 self.ready = True
#             return False

#         pkt = Packet(data)
#         cmd = uint16(data[5], data[6])

#         if cmd == LOG_HEADER_MSG:
#             id = uint16(data[9], data[10])
#             log.info("recv: log_header: id=%04x, '%s'" % (id, str(data[28:54])))
#             log.debug("recv: log_header: %s" % byte_to_hexstring(data[9:]))
#             self.__send_ack_log(id)
#             self.__publish(event=self.EVENT_LOG_HEADER, data=data[9:])
#             if self.log_data_file and not self.log_data_header_recorded:
#                 self.log_data_file.write(data[12:-2])
#                 self.log_data_header_recorded = True
#         elif cmd == LOG_DATA_MSG:
#             log.debug("recv: log_data: length=%d, %s" % (len(data[9:]), byte_to_hexstring(data[9:])))
#             self.__publish(event=self.EVENT_LOG_RAWDATA, data=data[9:])
#             try:
#                 self.log_data.update(data[10:])
#                 if self.log_data_file:
#                     self.log_data_file.write(data[10:-2])
#             except Exception as ex:
#                 print("--------------------------------------------")
#                 log.error('%s' % str(ex))
#             self.__publish(event=self.EVENT_LOG_DATA, data=self.log_data)

#         elif cmd == LOG_CONFIG_MSG:
#             log.debug("recv: log_config: length=%d, %s" % (len(data[9:]), byte_to_hexstring(data[9:])))
#             self.__publish(event=self.EVENT_LOG_CONFIG, data=data[9:])
#         elif cmd == WIFI_MSG:
#             log.debug("recv: wifi: %s" % byte_to_hexstring(data[9:]))
#             self.wifi_strength = data[9]
#             self.__publish(event=self.EVENT_WIFI, data=data[9:])
#         elif cmd == LIGHT_MSG:
#             log.debug("recv: light: %s" % byte_to_hexstring(data[9:]))
#             self.__publish(event=self.EVENT_LIGHT, data=data[9:])
#         elif cmd == FLIGHT_MSG:
#             flight_data = FlightData(data[9:])
#             flight_data.wifi_strength = self.wifi_strength
#             log.debug("recv: flight data: %s" % str(flight_data))
#             self.__publish(event=self.EVENT_FLIGHT_DATA, data=flight_data)
#         elif cmd == TIME_CMD:
#             log.debug("recv: time data: %s" % byte_to_hexstring(data))
#             self.__publish(event=self.EVENT_TIME, data=data[7:9])
#         elif cmd in (TAKEOFF_CMD, LAND_CMD, VIDEO_START_CMD, VIDEO_ENCODER_RATE_CMD, PALM_LAND_CMD,
#                      EXPOSURE_CMD):
#             log.info("recv: ack: cmd=0x%02x seq=0x%04x %s" %
#                      (uint16(data[5], data[6]), uint16(data[7], data[8]), byte_to_hexstring(data)))
#         elif cmd == TELLO_CMD_FILE_SIZE:
#             # Drone is about to send us a file. Get ready.
#             # N.b. one of the fields in the packet is a file ID; by demuxing
#             # based on file ID we can receive multiple files at once. This
#             # code doesn't support that yet, though, so don't take one photo
#             # while another is still being received.
#             log.info("recv: file size: %s" % byte_to_hexstring(data))
#             if len(pkt.get_data()) >= 7:
#                 (size, filenum) = struct.unpack('<xLH', pkt.get_data())
#                 log.info('      file size: num=%d bytes=%d' % (filenum, size))
#                 # Initialize file download state.
#                 self.file_recv[filenum] = DownloadedFile(filenum, size)
#             else:
#                 # We always seem to get two files, one with most of the payload missing.
#                 # Not sure what the second one is for.
#                 log.warn('      file size: payload too small: %s' % byte_to_hexstring(pkt.get_data()))
#             # Ack the packet.
#             self.send_packet(pkt)
#         elif cmd == TELLO_CMD_FILE_DATA:
#             # log.info("recv: file data: %s" % byte_to_hexstring(data[9:21]))
#             # Drone is sending us a fragment of a file it told us to prepare
#             # for earlier.
#             self.recv_file_data(pkt.get_data())
#         else:
#             log.info('unknown packet: %04x %s' % (cmd, byte_to_hexstring(data)))
#             return False

#         return True

#     def recv_file_data(self, data):
#         (filenum,chunk,fragment,size) = struct.unpack('<HLLH', data[0:12])
#         file = self.file_recv.get(filenum, None)

#         # Preconditions.
#         if file is None:
#             return

#         if file.recvFragment(chunk, fragment, size, data[12:12+size]):
#             # Did this complete a chunk? Ack the chunk so the drone won't
#             # re-send it.
#             self.send_packet_data(TELLO_CMD_FILE_DATA, type=0x50,
#                 payload=struct.pack('<BHL', 0, filenum, chunk))

#         if file.done():
#             # We have the whole file! First, send a normal ack with the first
#             # byte set to 1 to indicate file completion.
#             self.send_packet_data(TELLO_CMD_FILE_DATA, type=0x50,
#                 payload=struct.pack('<BHL', 1, filenum, chunk))
#             # Then send the FILE_COMPLETE packed separately telling it how
#             # large we thought the file was.
#             self.send_packet_data(TELLO_CMD_FILE_COMPLETE, type=0x48,
#                 payload=struct.pack('<HL', filenum, file.size))
#             # Inform subscribers that we have a file and clean up.
#             self.__publish(event=self.EVENT_FILE_RECEIVED, data=file.data())
#             del self.file_recv[filenum]

#     def record_log_data(self, path = None):
#         if path == None:
#             path = '%s/Documents/tello-%s.dat' % (
#                 os.getenv('HOME'),
#                 datetime.datetime.now().strftime('%Y-%m-%d_%H%M%S'))
#         log.info('record log data in %s' % path)
#         self.log_data_file = open(path, 'wb')

#     def __state_machine(self, event, sender, data, **args):
#         self.lock.acquire()
#         cur_state = self.state
#         event_connected = False
#         event_disconnected = False
#         log.debug('event %s in state %s' % (str(event), str(self.state)))

#         if self.state == self.STATE_DISCONNECTED:
#             if event == self.__EVENT_CONN_REQ:
#                 self.__send_conn_req()
#                 self.state = self.STATE_CONNECTING
#             elif event == self.__EVENT_QUIT_REQ:
#                 self.state = self.STATE_QUIT
#                 event_disconnected = True
#                 self.video_enabled = False

#         elif self.state == self.STATE_CONNECTING:
#             if event == self.__EVENT_CONN_ACK:
#                 self.state = self.STATE_CONNECTED
#                 event_connected = True
#                 # send time
#                 self.__send_time_command()
#             elif event == self.__EVENT_TIMEOUT:
#                 self.__send_conn_req()
#             elif event == self.__EVENT_QUIT_REQ:
#                 self.state = self.STATE_QUIT

#         elif self.state == self.STATE_CONNECTED:
#             if event == self.__EVENT_TIMEOUT:
#                 self.__send_conn_req()
#                 self.state = self.STATE_CONNECTING
#                 event_disconnected = True
#                 self.video_enabled = False
#             elif event == self.__EVENT_QUIT_REQ:
#                 self.state = self.STATE_QUIT
#                 event_disconnected = True
#                 self.video_enabled = False

#         elif self.state == self.STATE_QUIT:
#             pass

#         if cur_state != self.state:
#             log.info('state transit %s -> %s' % (cur_state, self.state))
#         self.lock.release()

#         if event_connected:
#             self.__publish(event=self.EVENT_CONNECTED, **args)
#             self.connected.set()
#         if event_disconnected:
#             self.__publish(event=self.EVENT_DISCONNECTED, **args)
#             self.connected.clear()

#     def __recv_thread(self):
#         sock = self.sock

#         while self.state != self.STATE_QUIT:

#             if self.state == self.STATE_CONNECTED:
#                 self.__send_stick_command()  # ignore errors

#             try:
#                 data, server = sock.recvfrom(self.udpsize)
#                 log.debug("recv: %s" % byte_to_hexstring(data))
#                 self.__process_packet(data)
#             except socket.timeout as ex:
#                 if self.state == self.STATE_CONNECTED:
#                     log.error('recv: timeout')
#                 self.__publish(event=self.__EVENT_TIMEOUT)
#             except Exception as ex:
#                 log.error('recv: %s' % str(ex))
#                 show_exception(ex)

#         log.info('exit from the recv thread.')

#     def __video_thread(self):
#         log.info('start video thread')
#         # Create a UDP socket
#         sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#         port = 6038
#         sock.bind(('', port))
#         sock.settimeout(5.0)
#         sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 512 * 1024)
#         log.info('video receive buffer size = %d' %
#                  sock.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF))

#         prev_video_data = None
#         prev_ts = None
#         history = []
#         while self.state != self.STATE_QUIT:
#             if not self.video_enabled:
#                 time.sleep(1.0)
#                 continue
#             try:
#                 data, server = sock.recvfrom(self.udpsize)
#                 now = datetime.datetime.now()
#                 log.debug("video recv: %s %d bytes" % (byte_to_hexstring(data[0:2]), len(data)))
#                 show_history = False

#                 # check video data loss
#                 video_data = VideoData(data)
#                 loss = video_data.gap(prev_video_data)
#                 if loss != 0:
#                     self.video_data_loss += loss
#                     # enable this line to see packet history
#                     # show_history = True
#                 prev_video_data = video_data

#                 # check video data interval
#                 if prev_ts is not None and 0.1 < (now - prev_ts).total_seconds():
#                     log.info('video recv: %d bytes %02x%02x +%03d' %
#                              (len(data), byte(data[0]), byte(data[1]),
#                               (now - prev_ts).total_seconds() * 1000))
#                 prev_ts = now

#                 # save video data history
#                 history.append([now, len(data), byte(data[0])*256 + byte(data[1])])
#                 if 100 < len(history):
#                     history = history[1:]

#                 # show video data history
#                 if show_history:
#                     prev_ts = history[0][0]
#                     for i in range(1, len(history)):
#                         [ ts, sz, sn ] = history[i]
#                         print('    %02d:%02d:%02d.%03d %4d bytes %04x +%03d%s' %
#                               (ts.hour, ts.minute, ts.second, ts.microsecond/1000,
#                                sz, sn, (ts - prev_ts).total_seconds()*1000,
#                                (' *' if i == len(history) - 1 else '')))
#                         prev_ts = ts
#                     history = history[-1:]

#                 # deliver video frame to subscribers
#                 self.__publish(event=self.EVENT_VIDEO_FRAME, data=data[2:])
#                 self.__publish(event=self.EVENT_VIDEO_DATA, data=data)

#                 # show video frame statistics
#                 if self.prev_video_data_time is None:
#                     self.prev_video_data_time = now
#                 self.video_data_size += len(data)
#                 dur = (now - self.prev_video_data_time).total_seconds()
#                 if 2.0 < dur:
#                     log.info(('video data %d bytes %5.1fKB/sec' %
#                               (self.video_data_size, self.video_data_size / dur / 1024)) +
#                              ((' loss=%d' % self.video_data_loss) if self.video_data_loss != 0 else ''))
#                     self.video_data_size = 0
#                     self.prev_video_data_time = now
#                     self.video_data_loss = 0

#                     # # keep sending start video command
#                     # self.__send_start_video()

#             except socket.timeout as ex:
#                 log.error('video recv: timeout')
#                 print("coin")
#                 # self.start_video()
#                 data = None
#             except Exception as ex:
#                 log.error('video recv: %s' % str(ex))
#                 show_exception(ex)

#         log.info('exit from the video thread.')

# if __name__ == '__main__':
#     print('You can use test.py for testing.')



# coding=utf-8
import socket
import time
import threading
import cv2
from threading import Thread
from djitellopy.decorators import accepts


class Tello:
    """Python wrapper to interact with the Ryze Tello drone using the official Tello api.
    Tello API documentation:
    https://dl-cdn.ryzerobotics.com/downloads/tello/20180910/Tello%20SDK%20Documentation%20EN_1.3.pdf
    """
    # Send and receive commands, client socket
    UDP_IP = '192.168.10.1'
    UDP_PORT = 8889
    RESPONSE_TIMEOUT = 0.5  # in seconds
    TIME_BTW_COMMANDS = 0.5  # in seconds
    TIME_BTW_RC_CONTROL_COMMANDS = 0.5  # in seconds
    last_received_command = time.time()

    # Video stream, server socket
    VS_UDP_IP = '0.0.0.0'
    VS_UDP_PORT = 11111

    # VideoCapture object
    cap = None
    background_frame_read = None

    stream_on = False

    def __init__(self):
        # To send comments
        self.address = (self.UDP_IP, self.UDP_PORT)
        self.clientSocket = socket.socket(socket.AF_INET,  # Internet
                                          socket.SOCK_DGRAM)  # UDP
        self.clientSocket.bind(('', self.UDP_PORT))  # For UDP response (receiving data)
        self.response = None
        self.stream_on = False

        # Run tello udp receiver on background
        thread = threading.Thread(target=self.run_udp_receiver, args=())
        thread.daemon = True
        thread.start()

    def run_udp_receiver(self):
        """Setup drone UDP receiver. This method listens for responses of Tello. Must be run from a background thread
        in order to not block the main thread."""
        while True:
            try:
                self.response, _ = self.clientSocket.recvfrom(1024)  # buffer size is 1024 bytes
            except Exception as e:
                print(e)
                break

    def get_udp_video_address(self):
        return 'udp://@' + self.VS_UDP_IP + ':' + str(self.VS_UDP_PORT)  # + '?overrun_nonfatal=1&fifo_size=5000'

    def get_video_capture(self):
        """Get the VideoCapture object from the camera drone
        Returns:
            VideoCapture
        """

        if self.cap is None:
            self.cap = cv2.VideoCapture(self.get_udp_video_address())

        if not self.cap.isOpened():
            self.cap.open(self.get_udp_video_address())

        return self.cap

    def get_frame_read(self):
        """Get the BackgroundFrameRead object from the camera drone. Then, you just need to call
        backgroundFrameRead.frame to get the actual frame received by the drone.
        Returns:
            BackgroundFrameRead
        """
        if self.background_frame_read is None:
            self.background_frame_read = BackgroundFrameRead(self, self.get_udp_video_address()).start()
        return self.background_frame_read

    def stop_video_capture(self):
        return self.streamoff()

    @accepts(command=str)
    def send_command_with_return(self, command):
        """Send command to Tello and wait for its response.
        Return:
            bool: True for successful, False for unsuccessful
        """
        # Commands very consecutive makes the drone not respond to them. So wait at least self.TIME_BTW_COMMANDS seconds
        diff = time.time() * 1000 - self.last_received_command
        if diff < self.TIME_BTW_COMMANDS:
            time.sleep(diff)

        print('Send command: ' + command)
        timestamp = int(time.time() * 1000)

        self.clientSocket.sendto(command.encode('utf-8'), self.address)

        while self.response is None:
            if (time.time() * 1000) - timestamp > self.RESPONSE_TIMEOUT * 1000:
                print('Timeout exceed on command ' + command)
                return False

        print('Response: ' + str(self.response))

        response = self.response.decode('utf-8')

        self.response = None

        self.last_received_command = time.time() * 1000

        return response

    @accepts(command=str)
    def send_command_without_return(self, command):
        """Send command to Tello without expecting a response. Use this method when you want to send a command
        continuously
            - go x y z speed: Tello fly to x y z in speed (cm/s)
                x: 20-500
                y: 20-500
                z: 20-500
                speed: 10-100
            - curve x1 y1 z1 x2 y2 z2 speed: Tello fly a curve defined by the current and two given coordinates with
                speed (cm/s). If the arc radius is not within the range of 0.5-10 meters, it responses false.
                x/y/z can’t be between -20 – 20 at the same time .
                x1, x2: 20-500
                y1, y2: 20-500
                z1, z2: 20-500
                speed: 10-60
            - rc a b c d: Send RC control via four channels.
                a: left/right (-100~100)
                b: forward/backward (-100~100)
                c: up/down (-100~100)
                d: yaw (-100~100)
        """
        # Commands very consecutive makes the drone not respond to them. So wait at least self.TIME_BTW_COMMANDS seconds

        print('Send command (no expect response): ' + command)
        self.clientSocket.sendto(command.encode('utf-8'), self.address)

    @accepts(command=str)
    def send_control_command(self, command):
        """Send control command to Tello and wait for its response. Possible control commands:
            - command: entry SDK mode
            - takeoff: Tello auto takeoff
            - land: Tello auto land
            - streamon: Set video stream on
            - streamoff: Set video stream off
            - emergency: Stop all motors immediately
            - up x: Tello fly up with distance x cm. x: 20-500
            - down x: Tello fly down with distance x cm. x: 20-500
            - left x: Tello fly left with distance x cm. x: 20-500
            - right x: Tello fly right with distance x cm. x: 20-500
            - forward x: Tello fly forward with distance x cm. x: 20-500
            - back x: Tello fly back with distance x cm. x: 20-500
            - cw x: Tello rotate x degree clockwise x: 1-3600
            - ccw x: Tello rotate x degree counter- clockwise. x: 1-3600
            - flip x: Tello fly flip x
                l (left)
                r (right)
                f (forward)
                b (back)
            - speed x: set speed to x cm/s. x: 10-100
            - wifi ssid pass: Set Wi-Fi with SSID password
        Return:
            bool: True for successful, False for unsuccessful
        """

        response = self.send_command_with_return(command)

        if response == 'OK' or response == 'ok':
            return True
        else:
            return self.return_error_on_send_command(command, response)

    @accepts(command=str)
    def send_read_command(self, command):
        """Send set command to Tello and wait for its response. Possible set commands:
            - speed?: get current speed (cm/s): x: 1-100
            - battery?: get current battery percentage: x: 0-100
            - time?: get current fly time (s): time
            - height?: get height (cm): x: 0-3000
            - temp?: get temperature (°C): x: 0-90
            - attitude?: get IMU attitude data: pitch roll yaw
            - baro?: get barometer value (m): x
            - tof?: get distance value from TOF (cm): x: 30-1000
            - wifi?: get Wi-Fi SNR: snr
        Return:
            bool: True for successful, False for unsuccessful
        """

        response = self.send_command_with_return(command)

        try:
            response = str(response)
        except TypeError as e:
            print(e)
            pass

        if ('error' not in response) and ('ERROR' not in response) and ('False' not in response):
            if response.isdigit():
                return int(response)
            else:
                return response
        else:
            return self.return_error_on_send_command(command, response)

    @staticmethod
    def return_error_on_send_command(command, response):
        """Returns False and print an informative result code to show unsuccessful response"""
        print('Command ' + command + ' was unsuccessful. Message: ' + str(response))
        return False

    def connect(self):
        """Entry SDK mode
        Returns:
            bool: True for successful, False for unsuccessful
        """
        return self.send_control_command("command")

    def takeoff(self):
        """Tello auto takeoff
        Returns:
            bool: True for successful, False for unsuccessful
            False: Unsuccessful
        """
        return self.send_control_command("takeoff")

    def land(self):
        """Tello auto land
        Returns:
            bool: True for successful, False for unsuccessful
        """
        return self.send_control_command("land")

    def streamon(self):
        """Set video stream on. If the response is 'Unknown command' means you have to update the Tello firmware. That
        can be done through the Tello app.
        Returns:
            bool: True for successful, False for unsuccessful
        """
        result = self.send_control_command("streamon")
        if result is True:
            self.stream_on = True
        return result

    def streamoff(self):
        """Set video stream off
        Returns:
            bool: True for successful, False for unsuccessful
        """
        result = self.send_control_command("streamoff")
        if result is True:
            self.stream_on = False
        return result

    def emergency(self):
        """Stop all motors immediately
        Returns:
            bool: True for successful, False for unsuccessful
        """
        return self.send_control_command("emergency")

    @accepts(direction=str, x=int)
    def move(self, direction, x):
        """Tello fly up, down, left, right, forward or back with distance x cm.
        Arguments:
            direction: up, down, left, right, forward or back
            x: 20-500
        Returns:
            bool: True for successful, False for unsuccessful
        """
        return self.send_control_command(direction + ' ' + str(x))

    @accepts(x=int)
    def move_up(self, x):
        """Tello fly up with distance x cm.
        Arguments:
            x: 20-500
        Returns:
            bool: True for successful, False for unsuccessful
        """
        return self.move("up", x)

    @accepts(x=int)
    def move_down(self, x):
        """Tello fly down with distance x cm.
        Arguments:
            x: 20-500
        Returns:
            bool: True for successful, False for unsuccessful
        """
        return self.move("down", x)

    @accepts(x=int)
    def move_left(self, x):
        """Tello fly left with distance x cm.
        Arguments:
            x: 20-500
        Returns:
            bool: True for successful, False for unsuccessful
        """
        return self.move("left", x)

    @accepts(x=int)
    def move_right(self, x):
        """Tello fly right with distance x cm.
        Arguments:
            x: 20-500
        Returns:
            bool: True for successful, False for unsuccessful
        """
        return self.move("right", x)

    @accepts(x=int)
    def move_forward(self, x):
        """Tello fly forward with distance x cm.
        Arguments:
            x: 20-500
        Returns:
            bool: True for successful, False for unsuccessful
        """
        return self.move("forward", x)

    @accepts(x=int)
    def move_back(self, x):
        """Tello fly back with distance x cm.
        Arguments:
            x: 20-500
        Returns:
            bool: True for successful, False for unsuccessful
        """
        return self.move("back", x)

    @accepts(x=int)
    def move_up(self, x):
        """Tello fly up with distance x cm.
        Arguments:
            x: 20-500
        Returns:
            bool: True for successful, False for unsuccessful
        """
        return self.move("up", x)

    @accepts(x=int)
    def rotate_clockwise(self, x):
        """Tello rotate x degree clockwise.
        Arguments:
            x: 1-360
        Returns:
            bool: True for successful, False for unsuccessful
        """
        return self.send_control_command("cw " + str(x))

    @accepts(x=int)
    def rotate_counter_clockwise(self, x):
        """Tello rotate x degree counter-clockwise.
        Arguments:
            x: 1-3600
        Returns:
            bool: True for successful, False for unsuccessful
        """
        return self.send_control_command("ccw " + str(x))

    @accepts(x=str)
    def flip(self, direction):
        """Tello fly flip.
        Arguments:
            direction: l (left), r (right), f (forward) or b (back)
        Returns:
            bool: True for successful, False for unsuccessful
        """
        return self.send_control_command("flip " + direction)

    def flip_left(self):
        """Tello fly flip left.
        Returns:
            bool: True for successful, False for unsuccessful
        """
        return self.flip("l")

    def flip_right(self):
        """Tello fly flip left.
        Returns:
            bool: True for successful, False for unsuccessful
        """
        return self.flip("r")

    def flip_forward(self):
        """Tello fly flip left.
        Returns:
            bool: True for successful, False for unsuccessful
        """
        return self.flip("f")

    def flip_back(self):
        """Tello fly flip left.
        Returns:
            bool: True for successful, False for unsuccessful
        """
        return self.flip("b")

    @accepts(x=int, y=int, z=int, speed=int)
    def go_xyz_speed(self, x, y, z, speed):
        """Tello fly to x y z in speed (cm/s)
        Arguments:
            x: 20-500
            y: 20-500
            z: 20-500
            speed: 10-100
        Returns:
            bool: True for successful, False for unsuccessful
        """
        return self.send_command_without_return('go %s %s %s %s' % (x, y, z, speed))

    @accepts(x1=int, y1=int, z1=int, x2=int, y2=int, z2=int, speed=int)
    def go_xyz_speed(self, x1, y1, z1, x2, y2, z2, speed):
        """Tello fly a curve defined by the current and two given coordinates with speed (cm/s).
            - If the arc radius is not within the range of 0.5-10 meters, it responses false.
            - x/y/z can’t be between -20 – 20 at the same time.
        Arguments:
            x1: 20-500
            x2: 20-500
            y1: 20-500
            y2: 20-500
            z1: 20-500
            z2: 20-500
            speed: 10-60
        Returns:
            bool: True for successful, False for unsuccessful
        """
        return self.send_command_without_return('curve %s %s %s %s %s %s %s' % (x1, y1, z1, x2, y2, z2, speed))

    @accepts(x=int)
    def set_speed(self, x):
        """Set speed to x cm/s.
        Arguments:
            x: 10-100
        Returns:
            bool: True for successful, False for unsuccessful
        """
        return self.send_control_command("speed " + str(x))

    last_rc_control_sent = 0

    @accepts(left_right_velocity=int, forward_backward_velocity=int, up_down_velocity=int, yaw_velocity=int)
    def send_rc_control(self, left_right_velocity, forward_backward_velocity, up_down_velocity, yaw_velocity):
        """Send RC control via four channels. Command is sent every self.TIME_BTW_RC_CONTROL_COMMANDS seconds.
        Arguments:
            left_right_velocity: -100~100 (left/right)
            forward_backward_velocity: -100~100 (forward/backward)
            up_down_velocity: -100~100 (up/down)
            yaw_velocity: -100~100 (yaw)
        Returns:
            bool: True for successful, False for unsuccessful
        """
        if int(time.time() * 1000) - self.last_rc_control_sent < self.TIME_BTW_RC_CONTROL_COMMANDS:
            pass
        else:
            self.last_rc_control_sent = int(time.time() * 1000)
            return self.send_command_without_return('rc %s %s %s %s' % (left_right_velocity, forward_backward_velocity,
                                                                        up_down_velocity, yaw_velocity))

    def set_wifi_with_ssid_password(self):
        """Set Wi-Fi with SSID password.
        Returns:
            bool: True for successful, False for unsuccessful
        """
        return self.send_control_command('wifi ssid pass')

    def get_speed(self):
        """Get current speed (cm/s)
        Returns:
            False: Unsuccessful
            int: 1-100
        """
        return self.send_read_command('speed?')

    def get_battery(self):
        """Get current battery percentage
        Returns:
            False: Unsuccessful
            int: -100
        """
        return self.send_read_command('battery?')

    def get_flight_time(self):
        """Get current fly time (s)
        Returns:
            False: Unsuccessful
            int: Seconds elapsed during flight.
        """
        return self.send_read_command('time?')

    def get_height(self):
        """Get height (cm)
        Returns:
            False: Unsuccessful
            int: 0-3000
        """
        return self.send_read_command('height?')

    def get_temperature(self):
        """Get temperature (°C)
        Returns:
            False: Unsuccessful
            int: 0-90
        """
        return self.send_read_command('temperature?')

    def get_attitude(self):
        """Get IMU attitude data
        Returns:
            False: Unsuccessful
            int: pitch roll yaw
        """
        return self.send_read_command('attitude?')

    def get_barometer(self):
        """Get barometer value (m)
        Returns:
            False: Unsuccessful
            int: 0-100
        """
        return self.send_read_command('baro?')

    def get_distance_tof(self):
        """Get distance value from TOF (cm)
        Returns:
            False: Unsuccessful
            int: 30-1000
        """
        return self.send_read_command('tof?')

    def get_wifi(self):
        """Get Wi-Fi SNR
        Returns:
            False: Unsuccessful
            str: snr
        """
        return self.send_read_command('wifi?')

    def end(self):
        """Call this method when you want to end the tello object"""
        if self.stream_on:
            self.streamoff()
        if self.background_frame_read is not None:
            self.background_frame_read.stop()
        if self.cap is not None:
            self.cap.release()


class BackgroundFrameRead:
    """
    This class read frames from a VideoCapture in background. Then, just call backgroundFrameRead.frame to get the
    actual one.
    """

    def __init__(self, tello, address):
        tello.cap = cv2.VideoCapture(address)
        self.cap = tello.cap

        if not self.cap.isOpened():
            self.cap.open(address)

        self.grabbed, self.frame = self.cap.read()
        self.stopped = False

    def start(self):
        Thread(target=self.update_frame, args=()).start()
        return self

    def update_frame(self):
        while not self.stopped:
            if not self.grabbed or not self.cap.isOpened():
                self.stop()
            else:
                (self.grabbed, self.frame) = self.cap.read()

    def stop(self):
        self.stopped = True