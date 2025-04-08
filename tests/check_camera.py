def check_evs_camera_model():
    """
    Kiểm tra loại cảm biến EVS và hiển thị giới hạn bias tương ứng
    """
    try:
        from metavision_core.event_io.raw_reader import initiate_device
        
        # Khởi tạo thiết bị
        print("Đang kết nối với camera EVS...")
        device = initiate_device("", do_time_shifting=False)
        
        # Lấy thông tin nhận dạng phần cứng
        hw_id = device.get_i_hw_identification()
        if hw_id:
            print("\n=== Thông tin phần cứng ===")
            system_id = hw_id.get_system_id()
            print(f"System ID: {system_id}")
            
            # Lấy thông tin sensor
            sensor_info = hw_id.get_sensor_info()
            if sensor_info:
                print(f"Tên sensor: {sensor_info.name}")
                print(f"Phiên bản chính: {sensor_info.major_version}")
                print(f"Phiên bản phụ: {sensor_info.minor_version}")
                
                # Xác định loại sensor dựa trên phiên bản
                if sensor_info.major_version == 3:
                    if sensor_info.minor_version == 1:
                        print("Loại sensor: Gen3.1")
                    else:
                        print("Loại sensor: Gen3")
                elif sensor_info.major_version == 4:
                    if sensor_info.minor_version == 1:
                        print("Loại sensor: Gen4.1")
                    else:
                        print("Loại sensor: Gen4")
                elif "IMX636" in sensor_info.name:
                    print("Loại sensor: IMX636")
                elif "GenX320" in sensor_info.name:
                    print("Loại sensor: GenX320")
        
        # Lấy kích thước cảm biến
        geometry = device.get_i_geometry()
        if geometry:
            width = geometry.get_width()
            height = geometry.get_height()
            print(f"\nKích thước cảm biến: {width}x{height}")
        
        # Lấy thông tin về biases
        biases = device.get_i_ll_biases()
        if biases:
            print("\n=== Thông tin về biases ===")
            all_biases = biases.get_all_biases()
            
            # Hiển thị giá trị và giới hạn của các bias quan trọng
            important_biases = ["bias_diff", "bias_diff_on", "bias_diff_off", "bias_fo", "bias_hpf", "bias_refr"]
            
            for bias_name in important_biases:
                if bias_name in all_biases:
                    bias_value = all_biases[bias_name]
                    bias_info = biases.get_bias_info(bias_name)
                    
                    # Lấy giới hạn của bias
                    min_val, max_val = bias_info.get_bias_range()
                    
                    print(f"{bias_name}:")
                    print(f"  Giá trị hiện tại: {bias_value}")
                    print(f"  Giới hạn: [{min_val}, {max_val}]")
                    
                    # Lấy thêm thông tin mô tả nếu có
                    try:
                        desc = bias_info.get_description()
                        print(f"  Mô tả: {desc}")
                    except:
                        pass
                    
                    # Kiểm tra xem bias có thể điều chỉnh được không
                    try:
                        modifiable = bias_info.is_modifiable()
                        print(f"  Có thể điều chỉnh: {'Có' if modifiable else 'Không'}")
                    except:
                        pass
        
        return "Success"
    
    except Exception as e:
        print(f"Lỗi khi kiểm tra camera EVS: {e}")
        return "Error"

if __name__ == "__main__":
    check_evs_camera_model()