# You should use python3 for compatibility with xbee.
import cv2

cap = cv2.VideoCapture("/opt/awscam/out/ch2_out.mjpeg")

for _ in range(100):
    success, frame = cap.read()
    frame = cv2.resize(frame, (640, 480))
    cv2.imshow("test", frame)
    cv2.waitKey(1)
