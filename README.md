# EXODUS: Swarm Intelligence for Autonomous Cybersecurity

EXODUS is a lightweight, modular, open-source cybersecurity framework. Create and share your agents, add capabilities by creating plugins, and automate your agent teams for pentesting, reconnaissance, vulnerability discovery, and much more.

---

<div align="center">
<img src="docs/machine_resolution.gif" alt="EXODUS - Autonomous Hack The Box Machine Resolution" width="800"/>
*Autonomous resolution of a Hack The Box machine using the Exodus framework (Video accelerated)*
</div>

---

## Key Features

+ Use the model you want: support for DeepSeek, Ollama, Google, OpenAI, and more.
+ Modular architecture: easily create or use plugins to add functionalities to your agents.
+ Multi-agent swarm architecture: from individual agents to specialized teams with different patterns (central orchestrator, agent delegation, etc.)
+ Lightweight implementation: avoids heavy agent libraries and uses only what is strictly necessary.

## 📋 Table of Contents

- [Installation & Setup](#-installation--setup)
- [Quick Start](#-quick-start)
- [Execution Modes (Engines)](#️-execution-modes-engines)
- [Creating Custom Plugins](#-creating-custom-plugins)
- [Creating Custom Agents](#-creating-custom-agents)
- [Agent Handoffs](#-agent-handoffs)
- [Secure Execution Modes](#-secure-execution-modes)
- [Technical Highlights](#-technical-highlights)
- [Architecture](#-architecture)

## 🚀 Installation & Setup

### One-Line Installation (Recommended)

To install EXODUS on Linux or macOS, simply run the following command in your terminal:

```bash
bash <(curl -sSL https://raw.githubusercontent.com/exodialabsxyz/exodus/main/exodus/install/bootstrap.sh)
```

This script will automatically detect your OS, install dependencies, and set up everything for you.

### Prerequisites

- Python 3.11 or higher
- Docker (optional, for isolated execution mode)
- An API key for your chosen LLM provider (Google Gemini, OpenAI, etc.)

### Installation

```bash
# Clone the repository
git clone https://github.com/exodialabsxyz/exodus.git
cd exodus

# Install EXODUS
pip install -e .
```

### Initial Configuration

1. **Copy the example configuration:**
   ```bash
   cp settings.toml.example settings.toml
   ```

2. **Configure your LLM provider:**
   Edit `settings.toml` and add your API key:
   ```toml
   [llm]
   default_model = "gemini/gemini-2.5-flash"
   default_provider = "litellm"
   default_max_context_tokens = 700000
   custom_api_base = ""  # Optional: for local models or custom endpoints
   
   [llm.default_provider_config]
   api_key = "your-api-key-here"
   ```

3. **Configure execution mode:**
   ```toml
   [agent]
   default_agent = "triage_agent"
   max_iterations = 100
   execution_mode = "local"  # or "docker"
   
   [agent.execution.docker]
   default_image = "parrotsec/security:7.0"
   default_image_name = "exodus_container"
   ```

4. **Set logging level:**
   ```toml
   [logging]
   level = "INFO"  # DEBUG, INFO, WARNING, ERROR
   format = "[exodus] %(asctime)s - %(name)s - %(levelname)s - %(message)s"
   ```

## ⚡ Quick Start

### Start a Chat Session

```bash
# Start with default agent
exodus-cli chat

# Start with a specific agent
exodus-cli chat --agent triage_agent

# Use a different model
exodus-cli chat --model "gemini/gemini-2.5-pro"

# Adjust temperature
exodus-cli chat --temperature 0.7
```

### Example Usage

```bash
# Start with the triage agent for automatic task routing
exodus-cli chat --agent triage_agent

> "Scan 192.168.1.1 for open ports and services"
# triage_agent will automatically transfer to recon_agent
# recon_agent will execute the scan and provide results
```

### Using Ollama (Local Models)

```toml
[llm]
default_model = "ollama/granite4:latest"
custom_api_base = "http://localhost:11434"

[llm.default_provider_config]
api_key = "ollama_apikey"
```

## ⚙️ Execution Modes (Engines)

EXODUS provides two distinct execution engines designed for different operational scenarios:

### Interactive Mode (Human-in-the-Loop)

The **default engine** for manual operation where a human operator (pentester, security analyst) maintains control and directs agent actions in real-time.

```bash
# Start interactive chat session
exodus-cli chat --agent triage_agent
```

**Use Cases:**
- **Manual pentesting**: Operator analyzes results and decides next steps
- **Exploratory reconnaissance**: Human expertise guides the investigation
- **Training and learning**: Understand how agents work step-by-step
- **Compliance requirements**: Maintain human oversight for sensitive operations

**Characteristics:**
- Human operator controls the flow
- Agent responds to each user message
- Full visibility into agent reasoning
- Manual approval before critical actions
- Interactive feedback and course correction

**Example workflow:**
```
You: "Scan this target for open ports"
Agent: [Executes nmap scan, shows results]
You: "Now enumerate the HTTP service on port 80"
Agent: [Performs HTTP enumeration]
You: "Looks vulnerable, try directory bruteforce"
Agent: [Executes gobuster]
```

---

### Automated Mode (Autonomous Execution)

The **automated engine** (`exodus-cli auto`) enables fully autonomous operation with advanced planning, reflection, and self-correction capabilities. Designed for tasks that require minimal human intervention.

```bash
# Execute autonomous mission
exodus-cli auto "Perform complete reconnaissance on exodialabs.xyz" \
  --agent recon_agent \
  --session scan_20250107 \
  --verbose
```

**Use Cases:**
- **Automated scanning**: Schedule unattended reconnaissance of infrastructure
- **CI/CD security testing**: Integrate into pipelines for continuous assessment
- **Bug bounty automation**: Autonomous discovery of vulnerabilities
- **Large-scale operations**: Deploy agent swarms for distributed tasks
- **Repetitive workflows**: Automate routine security assessments

**Advanced Features:**

#### 1. **Dynamic Planning**
The agent generates a structured task plan based on the objective:
```
Objective: "Scan target and find vulnerabilities"
Plan:
  ├─ task_1: Port scan and service discovery
  ├─ task_2: HTTP/SMB enumeration (depends on task_1)
  ├─ task_3: Vulnerability identification
  ├─ task_4: Exploit validation
  └─ task_5: Report generation
```

#### 2. **Strategic Reflection**
Periodic self-evaluation to ensure progress:
- **Iteration-based**: Reviews progress every N steps (default: 25)
- **Task-based**: Evaluates after N completed tasks (default: 3)
- **Actions**: `CONTINUE`, `REPLAN`, `ESCALATE`, or `COMPLETE`

```
Reflection Checkpoint:
  Progress: 3/6 tasks (50%)
  Avg Score: 8.5/10
  Action: CONTINUE
  Reasoning: "Making good progress, no blockers detected"
```

#### 3. **Dynamic Replanning**
Agent can regenerate the plan mid-execution if:
- Strategy isn't working (repeated failures)
- Environment changed (new services discovered)
- Task becomes irrelevant (objective already achieved)

```
Reflection: REPLAN (confidence: 9.0)
  Reasoning: "Initial plan assumed SSH access, but only HTTP is available.
             Pivoting to web-based exploitation strategy."

Plan Updated:
  ├─ task_1: ✓ Port scan completed
  ├─ task_2: ✓ Service enumeration
  ├─ task_3_new: Web vulnerability scan (modified)
  └─ task_4_new: SQL injection testing (new approach)
```

#### 4. **Checkpoint & Resume**
Execution state is automatically saved:
```bash
# Start mission
exodus-cli auto "Long-running task" --session my_mission

# Interrupt with Ctrl+C or timeout
^C Interrupted by user

# Resume from checkpoint
exodus-cli auto --resume --session my_mission
```

#### 5. **Escalation to Human**
Agent can request assistance when stuck:
```
Reflection: ESCALATE
  Reasoning: "Credentials required to proceed. Manual intervention needed."

Agent requests human assistance
```

**Configuration Options:**

```toml
[agent.automated]
reflection_iteration_interval = 25  # Reflect every N steps
reflection_task_interval = 3        # Reflect every N completed tasks
allow_replanning = true             # Enable dynamic replanning
min_task_score = 0.3                # Minimum acceptable task quality
```

---

### Choosing the Right Mode

| Aspect | Interactive Mode | Automated Mode |
|--------|------------------|----------------|
| **Control** | Human operator | Autonomous agent |
| **Planning** | Manual | Dynamic (LLM-generated) |
| **Reflection** | N/A | Every N tasks/iterations |
| **Replanning** | N/A | Automatic when needed |
| **Best For** | Exploratory work, HITL | Repetitive tasks, CI/CD |
| **Overhead** | Requires constant attention | Set and forget |
| **Use Case** | Pentesting engagement | Automated security scanning |

---

## 🔧 Creating Custom Plugins

Create powerful tools for your agents with just a simple decorator. EXODUS automatically generates the OpenAI-compatible schema:

```python
from exodus.core.decorators import tool

@tool(
    name="port_scanner",
    type="cli",
    description="Scans ports on a target host using nmap"
)
def port_scanner(target: str, ports: str = "1-1000") -> str:
    """Scans the specified ports on the target."""
    return f"nmap -p {ports} {target}"

# Register your plugin class
class SecurityPlugin:
    @staticmethod
    def get_tools():
        return {
            port_scanner.tool_name: port_scanner,
        }
```

To make your plugin discoverable, register it in your `pyproject.toml`:

```toml
[project.entry-points."exodus.plugins.tools"]
security = "your_package.plugins:SecurityPlugin"
```

EXODUS will automatically discover and load all plugins from the `exodus.plugins.tools` entry point group at startup.

**Plugin System:**
- **Python tools**: Execute code directly in your environment
- **CLI tools**: Return shell commands executed in isolated containers
- **Auto-validation**: Pydantic models generated automatically from type hints
- **Auto-discovery**: Plugins loaded via Python entry points (`exodus.plugins.tools`)
- **Distributable**: Share your plugins as PyPI packages

## 🤖 Creating Custom Agents

EXODUS agents use simple TOML configuration files with **modular system prompts** stored in separate Markdown files.

### Agent Structure

```
exodus/agents/
├── single/          # Agent TOML configs
│   ├── triage_agent.toml
│   └── recon_agent.toml
└── prompts/         # Markdown prompt files
    ├── common.md
    └── recon_agent.md
```

### Basic Configuration

```toml
[agent]
name = "recon_agent"
description = "Expert in reconnaissance and enumeration"
system_prompt = ["common.md", "recon_agent.md"]  # Load multiple prompt files
tools = ["core_bash"]
handoffs = ["triage_agent", "web_exploit_agent"]

[agent.llm]
model = "gemini/gemini-2.5-pro"
temperature = 0.5
```

### System Prompt Options

**Option 1: Modular Prompts (Recommended)**
```toml
system_prompt = ["common.md", "recon_agent.md"]  # Loads from exodus/agents/prompts/
```

**Option 2: Single File**
```toml
system_prompt = ["recon_agent.md"]
```

**Option 3: Inline Text**
```toml
system_prompt = "You are a pentesting expert. Analyze targets."
```

### Agent Configuration Options

- **name**: Unique agent identifier
- **description**: Brief description for handoffs
- **system_prompt**: String or array of `.md` files from `prompts/`
- **tools**: List of tool names (e.g., `["core_bash"]`)
- **handoffs**: Other agents to transfer control to
- **max_iterations**: Override global iteration limit (optional)

### Per-Agent LLM Settings

```toml
[agent.llm]
model = "gemini/gemini-2.5-pro"    # Override default model
temperature = 0.7                   # Randomness (0-2)
max_tokens = 100000                 # Max response length
max_context_tokens = 700000         # Max tokens on context
```

**Benefits:**
- ✅ Reuse common instructions across agents
- ✅ Keep TOML configs clean and simple
- ✅ Better version control for prompts
- ✅ Easy to update and maintain

## 🔄 Agent Handoffs

EXODUS supports **dynamic agent delegation** where agents can transfer control to other specialized agents during execution:

```toml
[agent]
name = "triage_agent"
description = "Routes requests to specialized agents"
system_prompt = "Analyze the user's request and delegate to the appropriate expert."
tools = []
handoffs = ["security_expert", "code_analyst", "recon_specialist"]

[agent.llm]
temperature = 0.3
```

**How it works:**
1. Agent analyzes the task and determines if another agent is better suited
2. Calls `transfer_to_{agent_name}` with a reason for the handoff
3. Target agent receives context and continues execution
4. Shared memory preserves conversation history across handoffs
5. Global `max_iterations` prevents infinite loops across all agents

**Example workflow:**
```
User: "Scan this webapp and find SQL injection vulnerabilities"
  ↓
triage_agent -> Identifies security task
  ↓
transfer_to_security_expert(reason="Requires vulnerability assessment")
  ↓
security_expert -> Scans target, finds issues, needs code review
  ↓
transfer_to_code_analyst(reason="Review vulnerable code patterns")
  ↓
code_analyst -> Provides fix recommendations
```

**Benefits:**
- **Specialized expertise**: Each agent focuses on what it does best
- **Automatic routing**: LLM decides when to delegate based on task requirements
- **Seamless context**: Conversation flows naturally between agents
- **No orchestrator needed**: Agents self-coordinate through handoffs

---

## 🧠 Context Management

EXODUS includes a context strategy to handle long-running missions without exceeding LLM token limits or losing critical information.

When an agent's conversation history approaches the `max_context_tokens` limit, EXODUS automatically:

1.  **Detects the threshold**: Triggers when current tokens reach 90% of the limit.
2.  **Self-Summarization**: Uses the agent's LLM to analyze the oldest 60% of the conversation.
3.  **Keypoint Extraction**: Generates a technical summary that preserves entities, tool results, and pending tasks.
4.  **Memory Update**: Replaces the old messages with a single summary message, freeing up context for new interactions.

### Configuration

You can enable and tune this behavior in your `settings.toml` or per-agent configuration:

```toml
[llm]
# Global default (optional)
default_max_context_tokens = 700000

# Per-agent override in agent TOML
[agent.llm]
max_context_tokens = 500000
```

**Benefits:**
- **Long Sessions**: Run extremely long missions without "Context Window Exceeded" errors.
- **Cost Optimization**: Keeps context lean, reducing token usage in subsequent calls.
- **Focus**: The LLM stays focused on recent results while retaining a high-level view of the past.

---

## 🐳 Secure Execution Modes

EXODUS provides multiple execution drivers for running tools safely:

**Docker Mode** (Recommended for isolated execution):
```toml
[agent]
execution_mode = "docker"

[agent.execution.docker]
default_image = "debian:latest"
default_image_name = "exodus_container"
```

- Isolated environment using any Docker image (Debian, Ubuntu, Kali, ParrotSec, Alpine, etc.)
- Automatic container lifecycle management
- Safe execution of commands without affecting host system
- Perfect for security tools or untrusted code execution

**Local Mode**:
```toml
[agent]
execution_mode = "local"
```

- Direct execution in your environment
- Faster for trusted tools
- Use for development and testing

## 🐳 Exodus Security Executor Container

EXODUS provides a specialized Docker container that runs an `exodus-server` daemon for executing Python-based tools in an isolated ParrotSec environment. Agents can communicate with this server via Unix sockets to execute EXODUS tools remotely.

### Quick Start

```bash
# Build the image
docker build -t exodus-security-executor -f docker/exodus_security_executor/Dockerfile .

# Run the container
docker run -d --name exodus-executor exodus-security-executor

# View logs
docker logs -f exodus-executor
```

The container automatically starts the `exodus-server` on `/tmp/exodus/executor.sock` and loads the full EXODUS tool registry. This allows agents to execute Python tools in an isolated, security-focused environment.

For detailed documentation, communication protocols, and advanced usage, see [`docker/README.md`](docker/README.md)

## ⚡ Technical Highlights

EXODUS is built on **abstract, modular architecture** that enables endless possibilities:

- **Pluggable LLM Providers**: Abstract `LLMProvider` interface supports any model backend (LiteLLM, OpenAI, custom providers)
- **Extensible Memory Systems**: Implement your own `MemoryManager` (JSON, Redis, PostgreSQL, vector DBs)
- **Custom Execution Drivers**: Create new `ToolExecutionDriver` backends (Kubernetes, Lambda, SSH, etc.)
- **Plugin Registry**: Automatic tool discovery via Python entry points - share and reuse tools across projects
- **Tool Type System**: Define custom tool types beyond `python` and `cli`
- **Agent Orchestration**: Framework-ready for swarm patterns (hierarchical, collaborative, competitive)
- **Type Safety**: Pydantic models auto-generated from type hints
- **Async-First**: Built on asyncio for concurrent agent execution
- **Minimal Core**: Only `httpx` and `pydantic` - everything else is pluggable

## 📦 Architecture

```
Agent Engine
    ├── LLM Provider (LiteLLM, OpenAI, custom)
    ├── Memory Manager (JSON, Redis, custom)
    ├── Tool Executor
    │   ├── Tool Registry (plugin discovery)
    │   └── Execution Driver (Docker/Local/custom)
    └── Agent Definition (TOML config)
        └── Handoffs (dynamic agent delegation)
```

## 🔌 Supported LLM Providers

Thanks to LiteLLM integration, EXODUS supports 100+ LLM providers:

- **Google**: `gemini/gemini-2.0-flash-exp`, `gemini/gemini-pro`
- **OpenAI**: `gpt-4`, `gpt-3.5-turbo`, `gpt-4-turbo`
- **Anthropic**: `claude-3-opus`, `claude-3-sonnet`
- **Ollama**: `ollama/llama3.2`, `ollama/mistral`, `ollama/qwen3:latest`
- **DeepSeek**: `deepseek/deepseek-chat`, `deepseek/deepseek-coder`
- **And many more**: Groq, Cohere, Replicate, Together AI, etc.

Simply set the model in your configuration (using litellm):
```toml
[llm]
default_model = "provider/model-name"
```

## 🏆 Showcases & Writeups

See EXODUS in action! Explore our collection of automated mission reports and writeups demonstrating how the framework resolves real-world security challenges.

👉 **[Browse All Writeups](writeups/)**

### Featured Missions:
- **[HTB Cap](writeups/hackthebox_machines/Cap/README.md)**: Full compromise of a Linux machine involving IDOR, credential harvesting, and Linux Capabilities exploitation.

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

- **Report bugs**: Open an issue at https://github.com/exodialabsxyz/exodus/issues
- **Suggest features**: Share your ideas for improvements
- **Create plugins**: Build and share tools for the community
- **Improve docs**: Help make EXODUS more accessible
- **Submit PRs**: Fix bugs or add features

Visit our GitHub: https://github.com/exodialabsxyz/exodus

## 📝 License

**EXODUS Core Framework is free and open source** under the [MIT License](LICENSE).

**You CAN:**
- Use commercially without restrictions
- Modify and distribute freely
- Create and sell plugins
- Build commercial products on top of EXODUS
- Use in production environments
- Fork and create derivatives

This includes the core framework, agent engine, CLI, plugin system, and all core components on this repository.

**Contact:** contact@exodialabs.xyz | **Website:** https://exodialabs.xyz

See [LICENSE](LICENSE) file for complete terms.

## ⚠️ Disclaimer

> **IMPORTANT**: EXODUS is a powerful cybersecurity tool. Use it responsibly.
> 
> The repository authors do not promote the misuse of this tool for criminal purposes, outside any regulation or law, which can cause serious harm. By downloading, using, or modifying the code, you accept the terms of the license and the aforementioned limitations on its use.
> 
> Always ensure you have proper authorization before testing or scanning any systems.

## 🔗 Resources

- **Website**: https://exodialabs.xyz
- **GitHub**: https://github.com/exodialabsxyz/exodus
- **Examples**: See `exodus/agents/single/` for agent examples
- **Issues & Discussions**: https://github.com/exodialabsxyz/exodus/issues
- **Contact**: contact@exodialabs.xyz

---

---

**EXODUS** - Made with ❤️ by AGP for the cybersecurity community

https://exodialabs.xyz |  contact@exodialabs.xyz | https://github.com/exodialabsxyz
