# ApstraWspare
A quick script to backup and Apstra instance, scp the backup to a warm spare, and then restore it.

### Quick HowTo
-Download the apstrabackup.sh to /usr/local/bin/apstrabackup.sh
-set it as executable (chmod +x /usr/local/bin/apstrabackup.sh
- create a cron job to run it - this is an exacmple to run it once every 5 minutes.
- To have this run automatically, you will need to create an ssh key for root on the warm spare - 
- I would recommend, if possible, putting the spare on an isolated network, and certainly on a **different hypervisor** than where the main Apstra VM resides.
**NB, you will have to make the following modifications to /etc/sshd/sshd_config for this to work as the backup and restore processes require root access. 
- backup /etc/ssh/sshd_config
- comment out the lines AllowGroups ssh-allow and DenyUsers root (to do this, prepend a #)
- change PermitRootLogin to yes
- restart sshd (systemctl restart sshd)
- If you need to fail over to the spare, it is recommended to change these back - simply copy your backup sshd_config back into /etc/ssh/sshd_config, and restart sshd

### Creating an ssh key and sharing it with the spare - 





### **1. Open a Terminal (Command Line)**

- **On Linux or macOS:** You can open the Terminal application.
- **On Windows:** If you're using Windows 10 or later, you can open **PowerShell** or use **Windows Subsystem for Linux (WSL)** if it's installed. Alternatively, you can use an SSH client like **Git Bash** or **PuTTY**.

---

### **2. Generate the SSH Key Pair**

To generate an SSH key pair, use the `ssh-keygen` command:

```bash
ssh-keygen -t rsa -b 4096 
```

#### Explanation of Options:
- **`-t rsa`**: This specifies the type of key to create. `rsa` is the most common type of SSH key. If you want a more modern algorithm, you can use `-t ed25519` (recommended for most use cases).
- **`-b 4096`**: This option specifies the number of bits in the key. `4096` bits is more secure than the default 2048 bits. If you choose `ed25519`, you don’t need to specify this option, as it automatically uses a secure key length.

Example:

```bash
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"
```

### **3. Choose Where to Save the Key**

Once you run the `ssh-keygen` command, you'll be asked where to save the key. By default, SSH keys are saved to the `~/.ssh/` directory, in a file called `id_rsa` (for RSA keys). You can press **Enter** to accept the default location.

Example output:

```bash
Enter file in which to save the key (/home/your_user/.ssh/id_rsa):
```

If you want to save the key in a different file, specify the full path, like:

```bash
Enter file in which to save the key (/home/your_user/.ssh/my_custom_key):
```

### **4. Copy the Public Key to the Remote Server**

To use your new SSH key for authentication, you need to add your public key to the server’s authorized keys. There are several ways to do this, but the most common method is to use the `ssh-copy-id` command (on Linux/macOS):

```bash
ssh-copy-id username@remote_host
```

- Replace `username` with your username on the remote server.
- Replace `remote_host` with the server’s IP address or hostname.

Example:

```bash
ssh-copy-id user@192.168.1.10
```

This will copy your public key to the remote server’s `~/.ssh/authorized_keys` file, allowing you to log in using your SSH key rather than a password.

**Note**: If `ssh-copy-id` is not available on your system, you can manually copy the contents of the public key (`id_rsa.pub`) to the remote server’s `~/.ssh/authorized_keys` file.

Example:

```bash
cat ~/.ssh/id_rsa.pub
```

Then copy the output and paste it into the `~/.ssh/authorized_keys` file on the remote server.

---

### **7. Test the SSH Key Authentication**

Once the public key is added to the remote server, you can test the SSH key authentication by connecting to the server:

```bash
ssh root@apstraspareIP
```

If everything is set up correctly, you should be logged in without needing to enter a password (unless you set a passphrase for your private key).

---
