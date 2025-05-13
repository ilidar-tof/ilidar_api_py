import ctypes
import os
import subprocess
import ipaddress
import signal

# V1.0.0 - Initial commit
# V1.0.1 - Added: add handling function for implicit IP address setup of host PC  
ilidar_wrapper_version = "V1.0.1"
CALLBACK_TYPE = ctypes.CFUNCTYPE(None, ctypes.POINTER(ctypes.c_uint16))

# Get IP list
def get_ip_list():
    if os.name == "nt":
        ip_addresses = []
        
        # Use ipconfig to get all IPs
        result = subprocess.run(['ipconfig'], stdout=subprocess.PIPE, text=True)
        
        # Parse the output to find IP addresses
        lines = result.stdout.splitlines()
        for line in lines:
            if 'IPv4' in line:
                ip = line.split(':')[1].replace(' ', '')
                if ip != '127.0.0.1' and ip not in ip_addresses:
                    ip_addresses.append(ip)
        
        return ip_addresses
    else:
        ip_addresses = []

        # Additional IPs using ifconfig or ip command
        try:
            # Use `ifconfig` (for Unix-based systems)
            result = subprocess.run(['ifconfig'], stdout=subprocess.PIPE, text=True)
        except FileNotFoundError:
            # Use `ip` (for Linux systems that don’t have ifconfig)
            result = subprocess.run(['ip', 'addr'], stdout=subprocess.PIPE, text=True)

        # Parse the output to find IP addresses
        lines = result.stdout.splitlines()
        for line in lines:
            if 'inet ' in line:
                ip = line.strip().split()[1].split('/')[0]
                if ip != '127.0.0.1' and ip not in ip_addresses:
                    ip_addresses.append(ip)
        
        return ip_addresses

# IP check
def is_ip(str):
    try:
        ipaddress.IPv4Address(str)
        return True
    except ValueError:
        return False

# Get subnet mask
def get_subnet_mask(ip):
    if os.name == "nt":
        # Use ipconfig to get all IPs
        result = subprocess.run(['ipconfig'], stdout=subprocess.PIPE, text=True)
        
        # Parse the output to find IP addresses
        lines = result.stdout.splitlines()
        found_idx = -1
        for line_idx, line in enumerate(lines, start=1):
            if 'IPv4' in line:
                host_ip = line.split(':')[1].replace(' ', '')
                if ip == host_ip:
                    found_idx = line_idx
            
            if line_idx == found_idx + 1:
                host_subnet = line.split(':')[1].replace(' ', '')
                return host_subnet
        
        return ''
    else:
        # Additional IPs using ifconfig or ip command
        try:
            # Use `ifconfig` (for Unix-based systems)
            result = subprocess.run(['ifconfig'], stdout=subprocess.PIPE, text=True)
        except FileNotFoundError:
            # Use `ip` (for Linux systems that don’t have ifconfig)
            result = subprocess.run(['ip', 'addr'], stdout=subprocess.PIPE, text=True)

        # Parse the output to find IP addresses
        lines = result.stdout.splitlines()
        for line_idx, line in enumerate(lines, start=1):
            if 'inet' in line:
                host_ip = line.strip().split()[1].split('/')[0]
                host_subnet = line.strip().split()[3].split('/')[0]
                if ip == host_ip:
                    return host_subnet

        return ''

# Get broadcast ip
def get_broadcast_ip(ip, subnet):
    # Convert IP and subnet mask to IPv4 objects
    network = ipaddress.IPv4Network(f'{ip}/{subnet}', strict=False)
    
    # Get the broadcast address from the network object
    broadcast_address = network.broadcast_address
    return str(broadcast_address)

# Parse ip string to array
def get_ip_array(ip_str):
    ip_parts = [int(x) for x in ip_str.split('.')]
    return (ctypes.c_uint8 * 4)(*ip_parts)

# Encode function of info_2 packet for F/W V1.5.0+
def encode_info_v2(src):
    dst = bytearray(166)  # 166-byte array

    # Sensor serial number (16-bit)
    dst[0] = src['sensor_sn'] % 256
    dst[1] = src['sensor_sn'] // 256

    # Fill bytes 2 to 68 with 0 (Read only in original code)
    for i in range(2, 70):
        dst[i] = 0

    # Capture mode and capture row (8-bit values)
    dst[71] = src['capture_mode']
    dst[72] = src['capture_row']

    # Capture shutter (16-bit values, total 5 elements)
    for i in range(5):
        dst[73 + i * 2] = (src['capture_shutter'][i] >> 0) & 0xFF
        dst[74 + i * 2] = (src['capture_shutter'][i] >> 8) & 0xFF

    # Capture limit (16-bit values, total 2 elements)
    dst[83] = (src['capture_limit'][0] >> 0) & 0xFF
    dst[84] = (src['capture_limit'][0] >> 8) & 0xFF
    dst[85] = (src['capture_limit'][1] >> 0) & 0xFF
    dst[86] = (src['capture_limit'][1] >> 8) & 0xFF

    # Capture period (32-bit value)
    dst[87] = (src['capture_period_us'] >> 0) & 0xFF
    dst[88] = (src['capture_period_us'] >> 8) & 0xFF
    dst[89] = (src['capture_period_us'] >> 16) & 0xFF
    dst[90] = (src['capture_period_us'] >> 24) & 0xFF

    # Capture sequence (8-bit value)
    dst[91] = src['capture_seq']

    # Data output and baud rate (32-bit value)
    dst[92] = src['data_output']
    dst[93] = (src['data_baud'] >> 0) & 0xFF
    dst[94] = (src['data_baud'] >> 8) & 0xFF
    dst[95] = (src['data_baud'] >> 16) & 0xFF
    dst[96] = (src['data_baud'] >> 24) & 0xFF

    # Sensor and destination IP addresses (each 4 bytes)
    dst[97:101] = src['data_sensor_ip']
    dst[101:105] = src['data_dest_ip']
    dst[105:109] = src['data_subnet']
    dst[109:113] = src['data_gateway']

    # Data port (16-bit value)
    dst[113] = (src['data_port'] >> 0) & 0xFF
    dst[114] = (src['data_port'] >> 8) & 0xFF

    # MAC address (6 bytes)
    dst[115:121] = src['data_mac_addr']

    # Sync configuration
    dst[121] = src['sync']
    dst[122] = (src['sync_trig_delay_us'] >> 0) & 0xFF
    dst[123] = (src['sync_trig_delay_us'] >> 8) & 0xFF
    dst[124] = (src['sync_trig_delay_us'] >> 16) & 0xFF
    dst[125] = (src['sync_trig_delay_us'] >> 24) & 0xFF

    # Sync illumination delay (16-bit values, total 15 elements)
    for i in range(15):
        dst[126 + i * 2] = (src['sync_ill_delay_us'][i] >> 0) & 0xFF
        dst[127 + i * 2] = (src['sync_ill_delay_us'][i] >> 8) & 0xFF

    # Sync trimmer values (8-bit)
    dst[156] = src['sync_trig_trim_us']
    dst[157] = src['sync_ill_trim_us']

    # Sync output delay (16-bit)
    dst[158] = (src['sync_output_delay_us'] >> 0) & 0xFF
    dst[159] = (src['sync_output_delay_us'] >> 8) & 0xFF

    # Arbitration settings (8-bit and 32-bit)
    dst[160] = src['arb']
    dst[161] = (src['arb_timeout'] >> 0) & 0xFF
    dst[162] = (src['arb_timeout'] >> 8) & 0xFF
    dst[163] = (src['arb_timeout'] >> 16) & 0xFF
    dst[164] = (src['arb_timeout'] >> 24) & 0xFF

    # Additional flag
    dst[165] = 0  # This flag is not written in the info packet

    return dst

# Decode function of info_v2 packet for F/W V1.5.0+
def decode_info_v2(src):
    # Initialize the output dictionary
    dst = {}
    dst['ilidar_version'] = "1.5.X"

    # Sensor serial number (16-bit)
    dst['sensor_sn'] = (src[1] << 8) | src[0]

    # Sensor HW ID (30 bytes)
    dst['sensor_hw_id'] = src[2:32]

    # Sensor FW version (3 bytes)
    dst['sensor_fw_ver'] = src[32:35]

    # Sensor FW date (12 bytes)
    dst['sensor_fw_date'] = src[35:47]

    # Sensor FW time (9 bytes)
    dst['sensor_fw_time'] = src[47:56]

    # Sensor calibration ID (32-bit)
    dst['sensor_calib_id'] = (src[59] << 24) | (src[58] << 16) | (src[57] << 8) | src[56]

    # Sensor firmware versions (3 bytes each)
    dst['sensor_fw0_ver'] = src[60:63]
    dst['sensor_fw1_ver'] = src[63:66]
    dst['sensor_fw2_ver'] = src[66:69]

    # Sensor model and boot control (8-bit values)
    dst['sensor_model_id'] = src[69]
    dst['sensor_boot_ctrl'] = src[70]

    # Capture mode and row (8-bit)
    dst['capture_mode'] = src[71]
    dst['capture_row'] = src[72]

    # Capture shutter (16-bit values, total 5 elements)
    dst['capture_shutter'] = [
        (src[74] << 8) | src[73],
        (src[76] << 8) | src[75],
        (src[78] << 8) | src[77],
        (src[80] << 8) | src[79],
        (src[82] << 8) | src[81]
    ]

    # Capture limit (16-bit values, total 2 elements)
    dst['capture_limit'] = [
        (src[84] << 8) | src[83],
        (src[86] << 8) | src[85]
    ]

    # Capture period (32-bit value)
    dst['capture_period_us'] = (src[90] << 24) | (src[89] << 16) | (src[88] << 8) | src[87]

    # Capture sequence (8-bit value)
    dst['capture_seq'] = src[91]

    # Data output (8-bit value)
    dst['data_output'] = src[92]

    # Data baud rate (32-bit value)
    dst['data_baud'] = (src[96] << 24) | (src[95] << 16) | (src[94] << 8) | src[93]

    # Sensor and destination IP addresses (4 bytes each)
    dst['data_sensor_ip'] = src[97:101]
    dst['data_dest_ip'] = src[101:105]
    dst['data_subnet'] = src[105:109]
    dst['data_gateway'] = src[109:113]

    # Data port (16-bit value)
    dst['data_port'] = (src[114] << 8) | src[113]

    # Data MAC address (6 bytes)
    dst['data_mac_addr'] = src[115:121]

    # Sync settings (8-bit and 32-bit values)
    dst['sync'] = src[121]
    dst['sync_trig_delay_us'] = (src[125] << 24) | (src[124] << 16) | (src[123] << 8) | src[122]

    # Sync illumination delay (16-bit values, total 15 elements)
    dst['sync_ill_delay_us'] = [
        (src[127] << 8) | src[126],
        (src[129] << 8) | src[128],
        (src[131] << 8) | src[130],
        (src[133] << 8) | src[132],
        (src[135] << 8) | src[134],
        (src[137] << 8) | src[136],
        (src[139] << 8) | src[138],
        (src[141] << 8) | src[140],
        (src[143] << 8) | src[142],
        (src[145] << 8) | src[144],
        (src[147] << 8) | src[146],
        (src[149] << 8) | src[148],
        (src[151] << 8) | src[150],
        (src[153] << 8) | src[152],
        (src[155] << 8) | src[154]
    ]

    # Sync trim and delay (8-bit and 16-bit values)
    dst['sync_trig_trim_us'] = src[156]
    dst['sync_ill_trim_us'] = src[157]
    dst['sync_output_delay_us'] = (src[159] << 8) | src[158]

    # Arbitration (8-bit and 32-bit values)
    dst['arb'] = src[160]
    dst['arb_timeout'] = (src[164] << 24) | (src[163] << 16) | (src[162] << 8) | src[161]

    # Lock (8-bit value)
    dst['lock'] = src[165]

    return dst

# Print function of info_v2 packet for F/W V1.5.0+
def print_info_v2(src):
    print(f"  sensor_sn: {src['sensor_sn']}")
    print(f"  capture_mode: {src['capture_mode']}")
    print(f"  capture_row: {src['capture_row']}")
    print(f"  capture_shutter: {src['capture_shutter']}")
    print(f"  capture_limit: {src['capture_limit']}")
    print(f"  capture_period_us: {src['capture_period_us']}")
    print(f"  capture_seq: {src['capture_seq']}")
    print(f"  data_output: {src['data_output']}")
    print(f"  data_baud: {src['data_baud']}")
    data_sensor_ip = src['data_sensor_ip']
    print(f"  data_sensor_ip: {data_sensor_ip[0]}.{data_sensor_ip[1]}.{data_sensor_ip[2]}.{data_sensor_ip[3]}")
    data_dest_ip = src['data_dest_ip']
    print(f"  data_dest_ip: {data_dest_ip[0]}.{data_dest_ip[1]}.{data_dest_ip[2]}.{data_dest_ip[3]}")
    data_subnet = src['data_subnet']
    print(f"  data_subnet: {data_subnet[0]}.{data_subnet[1]}.{data_subnet[2]}.{data_subnet[3]}")
    data_gateway = src['data_gateway']
    print(f"  data_gateway: {data_gateway[0]}.{data_gateway[1]}.{data_gateway[2]}.{data_gateway[3]}")
    print(f"  data_port: {src['data_port']}")
    data_mac_addr = src['data_mac_addr']
    print(f"  data_mac_addr: {data_mac_addr[0]}:{data_mac_addr[1]}:{data_mac_addr[2]}_{data_mac_addr[3]}:{data_mac_addr[4]}:{data_mac_addr[5]}")
    print(f"  sync: {src['sync']}")
    print(f"  sync_trig_delay_us: {src['sync_trig_delay_us']}")
    print(f"  sync_ill_delay_us: {src['sync_ill_delay_us']}")
    print(f"  sync_trig_trim_us: {src['sync_trig_trim_us']}")
    print(f"  sync_ill_trim_us: {src['sync_ill_trim_us']}")
    print(f"  sync_output_delay_us: {src['sync_output_delay_us']}")
    print(f"  arb: {src['arb']}")
    print(f"  arb_timeout: {src['arb_timeout']}")

# Print function of changed parameters for for F/W V1.4.0+
def print_diff_info_v2(pri, post):
    diff = 0

    if pri['capture_mode'] != post['capture_mode']:
        diff += 1
        print(f"  capture_mode: {pri['capture_mode']}")
        print(f"            --> {post['capture_mode']}")
        
    if pri['capture_row'] != post['capture_row']:
        diff += 1
        print(f"  capture_row: {pri['capture_row']}")
        print(f"           --> {post['capture_row']}")
        
    if pri['capture_shutter'] != post['capture_shutter']:
        diff += 1
        print(f"  capture_shutter: {pri['capture_shutter']}")
        print(f"               --> {post['capture_shutter']}")
        
    if pri['capture_limit'] != post['capture_limit']:
        diff += 1
        print(f"  capture_limit: {pri['capture_limit']}")
        print(f"             --> {post['capture_limit']}")
        
    if pri['capture_period_us'] != post['capture_period_us']:
        diff += 1
        print(f"  capture_period_us: {pri['capture_period_us']}")
        print(f"                 --> {post['capture_period_us']}")
        
    if pri['capture_seq'] != post['capture_seq']:
        diff += 1
        print(f"  capture_seq: {pri['capture_seq']}")
        print(f"           --> {post['capture_seq']}")
        
    if pri['data_output'] != post['data_output']:
        diff += 1
        print(f"  data_output: {pri['data_output']}")
        print(f"           --> {post['data_output']}")
        
    if pri['data_baud'] != post['data_baud']:
        diff += 1
        print(f"  data_baud: {pri['data_baud']}")
        print(f"         --> {post['data_baud']}")
        
    if pri['data_sensor_ip'] != bytearray(post['data_sensor_ip']):
        diff += 1
        arr = pri['data_sensor_ip']
        print(f"  data_sensor_ip: {arr[0]}.{arr[1]}.{arr[2]}.{arr[3]}")
        arr = post['data_sensor_ip']
        print(f"              --> {arr[0]}.{arr[1]}.{arr[2]}.{arr[3]}")
        
    if pri['data_dest_ip'] != bytearray(post['data_dest_ip']):
        diff += 1
        arr = pri['data_dest_ip']
        print(f"  data_dest_ip: {arr[0]}.{arr[1]}.{arr[2]}.{arr[3]}")
        arr = post['data_dest_ip']
        print(f"            --> {arr[0]}.{arr[1]}.{arr[2]}.{arr[3]}")
        
    if pri['data_subnet'] != bytearray(post['data_subnet']):
        diff += 1
        arr = pri['data_subnet']
        print(f"  data_subnet: {arr[0]}.{arr[1]}.{arr[2]}.{arr[3]}")
        arr = post['data_subnet']
        print(f"           --> {arr[0]}.{arr[1]}.{arr[2]}.{arr[3]}")
        
    if pri['data_gateway'] != bytearray(post['data_gateway']):
        diff += 1
        arr = pri['data_gateway']
        print(f"  data_gateway: {arr[0]}.{arr[1]}.{arr[2]}.{arr[3]}")
        arr = post['data_gateway']
        print(f"            --> {arr[0]}.{arr[1]}.{arr[2]}.{arr[3]}")
        
    if pri['data_port'] != post['data_port']:
        diff += 1
        print(f"  data_port: {pri['data_port']}")
        print(f"         --> {post['data_port']}")
        
    if pri['data_mac_addr'] != bytearray(post['data_mac_addr']):
        diff += 1
        arr = pri['data_mac_addr']
        print(f"  data_mac_addr: {arr[0]}:{arr[1]}:{arr[2]}_{arr[3]}:{arr[4]}:{arr[5]}")
        arr = post['data_mac_addr']
        print(f"             --> {arr[0]}:{arr[1]}:{arr[2]}_{arr[3]}:{arr[4]}:{arr[5]}")
        
    if pri['sync'] != post['sync']:
        diff += 1
        print(f"  sync: {pri['sync']}")
        print(f"    --> {post['sync']}")
        
    if pri['sync_trig_delay_us'] != post['sync_trig_delay_us']:
        diff += 1
        print(f"  sync_trig_delay_us: {pri['sync_trig_delay_us']}")
        print(f"                  --> {post['sync_trig_delay_us']}")
        
    if pri['sync_ill_delay_us'] != post['sync_ill_delay_us']:
        diff += 1
        print(f"  sync_ill_delay_us: {pri['sync_ill_delay_us']}")
        print(f"                 --> {post['sync_ill_delay_us']}")
        
    if pri['sync_trig_trim_us'] != post['sync_trig_trim_us']:
        diff += 1
        print(f"  sync_trig_trim_us: {pri['sync_trig_trim_us']}")
        print(f"                 --> {post['sync_trig_trim_us']}")
        
    if pri['sync_ill_trim_us'] != post['sync_ill_trim_us']:
        diff += 1
        print(f"  sync_ill_trim_us: {pri['sync_ill_trim_us']}")
        print(f"                --> {post['sync_ill_trim_us']}")
        
    if pri['sync_output_delay_us'] != post['sync_output_delay_us']:
        diff += 1
        print(f"  sync_output_delay_us: {pri['sync_output_delay_us']}")
        print(f"                    --> {post['sync_output_delay_us']}")
        
    if pri['arb'] != post['arb']:
        diff += 1
        print(f"  arb: {pri['arb']}")
        print(f"   --> {post['arb']}")
        
    if pri['arb_timeout'] != post['arb_timeout']:
        diff += 1
        print(f"  arb_timeout: {pri['arb_timeout']}")
        print(f"           --> {post['arb_timeout']}")

    return diff

# Main class starts here
class iTFS:
    def __init__(self, dll_path):
        # Load the DLL
        self.ilidar_wrapper = ctypes.CDLL(dll_path)
        self.ilidar_clean = False

        # Set function prototypes
        self.ilidar_wrapper.ilidar_init.argtypes = [ctypes.POINTER(ctypes.c_uint16), CALLBACK_TYPE]
        self.ilidar_wrapper.ilidar_init.restype = ctypes.c_int

        self.ilidar_wrapper.ilidar_create.argtypes = [ctypes.POINTER(ctypes.c_uint8), ctypes.POINTER(ctypes.c_uint8), ctypes.c_uint16]
        self.ilidar_wrapper.ilidar_create.restype = ctypes.c_int

        self.ilidar_wrapper.ilidar_destroy.argtypes = []
        self.ilidar_wrapper.ilidar_destroy.restype = ctypes.c_int

        self.ilidar_wrapper.ilidar_connect.argtypes = [ctypes.POINTER(ctypes.c_uint8), ctypes.c_uint16]
        self.ilidar_wrapper.ilidar_connect.restype = ctypes.c_int

        self.ilidar_wrapper.ilidar_disconnect.argtypes = []
        self.ilidar_wrapper.ilidar_disconnect.restype = ctypes.c_int

        self.ilidar_wrapper.ilidar_get_params.argtypes = [ctypes.POINTER(ctypes.c_uint8)]
        self.ilidar_wrapper.ilidar_get_params.restype = ctypes.c_int

        self.ilidar_wrapper.ilidar_set_params.argtypes = [ctypes.POINTER(ctypes.c_uint8)]
        self.ilidar_wrapper.ilidar_set_params.restype = ctypes.c_int

        self.ilidar_wrapper.ilidar_store.argtypes = []
        self.ilidar_wrapper.ilidar_store.restype = ctypes.c_int

        self.ilidar_wrapper.ilidar_lock.argtypes = []
        self.ilidar_wrapper.ilidar_lock.restype = ctypes.c_int

        self.ilidar_wrapper.ilidar_unlock.argtypes = []
        self.ilidar_wrapper.ilidar_unlock.restype = ctypes.c_int

        self.ilidar_wrapper.ilidar_start.argtypes = []
        self.ilidar_wrapper.ilidar_start.restype = ctypes.c_int

        self.ilidar_wrapper.ilidar_stop.argtypes = []
        self.ilidar_wrapper.ilidar_stop.restype = ctypes.c_int

        self.iscreated = False
        
    def version(self):
        return ilidar_wrapper_version

    def init(self, img_ptr, callback):
        print("Initializing wrapper class...")
        result = self.ilidar_wrapper.ilidar_init(img_ptr, callback)
        if result == 0:
            print("  Done.")
            return True
        else:
            print("Fail to initialize the wrapper class. Check the arguments")
            return False

    def create(self, dest_ip, dest_port):
        print("Creating interface...")
        host_ip_list = get_ip_list()
        if len(host_ip_list) > 0:
            if dest_ip is None:
                listening_ip = host_ip_list[0]
            else:
                if dest_ip in host_ip_list:
                    listening_ip = dest_ip
                else:
                    print("Invalid network setup. Check the available IP list of this PC:")
                    print(host_ip_list)
                    return False
                
            if dest_port is None:
                listening_port = 7256
            else:
                listening_port = dest_port

            listening_port = 7256
            listening_subnet = get_subnet_mask(listening_ip)
            broadcast_ip = get_broadcast_ip(listening_ip, listening_subnet)

            result = self.ilidar_wrapper.ilidar_create(get_ip_array(broadcast_ip), get_ip_array(listening_ip), ctypes.c_uint16(listening_port))
            if result != 0:
                print("Fail to create the sensor interface. Check the IP setup of this PC.")
                return False
            print("  Done.")
            self.iscreated = True
            return True

        else:
            print('Invalid network setup. There are no connections with IPv4...')
            return False
        
    def destroy(self):
        print("Destroying interface...")
        self.ilidar_wrapper.ilidar_destroy()
        self.ilidar_clean = True
        print("  Done.")
        
    def isclean(self):
        return self.ilidar_clean

    def connect(self, sensor_ip, sensor_port):
        if self.iscreated == False:
            print("Incoming IP adress is not set. Try to creating interface with default values...")
            host_ip_list = get_ip_list()
            dest_ip = [ip for ip in host_ip_list if ipaddress.ip_address(sensor_ip) in ipaddress.ip_network(ip + "/" + get_subnet_mask(ip), strict=False)]

            if len(dest_ip) > 0:
                listening_ip = dest_ip[0]
                listening_port = 7256

                listening_subnet = get_subnet_mask(listening_ip)
                broadcast_ip = get_broadcast_ip(listening_ip, listening_subnet)

                result = self.ilidar_wrapper.ilidar_create(get_ip_array(broadcast_ip), get_ip_array(listening_ip), ctypes.c_uint16(listening_port))
                if result != 0:
                    print("Fail to create the sensor interface. Check the IP setup of this PC.")
                    return False
                print("  Done.")
                self.iscreated = True

            else:
                print('Invalid network setup. There are no connections with IPv4...')
                return False

        print("Connecting to sensor...")
        result = self.ilidar_wrapper.ilidar_connect(get_ip_array(sensor_ip), ctypes.c_uint16(sensor_port))
        if result != 0:
            print("Fail to connect to the sensor. The sensor may be used by other users.")
            return False
        print("  Done.")
        return True

    def disconnect(self):
        print("Disconnecting the sensor...")
        self.ilidar_wrapper.ilidar_disconnect()
        print("  Done.")

    def get_params(self):
        output_buffer_ctypes = (ctypes.c_uint8 * 166)()
        result = self.ilidar_wrapper.ilidar_get_params(output_buffer_ctypes)
        if result != 0:
            print("Fail to get parameters from the sensor. Check the connection.")
            return None
        
        params = decode_info_v2(bytearray(output_buffer_ctypes))
        return params
        
    def set_params(self, params):
        input_buffer = encode_info_v2(params)
        input_buffer_ctypes = (ctypes.c_uint8 * 166).from_buffer_copy(input_buffer)
        result = self.ilidar_wrapper.ilidar_set_params(input_buffer_ctypes)
        if result != 0:
            print("Fail to set parameters from the sensor. Check the connection.")
            return False
        return True
    
    def print_params(self, params):
        print_info_v2(params)

    def print_diff(self, pri, post):
        print_diff_info_v2(pri, post)

    def store(self):
        self.ilidar_wrapper.ilidar_store()

    def lock(self):
        self.ilidar_wrapper.ilidar_lock()

    def unlock(self):
        self.ilidar_wrapper.ilidar_unlock()

    def start(self):
        self.ilidar_wrapper.ilidar_start()

    def stop(self):
        self.ilidar_wrapper.ilidar_stop()
    