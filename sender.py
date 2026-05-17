import socket
import struct
from picamera2 import Picamera2
import io
import time

PC_IP = "192.168.43.2"
PORT = 8000

picam2 = Picamera2()
config = picam2.create_preview_configuration(
    main={"size": (2592, 1944)},
    controls={
        "ExposureTime": 25000,

    }
)
picam2.configure(config)
picam2.start()

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((PC_IP, PORT))

while True:
    stream = io.BytesIO()
    picam2.capture_file(stream, format='jpeg')
    data = stream.getvalue()

    try:
        s.sendall(struct.pack(">L", len(data)))
        s.sendall(data)
    except:
        break

    stream.seek(0)
    time.sleep(0.1)
