try:
    import tomllib
except ImportError:
    # Fallback for older python versions if needed, though project requires >= 3.11
    import tomli as tomllib
from pathlib import Path
from typing import Any, Dict

BASE_DIR = Path(__file__).resolve().parent.parent

### Priority: CWD > Package Root (for dev/editable installs)
CWD_SETTINGS = Path.cwd() / "settings.toml"
PACKAGE_SETTINGS = BASE_DIR / "settings.toml"

SETTINGS_FILE = CWD_SETTINGS if CWD_SETTINGS.exists() else PACKAGE_SETTINGS


class Settings:
    _instance = None
    _config: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Settings, cls).__new__(cls)
            cls._instance._load()
        return cls._instance

    def _load(self):
        """Load settings from TOML file and environment variables."""
        if SETTINGS_FILE.exists():
            with open(SETTINGS_FILE, "rb") as f:
                try:
                    self._config = tomllib.load(f)
                except tomllib.TOMLDecodeError:
                    self._config = {}
        else:
            self._config = {}

        # Here we could override with environment variables if needed
        # self._override_from_env()

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a setting value using dot notation (e.g., 'llm.default_model')."""
        keys = key.split(".")
        value = self._config
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default

    def __getitem__(self, item):
        return self.get(item)


settings = Settings()
