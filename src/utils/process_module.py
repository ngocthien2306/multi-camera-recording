import queue
import time
import cv2
import numpy as np
from src.utils.biases import CameraBiasManager
try:
    from metavision_core.event_io.raw_reader import initiate_device
    from metavision_core.event_io import EventsIterator, LiveReplayEventsIterator, is_live_camera
    from metavision_sdk_core import PeriodicFrameGenerationAlgorithm, ColorPalette
    METAVISION_AVAILABLE = True
except ImportError:
    METAVISION_AVAILABLE = False
    print("Metavision SDK not available. Only RGB cameras are supported.")




def evs_camera_process(camera_id, device_path, frame_queue, command_event, status_value, device_info_queue=None, command_queue=None):
    """Process function for EVS camera processing"""
    if not METAVISION_AVAILABLE:
        print(f"Cannot initialize EVS camera {camera_id}: Metavision SDK not available")
        dummy_frame = np.zeros((480, 640), dtype=np.uint8)
        frame_queue.put((camera_id, dummy_frame))
        status_value.value = 0  # Mark as stopped
        return
        
    try:
        print(f"Opening EVS camera {camera_id}: '{device_path}'")
        status_value.value = 1  # Mark as running
        device = initiate_device("", do_time_shifting=False)
        
        # Send camera model information through Queue if available
        if device_info_queue:
            # Detect camera type
            camera_type = CameraBiasManager.detect_camera_model(device)
            biases_info = CameraBiasManager.get_biases_from_device(device)
            geometry = device.get_i_geometry()
            width = geometry.get_width() if geometry else 0
            height = geometry.get_height() if geometry else 0
            
            # Send information to main process
            device_info_queue.put({
                'camera_id': camera_id,
                'camera_type': camera_type,
                'resolution': (width, height),
                'biases': biases_info
            })
        
        mv_iterator = EventsIterator.from_device(device, start_ts=0, delta_t=1000)
        
        # mv_iterator = EventsIterator(input_path=device_path, delta_t=1000)
        height, width = mv_iterator.get_size()
        print(f"EVS camera {camera_id} opened with resolution: {width}x{height}")
        
        # Check if we should use live replay for recorded files
        if not is_live_camera(device_path):
            mv_iterator = LiveReplayEventsIterator(mv_iterator)
        
        # Create frame generator
        event_frame_gen = PeriodicFrameGenerationAlgorithm(
            sensor_width=width,
            sensor_height=height,
            fps=25,
            palette=ColorPalette.Gray
        )
        
        # Set callback for frame generation
        def on_cd_frame_cb(ts, cd_frame):
            if not command_event.is_set() and not frame_queue.full():
                # Create a copy of the frame for multiprocessing
                frame_copy = cd_frame.copy()
                frame_queue.put((camera_id, frame_copy))
        
        event_frame_gen.set_output_callback(on_cd_frame_cb)
        
        # Process events
        for evs in mv_iterator:
            if command_event.is_set():
                break
            
            if command_queue and not command_queue.empty():
                cmd, arg = command_queue.get()
                if cmd == 'start_recording':
                    # Start raw recording
                    device.get_i_events_stream().log_raw_data(arg)
                    print(f"EVS camera {camera_id} started raw recording to {arg}")
                elif cmd == 'stop_recording':
                    # Stop raw recording
                    device.get_i_events_stream().stop_log_raw_data()
                    print(f"EVS camera {camera_id} stopped raw recording")
                    
                elif cmd == 'update_bias':
                    # Update bias settings
                    bias_name, value = arg
                    try:
                        biases = device.get_i_ll_biases()
                        if biases is not None:
                            biases.set(bias_name, value)
                            print(f"EVS camera {camera_id} updated bias {bias_name} = {value}")
                    except Exception as e:
                        print(f"Error updating bias for camera {camera_id}: {e}")
                                    
            # Process events from camera
            event_frame_gen.process_events(evs)
            
    except Exception as e:
        print(f"Error in EVS camera {camera_id} process: {e}")
        # Send a dummy frame to keep the UI running
        dummy_frame = np.zeros((480, 640), dtype=np.uint8)
        if not frame_queue.full():
            frame_queue.put((camera_id, dummy_frame))
    finally:
        status_value.value = 0  # Mark as stopped
        print(f"EVS camera {camera_id} process stopped")

def rgb_camera_process(camera_id, device_id, frame_queue, command_event, status_value):
    """Process function for RGB camera processing"""
    try:
        print(f"Opening RGB camera {camera_id}, device ID: {device_id}")
        cap = cv2.VideoCapture(device_id)
        
        if not cap.isOpened():
            raise Exception(f"Cannot open RGB camera with device ID {device_id}")
        
        # Set camera properties
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        
        # Mark process as running
        status_value.value = 1
        
        # Calculate delay based on desired FPS
        fps = 30
        delay = 1.0 / fps
        
        while not command_event.is_set():
            ret, frame = cap.read()
            if ret:
                if not frame_queue.full():
                    frame_queue.put((camera_id, frame.copy()))
            else:
                # Send a dummy frame on error
                dummy_frame = np.zeros((1280, 720, 3), dtype=np.uint8)
                if not frame_queue.full():
                    frame_queue.put((camera_id, dummy_frame))
                print(f"Error reading frame from RGB camera {camera_id}")
            
            # Control frame rate
            time.sleep(delay)
            
    except Exception as e:
        print(f"Error in RGB camera {camera_id} process: {e}")
        dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        if not frame_queue.full():
            frame_queue.put((camera_id, dummy_frame))
    finally:
        if 'cap' in locals() and cap.isOpened():
            cap.release()
        status_value.value = 0  # Mark as stopped
        print(f"RGB camera {camera_id} process stopped")

def frame_recorder_process(camera_key, file_path, frame_queue, stop_event, frame_shape, fps, is_grayscale):
    """Process function for recording frames to video file"""
    try:
        print(f"Starting recorder process for {camera_key} to {file_path}")
        
        # Determine video parameters
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        
        if len(frame_shape) == 2:  # Grayscale
            height, width = frame_shape
            is_color = False
        else:  # RGB
            height, width, _ = frame_shape
            is_color = True
        
        # Create video writer
        writer = cv2.VideoWriter(file_path, fourcc, fps, (width, height), is_color)
        
        if not writer.isOpened():
            raise Exception(f"Failed to open video writer for {file_path}")
        
        frame_count = 0
        last_time = time.time()
        actual_fps = 0
        
        # Process frames until stop signal
        while not stop_event.is_set() or not frame_queue.empty():
            try:
                # Use a timeout to check for stop_event periodically
                frame = frame_queue.get(timeout=0.1)
                
                # Write frame
                writer.write(frame)
                frame_count += 1
                
                # Calculate actual FPS for logging
                if frame_count % 30 == 0:
                    current_time = time.time()
                    time_diff = current_time - last_time
                    if time_diff > 0:
                        actual_fps = 30 / time_diff
                        print(f"Recording {camera_key} at {actual_fps:.1f} FPS, queue size: {frame_queue.qsize()}")
                    last_time = current_time
                    
            except queue.Empty:
                # No frame available, just continue and check stop_event
                pass
                
    except Exception as e:
        print(f"Error in recorder process for {camera_key}: {e}")
    finally:
        # Make sure to close the writer
        if 'writer' in locals():
            writer.release()
            print(f"Recorder for {camera_key} stopped after writing {frame_count} frames")
