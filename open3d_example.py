import ctypes
import sys
import os
import time
import queue
import numpy as np
import open3d as o3d
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

# Create 3D viewer
def init_viewer():
    global pcd
    global vis
    
    # Initialize pointcloud visualizer
    vis = o3d.visualization.VisualizerWithKeyCallback()  # Interactive visualizer
    vis.create_window(window_name="Point Cloud Viewer")

    # Add a coordinate frame to show XYZ axes
    coordinate_frame = o3d.geometry.TriangleMesh.create_coordinate_frame(
        size=0.1,  # Adjust size as needed
        origin=[0, 0, 0]  # Origin of the coordinate frame
    )
    vis.add_geometry(coordinate_frame)

    # Add a grid
    grid = create_grid(size=10, step=1, height=-2.0)
    vis.add_geometry(grid)

    # Create an initial empty point cloud
    pcd = o3d.geometry.PointCloud()

    # Add the point cloud to the visualizer
    vis.add_geometry(pcd)

    # Customize render options
    render_option = vis.get_render_option()
    render_option.point_size = 2.0  # Set point size (default is 1.0)
    render_option.background_color = np.array([0, 0, 0])  # Black background

    # Camera and view setup
    view_control = vis.get_view_control()
    view_control.set_up([0, 0, 1])            # Set Z-up orientation
    vis.reset_view_point(True)

    # Add key callback for 'R' key to reset
    def reset_window_callback(vis):
        vis.reset_view_point(True)

    vis.register_key_callback(ord("R"), reset_window_callback)

# Create grid
def create_grid(size=10, step=1, color=[0.5, 0.5, 0.5], height=0):
    lines = []
    points = []

    # Create grid points and lines
    for i in range(-size, size + 1, step):
        # Horizontal lines (parallel to X-axis)
        points.append([i, -size, height])
        points.append([i, size, height])
        lines.append([len(points) - 2, len(points) - 1])

        # Vertical lines (parallel to Y-axis)
        points.append([-size, i, height])
        points.append([size, i, height])
        lines.append([len(points) - 2, len(points) - 1])

    # Convert to Open3D LineSet
    grid = o3d.geometry.LineSet()
    grid.points = o3d.utility.Vector3dVector(points)
    grid.lines = o3d.utility.Vector2iVector(lines)
    grid.colors = o3d.utility.Vector3dVector([color] * len(lines))

    return grid

# Read 3D reconstruction vectors from the file
def read_intrinsic(file_path):
    # Open the binary file in read mode
    with open(file_path, "rb") as fp:
        # Read the binary data and reshape into the desired array
        vec = np.fromfile(fp, dtype=np.float32).reshape((240, 320, 3))
    return vec[40:200, :, :]

#### MAIN ENTRY POINT ####
if __name__ == '__main__':
    # Get intrinsic vector for 3d reconstruction
    vec = read_intrinsic("iTFS-110.dat")
    vec = vec.reshape(-1, 3)

    # Rotate the vectors to X-front, Y-left, and Z-up Cartesian coordinates
    vec_x = vec[:, 2].reshape(-1, 1)  # Reshape to 2D
    vec_y = (-vec[:, 0]).reshape(-1, 1)
    vec_z = (-vec[:, 1]).reshape(-1, 1)
    vec_3d = np.concatenate((vec_x, vec_y, vec_z), axis=1)

    # Initialize point cloud viewer
    init_viewer()

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
            depth = img[:160, :]            # depth unit = mm
            # intensity = img[160:, :]      # Not used in this example

            # Reconstruct to 3D point cloud
            points = 0.001 * vec_3d * depth.reshape(-1, 1)   # 0.001 for mm to m unit

            # Visualize
            pcd.points = o3d.utility.Vector3dVector(points)
            vis.update_geometry(pcd)
            vis.poll_events()
            vis.update_renderer()
            time.sleep(0.001)

    except KeyboardInterrupt:
        print("\nCtrl+C detected! Cleaning up before exit.")

    # Delete interface
    LiDAR.stop()
    LiDAR.disconnect()
    LiDAR.destroy()

    # Destroy open3d windows
    vis.destroy_window()

    # Exit
    sys.exit(0)
