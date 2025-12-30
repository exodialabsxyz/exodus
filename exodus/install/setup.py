import getpass
import os
import pathlib
import platform
import shutil
import subprocess
import sys

DEFAULT_API_KEY = '"AIzaSyD0Zu6YJBq4yDFyD6YJYJYJYJYJYJYJYJY"'
DEFAULT_MODEL = '"gemini/gemini-2.5-flash"'
DEFAULT_EXECUTION_MODE = '"local"'

### Installer styles ###


class Colors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"


### Installer styling functions ###


def print_step(message):
    print(f"\n{Colors.BOLD}{Colors.OKBLUE}=== {message} ==={Colors.ENDC}\n")


def print_success(message):
    print(f"{Colors.OKGREEN}[0]{message}{Colors.ENDC}")


def print_info(message):
    print(f"{Colors.OKCYAN}[+] {message}{Colors.ENDC}")


def print_error(message):
    print(f"{Colors.FAIL}[X]{message}{Colors.ENDC}")


def setup_venv(install_dir: str):
    print_step("Setting up virtual environment")
    venv_dir = os.path.join(install_dir, ".venv")
    print_info(f"Creating virtual environment in {venv_dir}")
    try:
        subprocess.run([sys.executable, "-m", "venv", venv_dir], check=True)
        print_success("Virtual environment setup complete")
        return venv_dir
    except subprocess.CalledProcessError as e:
        print_error(f"Failed to create virtual environment: {e}")
        raise e


def install_exodus(install_dir: str, venv_dir: str):
    print_step("Installing EXODUS")
    pip_path = os.path.join(venv_dir, "bin", "pip")
    install_target = ".[cli]"
    try:
        print_info("Upgrading pip")
        subprocess.run([pip_path, "install", "--upgrade", "pip"], check=True)
        print_success("Pip upgraded")
        print_info("Installing EXODUS")
        subprocess.run([pip_path, "install", "-e", install_target], check=True, cwd=install_dir)
        print_success("EXODUS installed")
    except subprocess.CalledProcessError as e:
        print_error(f"Failed to install EXODUS: {e}")
        raise e


def create_symlink(venv_dir: str):
    print_step("Creating symlinks for CLI commands")

    local_bin = pathlib.Path.home() / ".local" / "bin"
    local_bin.mkdir(parents=True, exist_ok=True)

    scripts = ["exodus-cli", "exodus-server", "exodus-server-exec"]
    venv_bin = pathlib.Path(venv_dir) / "bin"
    for script in scripts:
        source = venv_bin / script
        target = local_bin / script

        if source.exists():
            if target.exists():
                target.unlink()
            target.symlink_to(source)
            print_info(f"Command {script} configured")

    print_success("Symlinks created for CLI commands")


def install_extra_dependencies(project_root: str, venv_dir: str):
    print_step("Installing extra dependencies")
    optional_features = {
        "docker": "Allows agents to execute tools in a Docker container with the EXODUS Security Executor or your favorite Docker images (NOTE: This does not install Docker itself, only the Python dependencies needed to interact with Docker)"
    }

    pip_path = os.path.join(venv_dir, "bin", "pip")
    selected_extras = ["cli"]

    for feature, description in optional_features.items():
        print_step(f"Optional Feature: {feature.upper()}")
        print_info(f"{description}\n")
        choice = (
            input(
                f"{Colors.BOLD}{Colors.OKBLUE}[?] Do you want to install {feature}? (y/N): {Colors.ENDC}"
            )
            .lower()
            .strip()
        )
        if choice == "y":
            selected_extras.append(feature)

    install_target = f".[{','.join(selected_extras)}]"
    print_info(f"Installing EXODUS with extras: {install_target}")
    try:
        subprocess.run(
            [pip_path, "install", "-e", install_target],
            check=True,
            cwd=project_root,
        )
        print_success("Extra dependencies installed")
    except subprocess.CalledProcessError as e:
        print_error(f"Error installing extra dependencies: {e}")
        raise e


def configure_exodus_settings(project_root: str):
    print_step("Configuring EXODUS settings")

    exodus_home = pathlib.Path.home() / ".exodus"
    exodus_home.mkdir(parents=True, exist_ok=True)

    target_settings = exodus_home / "settings.toml"
    example_settings = project_root / "settings.toml.example"

    if target_settings.exists():
        print_info(f"EXODUS settings already exists at {target_settings}")
        choice = (
            input(
                f"{Colors.BOLD}{Colors.OKBLUE}[?] Do you want to reset from defaults and configure the settings again? (y/N): {Colors.ENDC}"
            )
            .lower()
            .strip()
        )
        if choice != "y":
            print_info("Keeping existing EXODUS settings")
            return

    if example_settings.exists():
        print_info("Copying EXODUS settings from example settings file")
        shutil.copy(example_settings, target_settings)
        print_success("EXODUS settings copied from example settings file")
    else:
        print_error(f"Example settings file not found at {example_settings}")
        print_error("EXODUS settings not configured")
        return

    ### Reading the settings file
    with open(target_settings, "r") as f:
        settings_content = f.read()

    ### Configuring default model
    print_step("Configuring default model")
    print_info("Now you can configure the default model for your agents.")
    print_info(
        "By default EXODUS uses Litellm, so you can use the model name following the format <provider>/<model>."
    )
    print_info("For example, for Google Gemini, the model name is 'gemini/gemini-2.5-flash'.")
    print_info("For OpenAI, the model name is 'openai/gpt-4o' and so on ...")
    print_info(
        "Note: All we love local models! If you are using openai compatible server (like llama.cpp) just use openai/<model_served_name> (for example: openai/unsloth/Qwen3-4B-Instruct-2507-GGUF)"
    )

    default_model = input(
        f"{Colors.BOLD}{Colors.OKBLUE}[?] Enter your default model (Enter to skip): {Colors.ENDC}"
    ).strip()
    if default_model:
        settings_content = settings_content.replace(DEFAULT_MODEL, f'"{default_model}"')
    else:
        print_info(
            f"Skipping default model configuration. You can set it later in the settings file {target_settings}"
        )

    ### Configuring API Key
    print_step("Configuring API Key")
    print_info("In order to use your AI Model, you need to provide the API key for your provider.")
    print_info("You can find the API key in your provider's dashboard.")
    print_info("When you paste the API key, it will not be visible on the screen.\n")

    api_key = getpass.getpass(
        f"{Colors.BOLD}{Colors.OKBLUE}[?] Enter your API key from your provider (Enter to skip): {Colors.ENDC}"
    ).strip()

    if api_key:
        settings_content = settings_content.replace(DEFAULT_API_KEY, f'"{api_key}"')
    else:
        print_info(
            f"Skipping API key configuration. You can set it later in the settings file {target_settings}"
        )

    ### Configuring execution mode
    print_step("Configuring execution mode")
    print_info("With execution mode you can configure the default execution mode for your agents.")
    print_info(
        "By default EXODUS uses local execution mode. It means that your agents will execute the tools in your local environment."
    )
    print_info(
        "You can also use docker execution mode. It means that your agents will execute the tools in a Docker container."
    )

    execution_mode = input(
        f"{Colors.BOLD}{Colors.OKBLUE}[?] Enter your execution mode (local/docker): {Colors.ENDC}"
    ).strip()
    if execution_mode == "local":
        settings_content = settings_content.replace(DEFAULT_EXECUTION_MODE, '"local"')
    elif execution_mode == "docker":
        settings_content = settings_content.replace(DEFAULT_EXECUTION_MODE, '"docker"')
    else:
        print_error(f"Invalid execution mode: {execution_mode}; using local execution mode")

    ### Writing the settings file
    with open(target_settings, "w") as f:
        f.write(settings_content)
    print_success("EXODUS settings personalized")


def end_message(settings_path: pathlib.Path):
    print_success("EXODUS installation complete")
    print_info("You can now use EXODUS by running the following command:")
    print_info("exodus-cli chat")
    print_info(f"You can change the settings later in the settings file {settings_path.absolute()}")
    print_info("For more information, please refer to the documentation.")


if __name__ == "__main__":
    current_file_path = pathlib.Path(__file__).resolve()
    PROJECT_ROOT = current_file_path.parent.parent.parent

    venv_dir = setup_venv(PROJECT_ROOT)
    install_exodus(PROJECT_ROOT, venv_dir)
    install_extra_dependencies(PROJECT_ROOT, venv_dir)
    configure_exodus_settings(PROJECT_ROOT)

    install_system = platform.system().lower()
    if install_system == "linux":
        install_system = "debian"
    elif install_system == "darwin":
        install_system = "macos"
    elif install_system == "windows":
        install_system = "windows"
    else:
        raise ValueError(f"Unsupported system: {install_system}")

    if install_system == "debian" or install_system == "macos":
        create_symlink(venv_dir)

    end_message(pathlib.Path.home() / ".exodus" / "settings.toml")
