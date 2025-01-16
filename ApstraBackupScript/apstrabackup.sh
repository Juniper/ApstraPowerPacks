#!/bin/bash

warmspare_ip=192.168.111.63 # Add the IP of your spare VM
warmspare_user=root # Warm spare user - should be root if you'd like to run the import automatically
[[ -d /tmp/aosbackup/ ]] || mkdir /tmp/aosbackup/
rm -rf /tmp/aosbackup/*

/usr/sbin/aos_backup -o /tmp/aosbackup/
# Find the most recently created directory
new_directory=$(ls -dt /tmp/aosbackup/* | head -n 1)

# Remove the trailing slash from the directory name
new_directory=${new_directory%/}

# Print the result (for testing/debugging)
echo "The newest directory is: $new_directory"
sed -i 's|/etc/init.d/aos start|#/etc/init.d/aos start|' ${new_directory%/}/aos_restore || { echo "sed command failed. Exiting."; exit 1; } # remove the aos init line from aos_restore
ssh -i /root/.ssh/id_rsa  $warmspare_user@$warmspare_ip  << EOF
[[ -d /tmp/aosbackup/ ]] || mkdir /tmp/aosbackup/
rm -rf /tmp/aosbackup/*  
EOF

scp -i /root/.ssh/id_rsa -r /tmp/aosbackup/*/* $warmspare_user@$warmspare_ip:/tmp/aosbackup/ #copy over the backup file
ssh -i /root/.ssh/id_rsa  $warmspare_user@$warmspare_ip /tmp/aosbackup/aos_restore #run the restore

