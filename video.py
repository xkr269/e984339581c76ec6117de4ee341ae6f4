import numpy as np
import cv2
import time
import av

# 'udp://127.0.0.1:6666?timeout=2000'

con_str = "udp://192.168.10.1:11111" #?timeout=2000"
print(con_str)
# cap = cv2.VideoCapture(con_str)
# print("connected")

container = av.open(con_str)

for frame in container.decode(video=0):
    print("frame")


# while(True):
#     # Capture frame-by-frame
#     ret, frame = cap.read()

#     print(ret)
#     print(frame)

#     time.sleep(1)

    # # Our operations on the frame come here
    # gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # # Display the resulting frame
    # cv2.imshow('frame',gray)
    # if cv2.waitKey(1) & 0xFF == ord('q'):
    #     break


    
# #
# # Copyright (c) 2018, Manfred Constapel
# # This file is licensed under the terms of the MIT license.
# #

# """
# Pythonic DJI Ryze Tello Workbench: Example
# Extract one h.264 video frame from a snippet of a captured live stream (stream.log)
# and save the h.264 video frame to an image file (frame.png) using FFmpeg.
#  1. read raw video from log
#  2. pipe raw video data to FFmpeg via stdin
#  3. ffmpeg does the work (decoding and converting)
#  4. FFmpeg pipes output to stdout
#  5. output is going to be collected
#  6. Pillow saves output to an image
 
# """

# import json, time, sys, os
# import numpy as np
# import subprocess as sp
# import PIL.Image as pil

# # ------------------------------------------

# def split(value, size=2):
#     return tuple(value[0 + i:size + i] for i in range(0, len(value), size))


# def hex2dec(value):
#     if type(value) == str:
#         value = value.strip()
#         if ' ' not in value:
#             return int(value, 16)
#         else:
#             return hex2dec(value.split(' '))
#     else:
#         return tuple(int(item, 16) for item in value)


# def dec2hex(value, delim=''):
#     if type(value) == int:
#         s = hex(value)
#         return '0' * (len(s) % 2) + s[2:]     
#     else:       
#         return delim.join(dec2hex(item, delim) for item in value) 

# # ------------------------------------------

# def collect_stream(file):
#     stream = []
#     for line in file:
#         try:
#             obj = json.loads(line)
#             obj = obj[tuple(obj.keys())[0]]
#             sn, fn = obj['802.11']['sn'], obj['802.11']['fn']
#             if ('UDP' in obj and fn == 0 and obj['UDP']['dport'] == 7797) or ('UDP' not in obj and fn > 0 and 'LLC' in obj):
#                 res = ''
#                 if fn > 0:
#                     res += dec2hex(obj['LLC']['dsap'])
#                     res += dec2hex(obj['LLC']['ssap'])
#                     res += dec2hex(obj['LLC']['ctrl'])
#                 if 'Raw' in obj: res += obj['Raw']['load']
#                 if 'Padding' in obj: res += obj['Padding']['load']
#                 stream.append((sn, fn, res))
#         except Exception as e:
#             print(e)
#     return stream

# # ------------------------------------------

# def extract_h264_frame(stream):
#     content = ''
#     start = False    
#     for item in stream:  # TODO: use "fsn" and "ffn" for ordering the chunks and pieces
#         sn, fn, data = item    
#         if fn == 0:
#            head = data[4:14]
#            if head[:8] == '00000001' and head[9] == '7':
#                start = True  
#         if start:           
#             if fn == 0:
#                 fsn, ffn = hex2dec(split(data[0:4]))
#                 content += data[4:-8]  # sn 2 bytes; fcs 4 bytes
#             else:
#                 content += data[:-8]   # fcs 4 bytes
#     return content


# def print_h264_frame(frame):
#     content = split(frame, 32)
#     content = '\n'.join([' '.join(split(item, 2)) for item in content])
#     print(content)

# # ------------------------------------------

# if __name__ == "__main__":

#     file_img = 'frame.png'
#     file_log = 'frame.log'
    
#     stream = collect_stream(open(file_log, 'r'))    
#     frame = extract_h264_frame(stream)
    
#     print_h264_frame(frame)

#     if len(frame) > 0:

#         frame = hex2dec(split(frame))
     
#         if os.path.isfile(file_img): os.remove(file_img)

#         fmt = 'rgb24'  # rgb24, gray, ya8, rgba
        
#         cmd = ('ffmpeg', '-v', 'warning', '-i', '-', '-f', 'image2pipe', '-pix_fmt', fmt, '-vcodec', 'rawvideo', '-')
#         proc = sp.Popen(cmd, bufsize=10**8, stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE)        
        
#         (out, err) = proc.communicate(np.asarray(frame, dtype='uint8').tostring())
    
#         w, h = 960, 720  # TODO: extract image size from output of FFmpeg
    
#         nbcomp, bitpix, shape = None, None, None
#         if fmt == 'gray': nbcomp, bitpix, shape = 1, 8, (h, w)         # 145 kB
#         elif fmt == 'ya8': nbcomp, bitpix, shape = 2, 16, (h, w, 2)    # 180 kB
#         elif fmt == 'rgb24': nbcomp, bitpix, shape = 3, 24, (h, w, 3)  # 312 kB
#         elif fmt == 'rgba': nbcomp, bitpix, shape = 4, 32, (h, w, 4)   # 331 kB
    
#         if shape is None: exit()    
#         size = np.prod(shape)
        
#         if len(out) >= size:  # enough data in stream?
#             raw_image = out[:size]  # just the first frame in stream
#             image = np.fromstring(raw_image, dtype='uint{}'.format(bitpix // nbcomp))
#             image = image.reshape(shape)
#             im = pil.fromarray(image)
#             im.save(file_img)


