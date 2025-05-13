import ctypes
import sys
import os
import time
import queue
import numpy as np
import cv2
from ilidar import iTFS

# Global variables
callback_event_queue = queue.Queue()

# Define the Python callback function
CALLBACK_TYPE = ctypes.CFUNCTYPE(None, ctypes.POINTER(ctypes.c_uint16))

# This callback function is used for data notification
def python_callback(ptr):
    # Print frame count
    if not hasattr(python_callback, "frame_count"):
        python_callback.frame_count = 0
    print(f"F# {python_callback.frame_count}")
    python_callback.frame_count += 1

    # Send signal to main thread
    callback_event_queue.put(python_callback.frame_count)

# Get dll path
def get_full_dll_path():
    if os.name == "nt":
        # Windows: use ilidar.dll
        dir_path = os.getcwd()
        dll_file = "libilidar.dll"
        full_path = dir_path + "/" + dll_file
    else:
        # Unix-like: use ilidar.so
        dir_path = os.getcwd()
        dll_file = "libilidar.so"
        full_path = dir_path + "/" + dll_file

    # Check the dll file exist
    if os.path.exists(full_path) == False:
        print("Fail to find the dll file in the path: ")
        print(full_path)
        return None
    else:
        return full_path

#### MAIN ENTRY POINT ####
if __name__ == '__main__':
    # Create a 320x320 uint16 image buffer for sensor reading
    img = np.zeros((320, 320), dtype=np.uint16)
    img_ptr = img.ctypes.data_as(ctypes.POINTER(ctypes.c_uint16))

    # Get full path for the DLL file
    full_dll_path = get_full_dll_path()

    # Get new instance
    LiDAR = iTFS(full_dll_path)
    ctype_callback = CALLBACK_TYPE(python_callback)
    if LiDAR.init(img_ptr, ctype_callback) == False:
        sys.exit(0)

    # Create interface (Deprecated)
    # ilidar.py implicitly setup host IP address. You don't have to set it.
    # pc_ip = "192.168.5.2"   
    # pc_port = 7256          
    # if LiDAR.create(pc_ip, pc_port) == False:
    #     sys.exit(0)

    # Connect new sensor
    sensor_ip = "192.168.5.116" # To do: modify this IP to your network setup
    sensor_port = 7257          # Default
    if LiDAR.connect(sensor_ip, sensor_port) == False:
        LiDAR.destroy()
        sys.exit(0)

    # Sleep a second
    time.sleep(1)

    # Get parameters
    print("Connected sensor:")
    read_params = LiDAR.get_params()
    time.sleep(0.5)
    LiDAR.print_params(read_params)

    # Modify parameters
    print("Modified parameters (only changed parameters are listed): ")
    write_params = read_params.copy()   # Modify values from readings
    write_params['capture_mode'] = 1
    write_params['capture_shutter'] = [400, 80, 16, 0, 8000]
    write_params['capture_limit'] = [200, 200]
    write_params['capture_period_us'] = 100000
    write_params['capture_seq'] = 0
    LiDAR.print_diff(read_params, write_params)

    # Set parameters
    LiDAR.unlock()
    time.sleep(1)
    LiDAR.set_params(write_params)
    time.sleep(0.5)
    LiDAR.store()

    # Start stream
    print("Start to stream data")
    LiDAR.start()

    # Infinite loop
    try:
        print("Press Ctrl+C to exit.")
        while True:
            # Wait for queue
            recv_frame_count = callback_event_queue.get()
    
            # Get depth and intensity images from the raw output data
            depth = img[:160, :]         # depth unit = [mm] 
            intensity = img[160:, :]

            # Normalize to display
            depth_norm = np.clip((depth / 8000) * 255, 0, 255).astype(np.uint8) # normalized from 0 to 8 m
            intensity_norm = np.clip((intensity / 16384) * 255, 0, 255).astype(np.uint8)

            # Display using opencv
            cv2.imshow("DEPTH", depth_norm)
            cv2.imshow("INTENSITY", intensity_norm)
            cv2.waitKey(1)

    except KeyboardInterrupt:
        print("\nCtrl+C detected! Cleaning up before exit.")

    # Delete interface
    LiDAR.stop()
    LiDAR.disconnect()
    LiDAR.destroy()

    # Destroy opencv windows
    cv2.destroyAllWindows()

    # Exit
    sys.exit(0)
