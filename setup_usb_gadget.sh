#!/bin/bash

# USB MIDI Gadget Setup Script for Piano LED Visualizer
# This script configures the Raspberry Pi to support USB gadget mode
# for acting as a MIDI device when connected to a computer via USB.

set -e

echo "========================================"
echo "Piano LED Visualizer USB MIDI Gadget Setup"
echo "========================================"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run this script as root (use sudo)"
    exit 1
fi

# Check if running on Raspberry Pi
if ! grep -q "BCM" /proc/cpuinfo; then
    echo "This script is designed for Raspberry Pi only"
    exit 1
fi

# Function to backup file if it doesn't have a backup already
backup_file() {
    local file="$1"
    if [ -f "$file" ] && [ ! -f "$file.backup" ]; then
        echo "Creating backup of $file"
        cp "$file" "$file.backup"
    fi
}

# Function to add line to file if it doesn't exist
add_line_if_missing() {
    local file="$1"
    local line="$2"
    if ! grep -Fxq "$line" "$file" 2>/dev/null; then
        echo "Adding '$line' to $file"
        echo "$line" >> "$file"
    else
        echo "Line '$line' already exists in $file"
    fi
}

echo "Step 1: Updating system packages..."
apt-get update

echo "Step 2: Installing required packages..."
apt-get install -y python3-mido

echo "Step 3: Configuring boot settings..."

# Backup config.txt
backup_file "/boot/config.txt"

# Enable dwc2 overlay for USB gadget mode
add_line_if_missing "/boot/config.txt" "dtoverlay=dwc2"

# Enable libcomposite module
backup_file "/etc/modules"
add_line_if_missing "/etc/modules" "dwc2"
add_line_if_missing "/etc/modules" "libcomposite"

echo "Step 4: Configuring USB gadget mode..."

# Create USB gadget setup script
cat > /usr/local/bin/setup-usb-gadget.sh << 'EOF'
#!/bin/bash

# USB MIDI Gadget Setup Script
# This script is called at boot to set up USB gadget mode

CONFIGFS_PATH="/sys/kernel/config"
GADGET_PATH="$CONFIGFS_PATH/usb_gadget/piano_led_midi"

# Wait for configfs to be available
for i in {1..30}; do
    if [ -d "$CONFIGFS_PATH" ]; then
        break
    fi
    sleep 1
done

if [ ! -d "$CONFIGFS_PATH" ]; then
    echo "configfs not available, mounting..."
    modprobe configfs
    mount -t configfs none /sys/kernel/config
fi

# Load required modules
modprobe libcomposite

# Check if gadget already exists
if [ -d "$GADGET_PATH" ]; then
    echo "USB gadget already configured"
    exit 0
fi

echo "Setting up USB MIDI gadget..."

# The actual gadget setup will be handled by the Python module
# This script just ensures the system is ready

echo "USB gadget system ready"
EOF

chmod +x /usr/local/bin/setup-usb-gadget.sh

echo "Step 5: Creating systemd service..."

# Create systemd service for USB gadget setup
cat > /etc/systemd/system/usb-gadget-setup.service << 'EOF'
[Unit]
Description=USB MIDI Gadget Setup
After=local-fs.target
Before=network.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/setup-usb-gadget.sh
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

# Enable the service
systemctl daemon-reload
systemctl enable usb-gadget-setup.service

echo "Step 6: Configuring udev rules..."

# Create udev rule for USB gadget
cat > /etc/udev/rules.d/99-usb-gadget.rules << 'EOF'
# USB MIDI Gadget udev rules
SUBSYSTEM=="usb", ATTR{idVendor}=="1d6b", ATTR{idProduct}=="0104", TAG+="systemd"
EOF

# Reload udev rules
udevadm control --reload-rules

echo "Step 7: Setting up permissions..."

# Add pi user to required groups
usermod -a -G audio pi 2>/dev/null || true

# Create sudoers rule for USB gadget management
cat > /etc/sudoers.d/usb-gadget << 'EOF'
# Allow pi user to manage USB gadget without password
pi ALL=(ALL) NOPASSWD: /bin/sh -c echo * > /sys/kernel/config/usb_gadget/*/UDC
pi ALL=(ALL) NOPASSWD: /bin/rm -rf /sys/kernel/config/usb_gadget/*
pi ALL=(ALL) NOPASSWD: /bin/mkdir -p /sys/kernel/config/usb_gadget/*
pi ALL=(ALL) NOPASSWD: /usr/bin/tee /sys/kernel/config/usb_gadget/*/*
pi ALL=(ALL) NOPASSWD: /usr/local/bin/setup-usb-gadget.sh
EOF

echo "Step 8: Creating configuration file..."

# Create configuration file for USB gadget settings
cat > /etc/piano-led-visualizer/usb-gadget.conf << 'EOF'
# USB MIDI Gadget Configuration
# This file contains settings for the USB MIDI gadget mode

[device]
vendor_id = 0x1d6b
product_id = 0x0104
manufacturer = Piano LED Visualizer
product = Piano LED MIDI Device
serial_number = 123456789

[midi]
in_ports = 1
out_ports = 1
buffer_length = 128
queue_length = 32

[config]
auto_enable = false
max_power = 250
EOF

# Create directory if it doesn't exist
mkdir -p /etc/piano-led-visualizer
chown -R pi:pi /etc/piano-led-visualizer

echo "Step 9: Adding USB gadget management to Piano LED Visualizer..."

# The integration will be handled by modifying the existing Python code

echo "========================================"
echo "USB MIDI Gadget Setup Complete!"
echo "========================================"
echo ""
echo "IMPORTANT: A reboot is required for changes to take effect."
echo ""
echo "After reboot, you can:"
echo "1. Enable USB gadget mode through the web interface"
echo "2. Use the Piano LED Visualizer as a MIDI device when connected via USB"
echo "3. The device will appear as 'Piano LED MIDI Device' on the connected computer"
echo ""
echo "Note: USB gadget mode and USB host mode are mutually exclusive."
echo "When gadget mode is enabled, you cannot connect MIDI keyboards directly to the Pi."
echo ""
echo "To complete the setup, please run:"
echo "sudo reboot"
echo ""

# Ask user if they want to reboot now
read -p "Would you like to reboot now? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Rebooting in 5 seconds..."
    sleep 5
    reboot
else
    echo "Please reboot manually when ready: sudo reboot"
fi