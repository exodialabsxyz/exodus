# Shell Session Management

## When to Use Shell

Use `shell` when you need to **interact with a shell and execute commands** that are:
- **Interactive** (netcat listeners, SSH, reverse shells, msfconsole)
- **Long-running** (nmap, gobuster, hydra, john)

For quick commands, create and use a general session.

## Shell Actions

### Create Session
Start a new shell session and execute a command:
```
shell(action="create", session_name="listener", command="nc", args="-lvnp 4444")
shell(action="create", session_name="nmap", command="nmap", args="-p- 10.0.0.5")
shell(action="create", session_name="bash", command="ls -la")  # args is optional
```

### List Sessions
See all active sessions:
```
shell(action="list")
```

### Read Output
Get output from a session (default: last 50 lines):
```
shell(action="read", session_name="listener")
shell(action="read", session_name="nmap", lines=100)
```

### Interact
Send input to a session (commands, text, passwords, etc.):
```
shell(action="interact", session_name="listener", command="whoami")
shell(action="interact", session_name="ssh_target", command="cat /etc/passwd")
shell(action="interact", session_name="ssh_target", command="myusername")  # Send username
shell(action="interact", session_name="ssh_target", command="mypassword")  # Send password
```

### Kill Session
Close a session when done:
```
shell(action="kill", session_name="listener")
```

## Example: Netcat Listener

```
# Start listener
shell(action="create", session_name="nc", command="nc", args="-lvnp 4444")

# Check output
shell(action="read", session_name="nc")

# Send commands after connection
shell(action="interact", session_name="nc", command="whoami")
shell(action="read", session_name="nc")

# Clean up
shell(action="kill", session_name="nc")
```

## Example: SSH Interactive Session

```
# Start SSH connection
shell(action="create", session_name="ssh", command="ssh", args="user@10.0.0.5")

# Check what it's asking for
shell(action="read", session_name="ssh")

# If it asks for password, send it
shell(action="interact", session_name="ssh", command="mypassword")
shell(action="read", session_name="ssh")

# Now send commands
shell(action="interact", session_name="ssh", command="id")
shell(action="read", session_name="ssh")

# Clean up
shell(action="kill", session_name="ssh")
```

## Waiting for Long-Running Tasks

Use `wait` to pause before checking results from scans or brute force attacks:

```
# Start long-running scan
shell(action="create", session_name="nmap", command="nmap", args="-p- -sV 10.0.0.5")

# Wait for scan to progress (e.g., 60 seconds)
wait(seconds=60)

# Check results
shell(action="read", session_name="nmap", lines=100)

# Wait more if needed
wait(seconds=120)
shell(action="read", session_name="nmap", lines=100)

# Clean up
shell(action="kill", session_name="nmap")
```

## Important

- **Always kill sessions when done** - Don't leave zombie sessions
- Read output after interactions to see results
- Use descriptive session names
- Use `wait` between checks for long-running tasks to avoid spamming reads
