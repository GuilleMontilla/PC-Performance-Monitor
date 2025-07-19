"""
  Script Name : metrics_monitor.py
  Project     : PC Performance Monitor 
  Author      : Guillermo A. Montilla Ramos
  Contact     : guillermomontilla111@outlook.com
  Created     : 2025-07-03
  Updated     : 2025-07-18

  Description:
    This Python script collects real-time system performance data from a Windows system and sends it to an 
    Arduino over serial communication. Uses Win32 API to retrieve the CPU usage and RAM using ctypes. Also uses 
    the LibreHardwareMonitor DLL to retrieve GPU usage, GPU temperature, GPU clock speeds, GPU frequency and VRAM.

  History:
    2025-07-03 – Initial version: defined project scope, decided to use Windows native APIs (kernel32) via ctypes.
    2025-07-05 – Implemented CPU usage via GetSystemTimes; added FILETIME conversion and thread safety with Lock.
    2025-07-08 - Added memory metrics using GlobalMemoryStatusEx with fallback to GlobalMemoryStatus.
    2025-07-10 - Created WindowsNativeMonitor class with CPU, RAM, and system info modules.
    2025-07-12 - Developed TerminalMonitorApp with live console output and user-friendly layout.
    2025-07-14 – Implemented shutdown with Ctrl+C and event signaling; added privilege detection.
    2025-07-16 - Debugged edge cases with 0% CPU time; improved fallback logic and exception handling.
    2025-07-18 – Cleaned up code.
"""

import sys
import os
import ctypes
from ctypes import wintypes, windll, byref, sizeof, Structure, c_uint64
from datetime import datetime
from threading import Event, Lock

# Check if we are running on Windows
if os.name != 'nt':
    print("This script requires Windows to access native APIs")
    sys.exit(1)

# Structures for Windows native APIs
class FILETIME(Structure):
    _fields_ = [
        ("dwLowDateTime", wintypes.DWORD),
        ("dwHighDateTime", wintypes.DWORD)
    ]

# Constants
ERROR_SUCCESS = 0

class WindowsNativeMonitor:
    def __init__(self):
        # Windows native APIs
        self.kernel32 = windll.kernel32
        
        # Variables for CPU calculation with GetSystemTimes
        self.prev_idle_time = None
        self.prev_kernel_time = None
        self.prev_user_time = None
        self._cpu_lock = Lock()  # Lock for thread safety
        
        # Cache for data that doesn't change frequently
        self._cache_duration = 30  # Cache frequency for 30 seconds
        
    def get_cpu_usage_native(self):
        """Gets CPU usage using GetSystemTimes - Thread Safe"""
        with self._cpu_lock:
            try:
                # Define FILETIME structure
                class FILETIME(Structure):
                    _fields_ = [
                        ("dwLowDateTime", wintypes.DWORD),
                        ("dwHighDateTime", wintypes.DWORD),
                    ]
                
                # Variables for the times
                idle_time = FILETIME()
                kernel_time = FILETIME()
                user_time = FILETIME()
                
                # Call GetSystemTimes
                if not self.kernel32.GetSystemTimes(byref(idle_time), byref(kernel_time), byref(user_time)):
                    return 0.0
                
                # Convert FILETIME to 64-bit values
                def filetime_to_int64(ft):
                    return (ft.dwHighDateTime << 32) | ft.dwLowDateTime
                
                current_idle = filetime_to_int64(idle_time)
                current_kernel = filetime_to_int64(kernel_time)
                current_user = filetime_to_int64(user_time)
                
                # If this is the first call, store values and return 0
                if self.prev_idle_time is None:
                    self.prev_idle_time = current_idle
                    self.prev_kernel_time = current_kernel
                    self.prev_user_time = current_user
                    return 0.0
                
                # Calculate differences
                idle_diff = current_idle - self.prev_idle_time
                kernel_diff = current_kernel - self.prev_kernel_time
                user_diff = current_user - self.prev_user_time
                
                # Update previous values
                self.prev_idle_time = current_idle
                self.prev_kernel_time = current_kernel
                self.prev_user_time = current_user
                
                # Calculate CPU usage
                total_system_time = kernel_diff + user_diff
                
                if total_system_time == 0:
                    return 0.0
                
                cpu_usage = ((total_system_time - idle_diff) / total_system_time) * 100
                
                # Ensure it's in valid range
                return max(0.0, min(100.0, cpu_usage))
                
            except Exception as e:
                print(f"Error getting CPU usage with GetSystemTimes: {e}")
                return 0.0
            
    def get_memory_info_native(self):
        """Gets physical memory information using native API with complete structure"""
        try:
            class MEMORYSTATUSEX(Structure):
                """Complete MEMORYSTATUSEX structure according to Windows API"""
                _fields_ = [
                    ("dwLength", wintypes.DWORD),                   # Size of the structure
                    ("dwMemoryLoad", wintypes.DWORD),               # Percentage of memory in use (0-100)
                    ("ullTotalPhys", c_uint64),                     # Total physical memory in bytes
                    ("ullAvailPhys", c_uint64),                     # Available physical memory in bytes
                    ("ullTotalPageFile", c_uint64),                 # Total page file
                    ("ullAvailPageFile", c_uint64),                 # Available page file
                    ("ullTotalVirtual", c_uint64),                  # Total virtual memory
                    ("ullAvailVirtual", c_uint64),                  # Available virtual memory
                    ("ullAvailExtendedVirtual", c_uint64),          # Available extended virtual memory
                ]
            
            memory_status = MEMORYSTATUSEX()
            memory_status.dwLength = sizeof(MEMORYSTATUSEX)  # Required by the API
            
            # Call GlobalMemoryStatusEx
            result = windll.kernel32.GlobalMemoryStatusEx(byref(memory_status))
            
            if result:
                # Only use the three values we need
                total_mb = memory_status.ullTotalPhys / (1024 * 1024)
                available_mb = memory_status.ullAvailPhys / (1024 * 1024)
                used_mb = total_mb - available_mb
                load_percent = memory_status.dwMemoryLoad
                
                return {
                    'ram_load': float(load_percent),       # dwMemoryLoad
                    'ram_used': float(used_mb),           # ullTotalPhys - ullAvailPhys
                    'ram_total': float(total_mb)          # ullTotalPhys
                }
            else:
                # If GlobalMemoryStatusEx fails, use GlobalMemoryStatus as fallback
                print("GlobalMemoryStatusEx failed, using GlobalMemoryStatus...")
                return self.get_memory_info_fallback()
                
        except Exception as e:
            print(f"Error in get_memory_info_native: {e}")
            return self.get_memory_info_fallback()
    
    def get_memory_info_fallback(self):
        """Alternative method using GlobalMemoryStatus (older but functional)"""
        try:
            class MEMORYSTATUS(Structure):
                _fields_ = [
                    ("dwLength", wintypes.DWORD),
                    ("dwMemoryLoad", wintypes.DWORD),
                    ("dwTotalPhys", wintypes.DWORD),
                    ("dwAvailPhys", wintypes.DWORD),
                    ("ullTotalPageFile", c_uint64),                 
                    ("ullAvailPageFile", c_uint64),                 
                    ("ullTotalVirtual", c_uint64),                
                    ("ullAvailVirtual", c_uint64),                  
                    ("ullAvailExtendedVirtual", c_uint64),          
                ]
            
            memory_status = MEMORYSTATUS()
            memory_status.dwLength = sizeof(MEMORYSTATUS)
            
            windll.kernel32.GlobalMemoryStatus(byref(memory_status))
            
            total_mb = memory_status.dwTotalPhys / (1024 * 1024)
            available_mb = memory_status.dwAvailPhys / (1024 * 1024)
            used_mb = total_mb - available_mb
            load_percent = memory_status.dwMemoryLoad
            
            return {
                'ram_load': float(load_percent),
                'ram_used': float(used_mb),
                'ram_total': float(total_mb)
            }
                
        except Exception as e:
            print(f"Error in fallback method: {e}")
        
        # Default values if everything fails
        return {'ram_load': 0.0, 'ram_used': 0.0, 'ram_total': 0.0}
    
    def get_cpu_info_native(self):
        """Gets CPU information using GetSystemTimes (without frequency or clock)"""
        cpu_data = {
            'cpu_load': 0.0,
            'cpu_clock': 0.0,  # Placeholder, will be filled by LHM in the future
            'cpu_freq': 0.0,   # Placeholder, will be filled by LHM in the future
            'cpu_temp': 0.0
        }
        try:
            # CPU usage - fast call
            cpu_data['cpu_load'] = self.get_cpu_usage_native()
        except Exception as e:
            print(f"Error getting CPU info: {e}")
        return cpu_data
    
    def get_cpu_metrics(self):
        """Gets CPU metrics using native APIs (without frequency or clock)"""
        return self.get_cpu_info_native()
    
    def get_gpu_metrics(self):
        """Gets basic GPU metrics using native APIs"""
        gpu_data = {
            'gpu_load': 0.0,
            'gpu_clock': 0.0,
            'gpu_freq': 0.0,
            'gpu_temp': 0.0,
            'vram_used': 0.0,
            'vram_total': 0.0
        }
        
        # For now, just return default values
        # To get real GPU metrics we would need WMI or specific libraries
        return gpu_data
    
    def get_memory_metrics(self):
        """Gets memory metrics using native API"""
        return self.get_memory_info_native()
    
    def get_system_info_native(self):
        """Gets additional system information"""
        try:
            # Processor information
            class SYSTEM_INFO(Structure):
                _fields_ = [
                    ("wProcessorArchitecture", wintypes.WORD),
                    ("wReserved", wintypes.WORD),
                    ("dwPageSize", wintypes.DWORD),
                    ("lpMinimumApplicationAddress", ctypes.c_void_p),
                    ("lpMaximumApplicationAddress", ctypes.c_void_p),
                    ("dwActiveProcessorMask", ctypes.POINTER(wintypes.DWORD)),
                    ("dwNumberOfProcessors", wintypes.DWORD),
                ]
            
            system_info = SYSTEM_INFO()
            windll.kernel32.GetSystemInfo(byref(system_info))
            
            return {
                'processor_count': system_info.dwNumberOfProcessors,
            }
        except:
            return {'processor_count': 1}
    
    def get_all_metrics(self):
        """Gets all system metrics"""
        metrics = {}
        metrics.update(self.get_cpu_metrics())
        metrics.update(self.get_gpu_metrics())
        metrics.update(self.get_memory_metrics())
        metrics['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return metrics
    
    def close(self):
        """Closes connections"""
        pass

class TerminalMonitorApp:
    def __init__(self, update_interval=1.0):
        self.hardware_monitor = WindowsNativeMonitor()
        self.update_interval = update_interval
        self.running = False
        self.stop_event = Event()
        
    def start_monitoring(self):
        """Starts hardware monitoring"""
        self.running = True
        print("Press Ctrl+C to stop")
        
        try:
            while self.running and not self.stop_event.is_set():
                # Get metrics
                metrics = self.hardware_monitor.get_all_metrics()
                
                # Display in console
                self.print_metrics(metrics)
                
                # Wait interval
                self.stop_event.wait(self.update_interval)
                
        except KeyboardInterrupt:
            print("\nStopping monitoring...")
        finally:
            self.stop()
    
    def print_metrics(self, metrics):
        """Prints metrics to console"""
        print(f"\n=== System Metrics - {metrics['timestamp']} ===")
        print(f"CPU: Load: {metrics['cpu_load']:.1f}% | Clock: {metrics['cpu_clock']:.0f}MHz | Freq: {metrics['cpu_freq']:.0f}MHz | Temp: {metrics['cpu_temp']:.1f}°C")
        print(f"GPU: Load: {metrics['gpu_load']:.1f}% | Clock: {metrics['gpu_clock']:.0f}MHz | Freq: {metrics['gpu_freq']:.0f}MHz | Temp: {metrics['gpu_temp']:.1f}°C")
        print(f"VRAM: {metrics['vram_used']:.0f}MB / {metrics['vram_total']:.0f}MB")
        print(f"RAM: Load: {metrics['ram_load']:.1f}% | Used: {metrics['ram_used']:.0f}MB / {metrics['ram_total']:.0f}MB")
        
    def stop(self):
        """Stops monitoring"""
        self.running = False
        self.stop_event.set()
        self.hardware_monitor.close()
        print("Monitoring stopped")

def main():
    """Simplified main function for terminal"""
    # Configuration
    UPDATE_INTERVAL = 1.0  # Update interval
    
    # Startup banner
    print("=" * 60)
    print("   PC Performance Monitor   ")
    print("=" * 60)
    
    # Check privileges
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        status = "✓ Administrator" if is_admin else "⚠ User"
        print(f"Privileges: {status}")
    except:
        print("Privileges: Unknown")
    
    # System information
    try:
        import platform
        print(f"System: {platform.system()} {platform.release()}")
        print(f"Architecture: {platform.machine()}")
    except:
        pass
    
    print(f"Interval: {UPDATE_INTERVAL}s")
    print("-" * 60)
    
    # Create and run monitor
    monitor = TerminalMonitorApp(UPDATE_INTERVAL)
    
    try:
        monitor.start_monitoring()
    except Exception as e:
        print(f"\nCritical error: {e}")
    finally:
        print("\nFinal cleanup...")
        monitor.stop()
        print("Program terminated.")

if __name__ == "__main__":
    main()
