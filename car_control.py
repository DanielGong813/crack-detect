import sys
import socket
import cv2
import numpy as np
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
import struct

# 小车控制TCP客户端
# class CarClient(QObject):
#     def __init__(self, ip, port):
#         super().__init__()
#         self.ip = ip
#         self.port = port
#         self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#         self.is_connected = False
#
#     def connect_server(self):
#         try:
#             self.socket.connect((self.ip, self.port))
#             self.is_connected = True
#             QMessageBox.information(None, "提示", "连接小车成功！")
#         except Exception as e:
#             QMessageBox.critical(None, "错误", f"连接失败：{str(e)}")
#             self.is_connected = False
#
#     def send_cmd(self, cmd):
#         if not self.is_connected:
#             QMessageBox.warning(None, "警告", "请先连接小车！")
#             return
#         try:
#             self.socket.send(("ON" + cmd).encode("utf-8"))
#         except Exception as e:
#             QMessageBox.critical(None, "错误", f"发送指令失败：{str(e)}")
#             self.is_connected = False

# 图像接收线程（严格匹配你的树莓派发送协议）
class VideoThread(QThread):
    frame_signal = pyqtSignal(np.ndarray)

    def __init__(self, port=8000):
        super().__init__()
        self.port = port
        self.running = True
        self.conn = None
        self.server_socket = None

    def run(self):
        # 创建TCP服务端，等待树莓派连接
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(("0.0.0.0", self.port))
        self.server_socket.listen(1)
        print(f"等待树莓派摄像头连接，端口：{self.port}")

        # 接收树莓派连接
        self.conn, addr = self.server_socket.accept()
        print(f"树莓派已连接：{addr}")

        # 循环接收图像
        while self.running:
            try:
                # 1. 接收4字节长度（和树莓派 struct.pack(">L" 完全对应）
                len_data = self.recv_all(4)
                if not len_data:
                    break
                data_len = struct.unpack(">L", len_data)[0]

                # 2. 接收完整JPEG图像
                img_data = self.recv_all(data_len)
                if not img_data:
                    break

                # 3. 解码图像
                nparr = np.frombuffer(img_data, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if frame is not None:
                    self.frame_signal.emit(frame)

            except:
                break

    # 确保接收指定长度的数据（解决TCP粘包/分包）
    def recv_all(self, size):
        data = b""
        while len(data) < size:
            chunk = self.conn.recv(size - len(data))
            if not chunk:
                return None
            data += chunk
        return data

    def stop(self):
        self.running = False
        if self.conn:
            self.conn.close()
        if self.server_socket:
            self.server_socket.close()

# 主UI界面
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CSI摄像头小车控制")
        self.setFixedSize(1400, 960)

        # ==================== 配置区 ====================
        self.CAR_IP = "192.168.137.58"    # 树莓派IP
        self.CAR_CTRL_PORT = 2001       # 小车控制端口
        self.CAMERA_PORT = 8000         # 图像端口（和树莓派一致）
        # ================================================

        # self.car_client = CarClient(self.CAR_IP, self.CAR_CTRL_PORT)
        self.video_thread = None
        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # 视频显示区域
        self.video_label = QLabel()
        self.video_label.setStyleSheet("background-color: black;")
        self.video_label.setMinimumSize(1296, 972)
        self.video_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.video_label, alignment=Qt.AlignCenter)

        # 控制按钮布局
        control_layout = QGridLayout()
        main_layout.addLayout(control_layout)

        # 按钮创建
        self.btn_connect = QPushButton("连接小车")
        self.btn_forward = QPushButton("前进")
        self.btn_backward = QPushButton("后退")
        self.btn_left = QPushButton("左转")
        self.btn_right = QPushButton("右转")
        self.btn_stop = QPushButton("停止")

        # 按钮样式
        self.btn_connect.setStyleSheet("font-size:16px; padding:10px; background:green; color:white;")
        self.btn_stop.setStyleSheet("font-size:16px; padding:10px; background:red; color:white;")
        btn_style = "font-size:16px; padding:10px;"
        self.btn_forward.setStyleSheet(btn_style)
        self.btn_backward.setStyleSheet(btn_style)
        self.btn_left.setStyleSheet(btn_style)
        self.btn_right.setStyleSheet(btn_style)

        # 按钮布局
        control_layout.addWidget(self.btn_connect, 0, 0, 1, 4)
        control_layout.addWidget(self.btn_forward, 1, 1)
        control_layout.addWidget(self.btn_left, 2, 0)
        control_layout.addWidget(self.btn_stop, 2, 1)
        control_layout.addWidget(self.btn_right, 2, 2)
        control_layout.addWidget(self.btn_backward, 3, 1)

        # 绑定事件（只注释掉功能，不删除UI）
        self.btn_connect.clicked.connect(self.on_connect)
        # self.btn_forward.clicked.connect(lambda: self.car_client.send_cmd("A"))
        # self.btn_backward.clicked.connect(lambda: self.car_client.send_cmd("B"))
        # self.btn_left.clicked.connect(lambda: self.car_client.send_cmd("C"))
        # self.btn_right.clicked.connect(lambda: self.car_client.send_cmd("D"))
        # self.btn_stop.clicked.connect(lambda: self.car_client.send_cmd("E"))

    def on_connect(self):
        # 启动图像接收线程
        if self.video_thread is None:
            self.video_thread = VideoThread(self.CAMERA_PORT)
            self.video_thread.frame_signal.connect(self.show_frame)
            self.video_thread.start()

        # 连接小车控制（已注释）
        # self.car_client.connect_server()

    def show_frame(self, frame):
        # OpenCV转Qt图像
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        qt_img = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        self.video_label.setPixmap(QPixmap.fromImage(qt_img).scaled(
            self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def closeEvent(self, event):
        if self.video_thread:
            self.video_thread.stop()
        # if self.car_client.is_connected:
        #     self.car_client.socket.close()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())