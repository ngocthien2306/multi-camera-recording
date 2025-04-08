
import os
from multiprocessing import Process, Queue, Event, Value
import time

from src.utils.process_module import evs_camera_process, frame_recorder_process, rgb_camera_process

MAX_QUEUE_SIZE = 10  # Maximum frames to queue per camera

class CameraManager:
    """Class to manage camera processes"""
    def __init__(self):
        self.evs_cameras = {}  # Dictionary of EVS camera processes by ID
        self.rgb_cameras = {}  # Dictionary of RGB camera processes by ID
        self.frame_queues = {}  # Dictionary of frame queues by (type, ID)
        self.command_events = {}  # Dictionary of command events by (type, ID)
        self.status_values = {}  # Dictionary of status values by (type, ID)
        self.command_queue = {}
        self.device_info_queues = {}  # Add this line to initialize the dict
        
        self.recording = False
        self.recording_path = ""
        self.video_writers = {}  # Store VideoWriter objects for each camera
        
    def add_evs_camera(self, camera_id, device_path=""):
        """Add a new EVS camera"""
        key = ('EVS', camera_id)
        if key in self.command_events:
            self.remove_evs_camera(camera_id)
            
        # Create IPC mechanisms
        frame_queue = Queue(maxsize=MAX_QUEUE_SIZE)
        command_event = Event()
        status_value = Value('i', 0)  # 0=stopped, 1=running
        device_info_queue = Queue()  # Queue to receive device information
        
        if 'command_queue' not in self.__dict__:
            self.command_queue = {}
            
        self.command_queue[key] = Queue()
        
        # Store references
        self.frame_queues[key] = frame_queue
        self.command_events[key] = command_event
        self.status_values[key] = status_value
        self.device_info_queues[key] = device_info_queue
        
        process = Process(
            target=evs_camera_process,
            args=(camera_id, device_path, frame_queue, command_event, 
                status_value, device_info_queue, self.command_queue[key])
        )
        
        self.evs_cameras[camera_id] = process
        return key
        
    def add_rgb_camera(self, camera_id, device_id=0):
        """Add a new RGB camera"""
        key = ('RGB', camera_id)
        if key in self.command_events:
            self.remove_rgb_camera(camera_id)
            
        # Create IPC mechanisms
        frame_queue = Queue(maxsize=MAX_QUEUE_SIZE)
        command_event = Event()
        status_value = Value('i', 0)  # 0=stopped, 1=running
        
        # Store references
        self.frame_queues[key] = frame_queue
        self.command_events[key] = command_event
        self.status_values[key] = status_value
        
        # Create and start the process
        process = Process(
            target=rgb_camera_process,
            args=(camera_id, device_id, frame_queue, command_event, status_value)
        )
        
        self.rgb_cameras[camera_id] = process
        return key
    
    def update_camera_bias(self, bias_name, value, camera_id):
        """Send bias update command to specific EVS camera"""
        key = ('EVS', camera_id)
        if key in self.command_queue:
            self.command_queue[key].put(('update_bias', (bias_name, value)))
        
    def remove_evs_camera(self, camera_id):
        """Remove an EVS camera"""
        key = ('EVS', camera_id)
        if key in self.command_events:
            # Signal the process to stop
            self.command_events[key].set()
            
            # Wait for the process to terminate
            if camera_id in self.evs_cameras:
                process = self.evs_cameras[camera_id]
                if process.is_alive():
                    process.join(timeout=1.0)  # Wait up to 1 second
                    if process.is_alive():
                        process.terminate()  # Force terminate if not stopped
                
                # Clean up
                del self.evs_cameras[camera_id]
                
            # Clean up IPC mechanisms
            del self.frame_queues[key]
            del self.command_events[key]
            del self.status_values[key]
            
    
    
    def start_recording(self, folder_path, tag=""):
        """Start recording from all active cameras with dedicated recording queues"""
        if self.recording:
            return False
        
        # Create timestamp for file naming
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        self.recording_path = folder_path
        self.recording_tag = tag
        
        try:
            # Initialize recording queues and worker processes
            self.recording_queues = {}
            self.recording_processes = {}
            self.recording_stop_events = {}
            
            # Create camera-specific subfolders if they don't exist
            for camera_type in ['EVS', 'RGB']:
                camera_dir = os.path.join(folder_path, camera_type)
                if not os.path.exists(camera_dir):
                    os.makedirs(camera_dir)
            
            # For EVS cameras, start raw recording
            for camera_id in self.evs_cameras.keys():
                key = ('EVS', camera_id)
                
                if self.status_values[key].value == 1:  # Only record running cameras
                    # Start raw recording via command queue
                    raw_filepath = os.path.join(folder_path, 'EVS', f"EVS_{camera_id}_{tag}_{timestamp}.raw")
                    if key not in self.command_queue:
                        self.command_queue[key] = Queue()
                    self.command_queue[key].put(('start_recording', raw_filepath))
                    
                    # Setup a dedicated recording queue for video frames
                    video_filepath = os.path.join(folder_path, 'EVS', f"EVS_{camera_id}_{tag}_{timestamp}.avi")
                    
                    # Get a frame to determine dimensions for video writer
                    frame = self.get_frame('EVS', camera_id)
                    if frame is not None:
                        # Create recording queue and stop event
                        self.recording_queues[key] = Queue(maxsize=100)  # Allow up to 100 frames in buffer
                        self.recording_stop_events[key] = Event()
                        
                        # Start recorder process
                        recorder_process = Process(
                            target=frame_recorder_process,
                            args=(key, video_filepath, self.recording_queues[key], 
                                self.recording_stop_events[key], frame.shape, 25.0, True)
                        )
                        recorder_process.start()
                        self.recording_processes[key] = recorder_process
            
            # For RGB cameras, use dedicated recording queue
            for camera_id in self.rgb_cameras.keys():
                key = ('RGB', camera_id)
                
                if self.status_values[key].value == 1:  # Only record running cameras
                    # Determine output file name with tag
                    file_path = os.path.join(folder_path, 'RGB', f"RGB_{camera_id}_{tag}_{timestamp}.avi")
                    
                    # Get a frame to determine dimensions
                    frame = self.get_frame('RGB', camera_id)
                    if frame is not None:
                        # Create recording queue and stop event
                        self.recording_queues[key] = Queue(maxsize=100)  # Allow up to 100 frames in buffer
                        self.recording_stop_events[key] = Event()
                        
                        # Start recorder process
                        recorder_process = Process(
                            target=frame_recorder_process,
                            args=(key, file_path, self.recording_queues[key], 
                                self.recording_stop_events[key], frame.shape, 30.0, False)
                        )
                        recorder_process.start()
                        self.recording_processes[key] = recorder_process
            
            # Set recording state
            self.recording = True
            print(f"Started recording to {folder_path}")
            return True
        
        except Exception as e:
            print(f"Error starting recording: {e}")
            self.stop_recording()
            return False

    def stop_recording(self):
        """Stop recording from all cameras"""
        if not self.recording:
            return
        
        # Stop raw recording for EVS cameras
        for key in list(self.command_queue.keys()):
            if key[0] == 'EVS':  # For EVS cameras
                self.command_queue[key].put(('stop_recording', None))
        
        # Signal all recorder processes to stop
        for key, stop_event in self.recording_stop_events.items():
            stop_event.set()
        
        # Wait for recorder processes to finish
        for key, process in self.recording_processes.items():
            process.join(timeout=5.0)  # Wait up to 5 seconds
            if process.is_alive():
                process.terminate()
        
        # Clear recording resources
        if hasattr(self, 'recording_queues'):
            self.recording_queues.clear()
        if hasattr(self, 'recording_processes'):
            self.recording_processes.clear()
        if hasattr(self, 'recording_stop_events'):
            self.recording_stop_events.clear()
        
        self.recording = False
        self.recording_path = ""
        print("Recording stopped")

    def record_frame(self, camera_type, camera_id, frame):
        """Add frame to recording queue if recording is active"""
        if not self.recording:
            return
        
        key = (camera_type, camera_id)
        if key in self.recording_queues and frame is not None:
            # Add frame to recording queue without blocking
            if not self.recording_queues[key].full():
                self.recording_queues[key].put(frame.copy())  # Use copy to prevent reference issues
        
        
    def remove_rgb_camera(self, camera_id):
        """Remove an RGB camera"""
        key = ('RGB', camera_id)
        if key in self.command_events:
            # Signal the process to stop
            self.command_events[key].set()
            
            # Wait for the process to terminate
            if camera_id in self.rgb_cameras:
                process = self.rgb_cameras[camera_id]
                if process.is_alive():
                    process.join(timeout=1.0)  # Wait up to 1 second
                    if process.is_alive():
                        process.terminate()  # Force terminate if not stopped
                
                # Clean up
                del self.rgb_cameras[camera_id]
                
            # Clean up IPC mechanisms
            del self.frame_queues[key]
            del self.command_events[key]
            del self.status_values[key]
    
    def start_all_cameras(self):
        """Start all camera processes"""
        for camera_id, process in self.evs_cameras.items():
            if not process.is_alive():
                process.start()
                
                time.sleep(5)
                
        for camera_id, process in self.rgb_cameras.items():
            if not process.is_alive():
                process.start()
    
    def stop_all_cameras(self):
        """Stop all camera processes"""
        # Signal all processes to stop
        for key in list(self.command_events.keys()):
            self.command_events[key].set()
        
        # Wait for all processes to terminate
        for camera_id, process in list(self.evs_cameras.items()):
            if process.is_alive():
                process.join(timeout=1.0)
                if process.is_alive():
                    process.terminate()
        
        for camera_id, process in list(self.rgb_cameras.items()):
            if process.is_alive():
                process.join(timeout=1.0)
                if process.is_alive():
                    process.terminate()
        
        # Clear all dictionaries
        self.evs_cameras.clear()
        self.rgb_cameras.clear()
        self.frame_queues.clear()
        self.command_events.clear()
        self.status_values.clear()
    
    def get_frame(self, camera_type, camera_id):
        """Get the latest frame from a camera, non-blocking"""
        key = (camera_type, camera_id)
        if key in self.frame_queues and not self.frame_queues[key].empty():
            # Get the latest frame from the queue
            received_id, frame = self.frame_queues[key].get()
            return frame
        return None
    
    def is_camera_running(self, camera_type, camera_id):
        """Check if a camera is running"""
        key = (camera_type, camera_id)
        if key in self.status_values:
            return self.status_values[key].value == 1
        return False
    
    def cleanup(self):
        """Clean up all resources"""
        self.stop_all_cameras()

