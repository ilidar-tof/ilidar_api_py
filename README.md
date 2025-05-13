# ilidar-api-pywrapper

- This repository contains the initial version of a Python script for the iLidar-ToF iTFS series.
- The script in this repository utilizes a pre-compiled library (`libilidar.dll` or `libilidar.so`) to control the sensor in a many-to-many configuration.
- More details and additional example scripts will be updated in the future.

**Current Version is 1.0.2 (2025-05-13)**

## Project List
|Project|Library|Description|Usage|
|:---:|:---:|:---|:---|
|`opencv_example`|OpenCV|Illustrates how to read the depth and intensity data and convert them to the image format|2D depth and intensity images|
|`open3d_example`|Open3D|Illustrates how to transform the depth images to the point cloud|3D point cloud|

## Test Environment
This repository has been built and tested with real sensors in the following environment:
|      OS      | Python | OpenCV | Open3D |
| :----------: | :----: | :----: | :----: |
|  Windows 10  | 3.12.X | 4.9.0  | 0.19.0 |
| Ubuntu 20.04 | 3.8.X  | 4.7.0  | 0.19.0 |

## OpenCV

- `opencv_example.py` demonstrates a simple script for reading and displaying depth and intensity images.
- To run the script, follow these steps:
  1. Ensure the sensor is connected and configured within the same subnet as this PC.
  2. Set the sensor’s IP address (`sensor_ip`) at **L#70**.
  3. Modify any parameters you wish to change at **L#88**. Detailed parameter descriptions can be found on the **HYBO GitHub page**.
  4. Run the script using:
     ```sh
     $ python3 opencv_example.py
     ```

## Open3D

- `open3d_example.py` demonstrates a simple script for 3D reconstruction.
- To run the script, follow these steps:
  1. Ensure the sensor is connected and configured within the same subnet as this PC.
  2. Set the sensor's intrinsic vector file (`iTFS-110.dat` or `iTFS-80.dat`) at **L#126**
  3. Set the sensor’s IP address (`sensor_ip`) at **L#158**.
  4. Modify any parameters you wish to change at **L#176**. Detailed parameter descriptions can be found on the **HYBO GitHub page**.
  5. Run the script using:
     ```sh
     $ python3 open3d_example.py
     ```


## Result

If the scripts run successfully, the following message will appear:

```
Initializing wrapper class...
  Done.
Creating interface...
[MESSAGE] iTFS::LiDAR unique broadcast IP has been set: 192.168.5.255
[MESSAGE] iTFS::LiDAR unique listening IP has been set: 192.168.5.5
[MESSAGE] iTFS::LiDAR is ready.
  Done.
Connecting to sensor...
[MESSAGE] iTFS::LiDAR attempting to connect to the sensor: 192.168.5.116
.........[MESSAGE] iTFS::LiDAR A new device is registered. D#0: 192.168.5.116:4905
[MESSAGE] iTFS::LiDAR successfully connected!
  Done.
[MESSAGE] iTFS::LiDAR cmd_read_info packet was sent.
[MESSAGE] iTFS::LiDAR cmd_read_info packet was sent.
Connected sensor:
  sensor_sn: 628
  capture_mode: 2
  capture_row: 160
  capture_shutter: [400, 80, 16, 0, 8000]
  capture_limit: [200, 200]
  capture_period_us: 100000
  capture_seq: 0
  data_output: 7
  data_baud: 115200
  data_sensor_ip: 192.168.5.116
  data_dest_ip: 192.168.5.5
  data_subnet: 255.255.255.0
  data_gateway: 192.168.5.1
  data_port: 7256
  data_mac_addr: 10:1:0_4:2:116
  sync: 1
  sync_trig_delay_us: 2540
  sync_ill_delay_us: [4760, 4760, 4760, 4580, 4760, 4760, 4760, 7844, 1650, 1650, 1650, 0, 0, 0, 0]
  sync_trig_trim_us: 4
  sync_ill_trim_us: 2
  sync_output_delay_us: 0
  arb: 0
  arb_timeout: 300000
Modified parameters (only changed values are listed):
  capture_mode: 2 --> 1
Starting data stream...
Press **Ctrl+C** to exit.
F# 0
F# 1
F# 2
F# 3
F# 4
...
```


## Troubleshooting

### Failed to initialize the wrapper class:
- Verify the `libilidar` file is in the correct location. Run the script in the same directory as the library (or update `dll_full_path` in the script).
- If necessary, build and use the dll file directly from [ilidar_api_cpp].

### Failed to create the interface:
- Check the PC’s IP configuration and ensure it matches the values in the script.

### Failed to connect to the sensor:
- Ensure both the sensor and PC are in the same subnet.
- If another PC is running this script with the target sensor, the connection cannot be established until the other PC stops running the script.

### Failed to display images or 3D point clouds:
- Verify that OpenCV (or Open3D) is correctly installed. This script was developed under:
  ```
  Python 3.10.11
  opencv-python 4.7.0
  open3d-python 0.19.0
  ```



[ilidar_api_cpp]: https://github.com/ilidar-tof/ilidar_api_cpp