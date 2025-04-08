class BiasInfo:
    """Stores information about a specific bias"""
    def __init__(self, name, value, min_val, max_val, description="", modifiable=True):
        self.name = name
        self.value = value
        self.min_val = min_val
        self.max_val = max_val
        self.description = description
        self.modifiable = modifiable
        
class CameraSensorType:
    """Enum for EVS camera types"""
    UNKNOWN = "Unknown"
    GEN3 = "Gen3"
    GEN31 = "Gen3.1"
    GEN4 = "Gen4"
    GEN41 = "Gen4.1"
    IMX636 = "IMX636"
    GENX320 = "GenX320"

class CameraBiasManager:
    """Class to manage biases based on camera type"""
    
    @staticmethod
    def detect_camera_model(device):
        """Determine camera type from device"""
        try:
            # Get hardware identification information
            hw_id = device.get_i_hw_identification()
            if hw_id:
                # Get sensor information
                sensor_info = hw_id.get_sensor_info()
                if sensor_info:
                    # Identify sensor type based on version and name
                    if "IMX636" in sensor_info.name:
                        return CameraSensorType.IMX636
                    elif "GenX320" in sensor_info.name:
                        return CameraSensorType.GENX320
                    elif sensor_info.major_version == 3:
                        if sensor_info.minor_version == 1:
                            return CameraSensorType.GEN31
                        else:
                            return CameraSensorType.GEN3
                    elif sensor_info.major_version == 4:
                        if sensor_info.minor_version == 1:
                            return CameraSensorType.GEN41
                        else:
                            return CameraSensorType.GEN4
            
            # If unable to determine from HW info, try to identify from biases
            biases = device.get_i_ll_biases()
            if biases:
                all_biases = biases.get_all_biases()
                
                # Identify camera type from bias_diff
                if "bias_diff" in all_biases:
                    bias_diff = all_biases["bias_diff"]
                    if bias_diff == 299 or (250 < bias_diff < 350):
                        return CameraSensorType.GEN31
                    elif bias_diff == 80 or (50 < bias_diff < 100):
                        return CameraSensorType.GEN41
                    elif bias_diff == 0 or (-25 <= bias_diff <= 23):
                        return CameraSensorType.IMX636
                    elif bias_diff == 51 or (41 <= bias_diff <= 51):
                        return CameraSensorType.GENX320
            
            # If unable to determine from biases, try to identify from dimensions
            geometry = device.get_i_geometry()
            if geometry:
                width = geometry.get_width()
                height = geometry.get_height()
                
                if width == 1280 and height == 720:
                    return CameraSensorType.IMX636
                elif width == 320 and height == 320:
                    return CameraSensorType.GENX320
                elif width == 640 and height == 480:
                    # Cannot precisely distinguish Gen3 vs Gen4 from dimensions alone
                    return CameraSensorType.GEN4  # Default to Gen4
                    
        except Exception as e:
            print(f"Error determining camera type: {e}")
        
        return CameraSensorType.UNKNOWN
    
    @staticmethod
    def get_bias_limits(camera_type):
        """
        Returns default bias limits for each camera type
        Returns a dict with bias name as key and value as tuple (default_value, min, max, description)
        """
        # Bias limits for Gen3.1
        if camera_type == CameraSensorType.GEN31:
            return {
                "bias_diff": (299, 200, 400, "Bias differential reference"),
                "bias_diff_on": (384, 374, 499, "ON events contrast threshold"),
                "bias_diff_off": (222, 100, 234, "OFF events contrast threshold"),
                "bias_fo": (1477, 1250, 1800, "Low-pass filter bandwidth"),
                "bias_hpf": (1499, 900, 1800, "High-pass filter bandwidth"),
                "bias_refr": (1500, 1300, 1800, "Refractory period")
            }
        
        # Bias limits for Gen4.1
        elif camera_type == CameraSensorType.GEN41:
            return {
                "bias_diff": (80, 52, 100, "Bias differential reference"),
                "bias_diff_on": (115, 95, 140, "ON events contrast threshold"),
                "bias_diff_off": (52, 25, 65, "OFF events contrast threshold"),
                "bias_fo": (74, 45, 110, "Low-pass filter bandwidth"),
                "bias_hpf": (0, 0, 120, "High-pass filter bandwidth"),
                "bias_refr": (68, 30, 100, "Refractory period")
            }
        
        # Bias limits for IMX636
        elif camera_type == CameraSensorType.IMX636:
            return {
                "bias_diff": (0, -25, 23, "Bias differential reference"),
                "bias_diff_on": (0, -85, 140, "ON events contrast threshold"),
                "bias_diff_off": (0, -35, 190, "OFF events contrast threshold"),
                "bias_fo": (0, -35, 55, "Low-pass filter bandwidth"),
                "bias_hpf": (0, 0, 120, "High-pass filter bandwidth"),
                "bias_refr": (0, -20, 235, "Refractory period")
            }
        
        # Bias limits for GenX320
        elif camera_type == CameraSensorType.GENX320:
            return {
                "bias_diff": (51, 41, 51, "Bias differential reference"),
                "bias_diff_on": (25, 24, 60, "ON events contrast threshold"),
                "bias_diff_off": (28, 19, 50, "OFF events contrast threshold"),
                "bias_fo": (34, 19, 39, "Low-pass filter bandwidth"),
                "bias_hpf": (40, 0, 127, "High-pass filter bandwidth"),
                "bias_refr": (10, 0, 127, "Refractory period")
            }
        
        # Default values for Gen3/Gen4 or unidentified
        else:
            return {
                "bias_diff": (0, -25, 23, "Bias differential reference"),
                "bias_diff_on": (0, -85, 140, "ON events contrast threshold"),
                "bias_diff_off": (0, -35, 190, "OFF events contrast threshold"),
                "bias_fo": (0, -35, 55, "Low-pass filter bandwidth"),
                "bias_hpf": (0, 0, 120, "High-pass filter bandwidth"),
                "bias_refr": (0, -20, 235, "Refractory period")
            }
    
    @staticmethod
    def get_biases_from_device(device):
        """Get bias information from camera device"""
        biases_info = {}
        
        try:
            biases_facility = device.get_i_ll_biases()
            if biases_facility:
                all_biases = biases_facility.get_all_biases()
                
                # Get detailed information for each bias
                for bias_name, bias_value in all_biases.items():
                    try:
                        bias_info = biases_facility.get_bias_info(bias_name)
                        min_val, max_val = bias_info.get_bias_range()
                        description = bias_info.get_description()
                        modifiable = bias_info.is_modifiable()
                        
                        biases_info[bias_name] = BiasInfo(
                            bias_name, bias_value, min_val, max_val, 
                            description, modifiable
                        )
                    except Exception as e:
                        print(f"Error getting detailed information for bias {bias_name}: {e}")
        except Exception as e:
            print(f"Error getting bias information from device: {e}")
            
        return biases_info

