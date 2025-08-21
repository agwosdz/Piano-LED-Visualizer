#!/usr/bin/env python3
"""
USB MIDI Gadget Mode Implementation for Piano LED Visualizer

This module enables the Raspberry Pi to act as a USB MIDI device when connected
to a computer via USB. It handles the setup and management of USB gadget mode
using the g_midi kernel module and configfs.

Author: Piano LED Visualizer Team
License: MIT
"""

import os
import subprocess
import time
import threading
from pathlib import Path
from lib.log_setup import logger
import mido
from collections import deque

class USBMIDIGadget:
    def __init__(self, usersettings, midi_event_processor=None):
        self.usersettings = usersettings
        self.midi_event_processor = midi_event_processor
        self.gadget_name = "piano_led_midi"
        self.configfs_path = Path("/sys/kernel/config/usb_gadget")
        self.gadget_path = self.configfs_path / self.gadget_name
        self.is_enabled = False
        self.midi_device_path = None
        self.midi_input = None
        self.midi_output = None
        self.message_queue = deque()
        self.running = False
        self.worker_thread = None
        
        # USB device descriptor values
        self.vendor_id = "0x1d6b"  # Linux Foundation
        self.product_id = "0x0104"  # Multifunction Composite Gadget
        self.device_class = "0x00"
        self.device_subclass = "0x00"
        self.device_protocol = "0x00"
        self.max_packet_size = "64"
        
        # Device strings
        self.manufacturer = "Piano LED Visualizer"
        self.product = "Piano LED MIDI Device"
        self.serial_number = "123456789"
        
    def check_prerequisites(self):
        """Check if the system supports USB gadget mode"""
        try:
            import platform
            
            # Check if we're running on Windows
            if platform.system() == 'Windows':
                logger.warning("USB gadget mode is only supported on Raspberry Pi hardware, not Windows")
                return False
            
            # Check if we're running on a Raspberry Pi
            with open('/proc/cpuinfo', 'r') as f:
                cpuinfo = f.read()
                if 'BCM' not in cpuinfo:
                    logger.warning("USB gadget mode is only supported on Raspberry Pi")
                    return False
            
            # Check if configfs is mounted
            if not self.configfs_path.exists():
                logger.error("configfs not found. Please ensure it's mounted at /sys/kernel/config")
                return False
                
            # Check if dwc2 overlay is enabled
            result = subprocess.run(['lsmod'], capture_output=True, text=True)
            if 'dwc2' not in result.stdout:
                logger.warning("dwc2 module not loaded. USB gadget mode may not work properly.")
                
            return True
            
        except Exception as e:
            logger.error(f"Error checking prerequisites: {e}")
            return False
    
    def setup_gadget(self):
        """Setup USB MIDI gadget using configfs"""
        try:
            if not self.check_prerequisites():
                return False
                
            # Remove existing gadget if it exists
            self.cleanup_gadget()
            
            logger.info("Setting up USB MIDI gadget...")
            
            # Create gadget directory
            self.gadget_path.mkdir(exist_ok=True)
            
            # Set device descriptor
            self._write_file(self.gadget_path / "idVendor", self.vendor_id)
            self._write_file(self.gadget_path / "idProduct", self.product_id)
            self._write_file(self.gadget_path / "bcdDevice", "0x0100")
            self._write_file(self.gadget_path / "bcdUSB", "0x0200")
            self._write_file(self.gadget_path / "bDeviceClass", self.device_class)
            self._write_file(self.gadget_path / "bDeviceSubClass", self.device_subclass)
            self._write_file(self.gadget_path / "bDeviceProtocol", self.device_protocol)
            self._write_file(self.gadget_path / "bMaxPacketSize0", self.max_packet_size)
            
            # Create strings
            strings_dir = self.gadget_path / "strings" / "0x409"
            strings_dir.mkdir(parents=True, exist_ok=True)
            self._write_file(strings_dir / "manufacturer", self.manufacturer)
            self._write_file(strings_dir / "product", self.product)
            self._write_file(strings_dir / "serialnumber", self.serial_number)
            
            # Create MIDI function
            functions_dir = self.gadget_path / "functions"
            functions_dir.mkdir(exist_ok=True)
            midi_function = functions_dir / "midi.usb0"
            midi_function.mkdir(exist_ok=True)
            
            # Configure MIDI function
            self._write_file(midi_function / "in_ports", "1")
            self._write_file(midi_function / "out_ports", "1")
            self._write_file(midi_function / "buflen", "128")
            self._write_file(midi_function / "qlen", "32")
            
            # Create configuration
            configs_dir = self.gadget_path / "configs"
            configs_dir.mkdir(exist_ok=True)
            config_dir = configs_dir / "c.1"
            config_dir.mkdir(exist_ok=True)
            
            # Set configuration attributes
            self._write_file(config_dir / "MaxPower", "250")
            self._write_file(config_dir / "bmAttributes", "0x80")
            
            # Create configuration strings
            config_strings = config_dir / "strings" / "0x409"
            config_strings.mkdir(parents=True, exist_ok=True)
            self._write_file(config_strings / "configuration", "MIDI Configuration")
            
            # Link function to configuration
            link_path = config_dir / "midi.usb0"
            if not link_path.exists():
                link_path.symlink_to(midi_function)
            
            logger.info("USB MIDI gadget setup completed")
            return True
            
        except Exception as e:
            logger.error(f"Error setting up USB MIDI gadget: {e}")
            return False
    
    def enable_gadget(self):
        """Enable the USB MIDI gadget"""
        try:
            if not self.gadget_path.exists():
                if not self.setup_gadget():
                    return False
            
            # Find UDC (USB Device Controller)
            udc_path = Path("/sys/class/udc")
            if not udc_path.exists():
                logger.error("No USB Device Controller found")
                return False
                
            udc_devices = list(udc_path.iterdir())
            if not udc_devices:
                logger.error("No UDC devices available")
                return False
                
            udc_name = udc_devices[0].name
            logger.info(f"Using UDC: {udc_name}")
            
            # Enable gadget
            self._write_file(self.gadget_path / "UDC", udc_name)
            
            # Wait for device to be created
            time.sleep(2)
            
            # Find the MIDI device
            self._find_midi_device()
            
            if self.midi_device_path:
                self.is_enabled = True
                logger.info(f"USB MIDI gadget enabled successfully. Device: {self.midi_device_path}")
                return True
            else:
                logger.error("MIDI device not found after enabling gadget")
                return False
                
        except Exception as e:
            logger.error(f"Error enabling USB MIDI gadget: {e}")
            return False
    
    def disable_gadget(self):
        """Disable the USB MIDI gadget"""
        try:
            if self.gadget_path.exists():
                # Disable gadget
                self._write_file(self.gadget_path / "UDC", "")
                
            self.is_enabled = False
            self.midi_device_path = None
            
            if self.midi_input:
                self.midi_input.close()
                self.midi_input = None
                
            if self.midi_output:
                self.midi_output.close()
                self.midi_output = None
                
            logger.info("USB MIDI gadget disabled")
            return True
            
        except Exception as e:
            logger.error(f"Error disabling USB MIDI gadget: {e}")
            return False
    
    def cleanup_gadget(self):
        """Remove gadget configuration"""
        try:
            if self.is_enabled:
                self.disable_gadget()
                
            if self.gadget_path.exists():
                # Remove symlinks first
                config_dir = self.gadget_path / "configs" / "c.1"
                if config_dir.exists():
                    for item in config_dir.iterdir():
                        if item.is_symlink():
                            item.unlink()
                
                # Remove directories in reverse order
                subprocess.run(["sudo", "rm", "-rf", str(self.gadget_path)], 
                             capture_output=True)
                
            logger.info("USB MIDI gadget cleanup completed")
            
        except Exception as e:
            logger.error(f"Error cleaning up USB MIDI gadget: {e}")
    
    def _write_file(self, path, content):
        """Write content to a file with sudo if needed"""
        try:
            with open(path, 'w') as f:
                f.write(str(content))
        except PermissionError:
            # Try with sudo
            subprocess.run(["sudo", "sh", "-c", f"echo '{content}' > {path}"], 
                         check=True)
    
    def _find_midi_device(self):
        """Find the created MIDI device"""
        try:
            # Look for MIDI devices
            for i in range(10):  # Try for 10 seconds
                midi_devices = mido.get_input_names()
                for device in midi_devices:
                    if "f_midi" in device.lower() or "gadget" in device.lower():
                        self.midi_device_path = device
                        return
                time.sleep(1)
                
        except Exception as e:
            logger.error(f"Error finding MIDI device: {e}")
    
    def start_midi_processing(self):
        """Start MIDI message processing"""
        if not self.is_enabled or not self.midi_device_path:
            logger.error("USB MIDI gadget not enabled")
            return False
            
        try:
            # Open MIDI ports
            self.midi_input = mido.open_input(self.midi_device_path, 
                                            callback=self._midi_callback)
            self.midi_output = mido.open_output(self.midi_device_path)
            
            self.running = True
            self.worker_thread = threading.Thread(target=self._process_messages)
            self.worker_thread.daemon = True
            self.worker_thread.start()
            
            logger.info("MIDI processing started")
            return True
            
        except Exception as e:
            logger.error(f"Error starting MIDI processing: {e}")
            return False
    
    def stop_midi_processing(self):
        """Stop MIDI message processing"""
        self.running = False
        
        if self.worker_thread:
            self.worker_thread.join(timeout=1)
            
        if self.midi_input:
            self.midi_input.close()
            self.midi_input = None
            
        if self.midi_output:
            self.midi_output.close()
            self.midi_output = None
            
        logger.info("MIDI processing stopped")
    
    def _midi_callback(self, message):
        """Handle incoming MIDI messages from USB"""
        try:
            # Add timestamp and queue message
            timestamped_message = (message, time.perf_counter())
            self.message_queue.append(timestamped_message)
            
            # Forward to existing MIDI event processor if available
            if self.midi_event_processor:
                self.midi_event_processor.process_message(message)
                
        except Exception as e:
            logger.error(f"Error in MIDI callback: {e}")
    
    def _process_messages(self):
        """Process queued MIDI messages"""
        while self.running:
            try:
                if self.message_queue:
                    message, timestamp = self.message_queue.popleft()
                    # Additional processing can be added here
                    
                time.sleep(0.001)  # Small delay to prevent busy waiting
                
            except Exception as e:
                logger.error(f"Error processing MIDI messages: {e}")
    
    def send_midi_message(self, message):
        """Send MIDI message to connected computer"""
        if self.midi_output and self.is_enabled:
            try:
                self.midi_output.send(message)
                return True
            except Exception as e:
                logger.error(f"Error sending MIDI message: {e}")
                return False
        return False
    
    def get_status(self):
        """Get current status of USB MIDI gadget"""
        return {
            "enabled": self.is_enabled,
            "device_path": self.midi_device_path,
            "running": self.running,
            "queue_size": len(self.message_queue)
        }
    
    def toggle_mode(self):
        """Toggle USB MIDI gadget mode on/off"""
        if self.is_enabled:
            self.stop_midi_processing()
            return self.disable_gadget()
        else:
            if self.enable_gadget():
                return self.start_midi_processing()
            return False