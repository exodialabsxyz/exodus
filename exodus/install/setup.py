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


def setup_venv(install_dir: str):
    print(f"{'=' * 8} Setting up virtual environment {'=' * 8}")
    venv_dir = os.path.join(install_dir, ".venv")
    subprocess.run([sys.executable, "-m", "venv", venv_dir], check=True)
    print(f"{'=' * 8} Virtual environment setup complete {'=' * 8}")
    return venv_dir


def install_exodus(install_dir: str, venv_dir: str):
    print(f"{'=' * 8} Installing EXODUS {'=' * 8}")
    pip_path = os.path.join(venv_dir, "bin", "pip")
    install_target = ".[cli]"
    subprocess.run([pip_path, "install", "--upgrade", "pip"], check=True)
    subprocess.run([pip_path, "install", "-e", install_target], check=True, cwd=install_dir)
    print(f"{'=' * 8} EXODUS installed {'=' * 8}")


def create_symlink(venv_dir: str):
    print(f"{'=' * 8} Configuring CLI commands {'=' * 8}")

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
            print(f"Command {script} configured")

    print(f"{'=' * 8} CLI commands configured {'=' * 8}")


def install_extra_dependencies(project_root: str, venv_dir: str):
    print(f"{'=' * 8} Installing extra dependencies {'=' * 8}")
    optional_features = {
        "docker": "Let the agents to execute tools in a Docker container with the EXODUS Security Executor or your favorites Docker images"
    }

    pip_path = os.path.join(venv_dir, "bin", "pip")
    selected_extras = ["cli"]

    for feature, description in optional_features.items():
        print(f"\n{'=' * 8} {feature} {'=' * 8}")
        print(f"{description}")
        print(f"\n{'=' * 8} {'=' * 8}\n")
        choice = input(f"Do you want to install {feature}? (y/N): ").lower().strip()
        if choice == "y":
            selected_extras.append(feature)

    install_target = f".[{','.join(selected_extras)}]"
    print(f"Installing EXODUS with extras: {install_target[1:]}")
    try:
        subprocess.run(
            [pip_path, "install", "-e", install_target],
            check=True,
            cwd=project_root,
        )
        print(f"{'=' * 8} Extra dependencies installed {'=' * 8}")
    except subprocess.CalledProcessError as e:
        print(f"Error installing extra dependencies: {e}")


def configure_exodus_settings(project_root: str):
    print(f"{'=' * 8} Configuring EXODUS settings {'=' * 8}")

    exodus_home = pathlib.Path.home() / ".exodus"
    exodus_home.mkdir(parents=True, exist_ok=True)

    target_settings = exodus_home / "settings.toml"
    example_settings = project_root / "settings.toml.example"

    if target_settings.exists():
        print(f"EXODUS settings already exists at {target_settings}")
        choice = (
            input("Do you want to reset from defaults and configure the settings again? (y/N): ")
            .lower()
            .strip()
        )
        if choice != "y":
            print(f"{'=' * 8} EXODUS settings not configured {'=' * 8}")
            return

    if example_settings.exists():
        print("Copying EXODUS settings from example settings file")
        shutil.copy(example_settings, target_settings)
        print(f"{'=' * 8} EXODUS settings copied from example settings file {'=' * 8}")
    else:
        print(f"Example settings file not found at {example_settings}")
        print(f"{'=' * 8} EXODUS settings not configured {'=' * 8}")
        return

    print(f"{'=' * 8} Personalizing EXODUS settings {'=' * 8}")
    print("In order to use your AI Model, you need to provide the API key for your provider.")
    print("You can find the API key in your provider's dashboard.")
    print("When you paste the api key, it will not be visible on the screen.\n")

    api_key = getpass.getpass("Enter your API key from your provider (Enter to skip): ").strip()

    with open(target_settings, "r") as f:
        settings_content = f.read()

    if api_key:
        settings_content = settings_content.replace(DEFAULT_API_KEY, f'"{api_key}"')
    else:
        print(
            f"Skipping API key configuration. You can set it later in the settings file {target_settings}"
        )

    print("[+] Configuring default model")
    print("Now you can configure the default model for your agents.")
    print(
        "By default EXODUS uses Litellm, so you can use the model name following the format <provider>/<model>."
    )
    print("For example, for Google Gemini, the model name is 'gemini/gemini-2.5-flash'.")
    print("For OpenAI, the model name is 'openai/gpt-4o' and so on ...")
    print(
        "Note: All we love local models! If you are using openai compatible server (like llama.cpp) just use openai/<model_served_name> (for example: openai/unsloth/Qwen3-4B-Instruct-2507-GGUF)"
    )

    default_model = input("Enter your default model (Enter to skip): ").strip()
    if default_model:
        settings_content = settings_content.replace(DEFAULT_MODEL, f'"{default_model}"')
    else:
        print(
            f"Skipping default model configuration. You can set it later in the settings file {target_settings}"
        )

    print("[+] Great! Finally we are configuring the execution mode")
    print("With execution mode you can configure the default execution mode for your agents.")
    print(
        "By default EXODUS uses local execution mode. It means that your agents will execute the tools in your local environment."
    )
    print(
        "You can also use docker execution mode. It means that your agents will execute the tools in a Docker container."
    )

    execution_mode = input("Enter your execution mode (local/docker): ").strip()
    if execution_mode == "local":
        settings_content = settings_content.replace(DEFAULT_EXECUTION_MODE, '"local"')
    elif execution_mode == "docker":
        settings_content = settings_content.replace(DEFAULT_EXECUTION_MODE, '"docker"')
    else:
        print(f"Invalid execution mode: {execution_mode}; using local execution mode")

    with open(target_settings, "w") as f:
        f.write(settings_content)
    print(f"{'=' * 8} EXODUS settings personalized {'=' * 8}")


def end_message(settings_path: pathlib.Path):
    print(f"{'=' * 8} EXODUS installation complete {'=' * 8}")
    print(f"{'=' * 8} You can now use EXODUS by running the following command: {'=' * 8}")
    print(f"{'=' * 8} exodus-cli chat{'=' * 8}\n\n")
    print(f"You can change the settings later in the settings file {settings_path.absolute()}")
    print(f"{'=' * 8} For more information, please refer to the documentation. {'=' * 8}")


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
