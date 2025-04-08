import cv2
import numpy as np

def open_multiple_cameras(num_cameras=3):
    # Tạo danh sách để lưu trữ các đối tượng camera
    cameras = []
    
    # Mở các camera
    for i in range(num_cameras):
        cap = cv2.VideoCapture(i)
        # Kiểm tra xem camera có mở được không
        if not cap.isOpened():
            print(f"Không thể mở camera {i}")
        else:
            print(f"Đã mở camera {i}")
            cameras.append(cap)
    
    if len(cameras) == 0:
        print("Không thể mở bất kỳ camera nào")
        return
    
    while True:
        frames = []
        # Đọc frame từ mỗi camera
        for i, cap in enumerate(cameras):
            ret, frame = cap.read()
            if not ret:
                print(f"Không thể đọc frame từ camera {i}")
                # Đặt một khung hình trống
                h, w = 480, 640
                frame = np.zeros((h, w, 3), dtype=np.uint8)
                cv2.putText(frame, f"Camera {i} disconnected", (50, h//2), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            frames.append(frame)
        
        # Nếu có ít hơn 3 camera, tạo khung hình trống
        while len(frames) < 3:
            h, w = 480, 640
            empty_frame = np.zeros((h, w, 3), dtype=np.uint8)
            cv2.putText(empty_frame, f"No Camera {len(frames)}", (50, h//2), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            frames.append(empty_frame)
        
        # Đảm bảo tất cả các khung hình có cùng kích thước
        resized_frames = []
        for frame in frames:
            resized = cv2.resize(frame, (640, 480))
            resized_frames.append(resized)
        
        # Tạo layout hiển thị: 3 camera cạnh nhau theo chiều ngang
        top_row = np.hstack((resized_frames[0], resized_frames[1], resized_frames[2]))
        
        # Hiển thị tất cả camera
        cv2.imshow('Multiple Cameras', top_row)
        
        # Nhấn 'q' để thoát
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    # Giải phóng tất cả camera và đóng cửa sổ
    for cap in cameras:
        cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    open_multiple_cameras(3)