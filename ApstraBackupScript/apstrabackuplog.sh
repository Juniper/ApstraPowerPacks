#!/bin/bash

# Define log file
LOG_FILE="/var/log/aos_backup_restore.log"
exec > >(tee -a "$LOG_FILE") 2>&1

# Variables
warmspare_ip=192.168.111.63 # Add the IP of your spare VM
warmspare_user=root # Warm spare user - should be root if you'd like to run the import automatically

echo "Starting backup and restore process at $(date)"

# Ensure the /tmp/aosbackup/ directory exists
if [[ ! -d /tmp/aosbackup/ ]]; then
    echo "Creating /tmp/aosbackup/ directory."
    mkdir /tmp/aosbackup/ || { echo "Failed to create /tmp/aosbackup/. Exiting."; exit 1; }
else
    echo "/tmp/aosbackup/ directory already exists."
fi

# Remove any existing files in /tmp/aosbackup/
echo "Cleaning up /tmp/aosbackup/."
rm -rf /tmp/aosbackup/* || { echo "Failed to clean /tmp/aosbackup/. Exiting."; exit 1; }

# Perform the backup
echo "Running /usr/sbin/aos_backup."
/usr/sbin/aos_backup -o /tmp/aosbackup/ || { echo "Backup command failed. Exiting."; exit 1; }

# Find the most recently created directory
echo "Finding the most recently created backup directory."
new_directory=$(ls -dt /tmp/aosbackup/* 2>/dev/null | head -n 1)
if [[ -z "$new_directory" ]]; then
    echo "No backup directory found. Exiting."
    exit 1
fi
new_directory=${new_directory%/}
echo "The newest directory is: $new_directory"

# Modify the aos_restore file
echo "Modifying the aos_restore file."
sed -i 's|/etc/init.d/aos start|#/etc/init.d/aos start|' "${new_directory%/}/aos_restore" || { echo "sed command failed. Exiting."; exit 1; }

# SSH into the warm spare VM to prepare the directory
echo "Connecting to warm spare VM to prepare directory."
ssh -i /root/.ssh/id_rsa "$warmspare_user@$warmspare_ip" << EOF
[[ -d /tmp/aosbackup/ ]] || mkdir /tmp/aosbackup/
rm -rf /tmp/aosbackup/*
EOF
if [[ $? -ne 0 ]]; then
    echo "SSH to warm spare VM failed. Exiting."
    exit 1
fi

# Copy backup files to warm spare VM
echo "Copying backup files to warm spare VM."
scp -i /root/.ssh/id_rsa -r /tmp/aosbackup/*/* "$warmspare_user@$warmspare_ip:/tmp/aosbackup/" || { echo "SCP command failed. Exiting."; exit 1; }

# Run the restore on the warm spare VM
echo "Running the restore on the warm spare VM."
ssh -i /root/.ssh/id_rsa "$warmspare_user@$warmspare_ip" /tmp/aosbackup/aos_restore
if [[ $? -ne 0 ]]; then
    echo "Restore command failed on warm spare VM. Exiting."
    exit 1
fi

echo "Backup and restore process completed successfully at $(date)."
exit 0
