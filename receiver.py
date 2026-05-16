import socket
import cv2
import numpy as np
import struct
import threading

frame = None
lock = threading.Lock()

def recv_thread():
    global frame
    HOST = '0.0.0.0'
    PORT = 8000

    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4*1024*1024)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen(1)
    conn, addr = s.accept()

    while True:
        try:
            data_len = conn.recv(4)
            if len(data_len) < 4:
                break

            length = struct.unpack(">L", data_len)[0]

            # ===================== 安全修复 1 =====================
            if length <= 0 or length > 3 * 1024 * 1024:
                continue

            data = b''
            while len(data) < length:
                packet = conn.recv(4096)
                if not packet:
                    break
                data += packet

            arr = np.frombuffer(data, dtype=np.uint8)
            new_frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)

            # ===================== 安全修复 2 =====================
            if new_frame is not None:
                with lock:
                    frame = new_frame.copy()  # 必须copy

        except:
            break

t = threading.Thread(target=recv_thread)
t.daemon = True
t.start()

while True:
    current_frame = None
    with lock:
        current_frame = frame

    if current_frame is not None:
        cv2.imshow("frame", current_frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cv2.destroyAllWindows()