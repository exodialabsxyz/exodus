# Session Management Guidelines

## When to Use bash vs Sessions

### Use `bash` tool for:
- **Ephemeral commands**: Quick, one-time operations that don't require state persistence
- **Lightweight operations**: Fast commands that complete in seconds
- **Simple queries**: File reads, quick checks, basic system commands

Examples:
- `bash("ls -la /tmp")`
- `bash("cat /etc/passwd")`
- `bash("whoami")`
- `bash("ps aux | grep ssh")`

### Use **session tools** for:
- **Interactive tools**: Programs requiring continuous input/output interaction
  - Reverse shells (netcat listeners, caught shells)
  - SSH connections
  - Database clients (mysql, psql)
  - Interactive frameworks (msfconsole, sqlmap --wizard)
  
- **Long-running scans**: Commands that take minutes/hours to complete
  - `nmap` full port scans
  - `gobuster` directory brute-forcing
  - `hydra` or `medusa` password attacks
  - `john` hash cracking
  - `nikto` web scans

## How to Work with Sessions

### 1. Opening a Session
```
session_open(session_name="nmap_scan", command="nmap -p- -sV 10.0.0.5")
session_open(session_name="listener", command="nc -lvnp 4444")
```
**Best practices**:
- Use descriptive names: `listener`, `ssh_target`, `nmap_full_scan`
- One purpose per session (don't mix unrelated tasks)

### 2. Checking Session Status
```
session_list()  # See all active sessions
session_read(session_name="nmap_scan", lines=50)  # Check progress
```
**Best practices**:
- Regularly check long-running sessions for completion
- Use `session_read` to verify prompts before sending commands

### 3. Interacting with Sessions
```
session_interact(session_name="ssh_target", input="whoami")
session_interact(session_name="listener", input="cat /etc/passwd")
```
**Best practices**:
- Always read output after sending commands to understand the state
- Wait for prompts before sending the next command

### 4. Closing Sessions - CRITICAL
```
session_close(session_name="nmap_scan")
```
**IMPORTANT**: 
- **Always close sessions when finished** - This is mandatory for cleanliness
- Don't leave zombie sessions running unnecessarily
- Before transferring to another agent, close your completed sessions
- Check `session_list()` periodically and clean up finished tasks

## Workflow Example

**Bad approach** (blocking):
```
bash("nmap -p- 10.0.0.5")  # This blocks for 10+ minutes
bash("gobuster dir -u http://10.0.0.5 -w wordlist.txt")  # Can't run until nmap finishes
```

**Good approach** (parallelized with sessions):
```
1. session_open(session_name="nmap_scan", command="nmap -p- 10.0.0.5")
2. session_open(session_name="gobuster_scan", command="gobuster dir -u http://10.0.0.5 -w /usr/share/wordlists/dirb/common.txt")
3. [Do other work or transfer to another agent]
4. session_read(session_name="nmap_scan")  # Check progress later
5. session_read(session_name="gobuster_scan")
6. session_close(session_name="nmap_scan")  # Clean up when done
7. session_close(session_name="gobuster_scan")
```

## Session Hygiene Checklist

Before ending your turn or transferring control:
- [ ] Have I closed all completed sessions?
- [ ] Are any sessions still running that need monitoring?
- [ ] Did I document active sessions for the next agent?

**Remember**: Clean, organized session management makes you a professional operator.
