import json
import os

from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

from exodus.core.models.memory import MemoryManager, Message
from exodus.settings import settings
from exodus.logs import logger

class LocalJsonMemoryManager(MemoryManager):
    
    def __init__(self):
        super().__init__()
        self._workspace = settings.get("agent.memory.local.workspace", None)
        
        if not self._workspace:
            logger.warning("No workspace provided for local JSON memory manager, setting to the current working directory")
            self._workspace = Path.cwd()
        else:
            self._workspace = Path(self._workspace)
        
        if not self._workspace.exists():
            logger.debug("Workspace does not exist, creating it")
            self._workspace.mkdir(parents=True, exist_ok=True)
        else:
            logger.debug("Workspace exists, using it")
        
    def add_memory(self, message: Message) -> None:
        self._short_term_memory.append(message)

    def get_memory(self) -> List[Message]:
        return self._short_term_memory

    def clear_memory(self) -> None:
        self._short_term_memory = []

    def load_memory(self, memory_file: Path) -> None:
        if not memory_file.exists():
            logger.error("Memory file does not exist, cannot load memory")
            return
        
        try:
            data = json.loads(memory_file.read_text(encoding="utf-8"))
            self.short_term_memory = []
            for item in data:
                if 'timestamp' in item and isinstance(item['timestamp'], str):
                    try:
                        item['timestamp'] = datetime.fromisoformat(item['timestamp'])
                    except Exception as e:
                        logger.error(f"Failed to parse timestamp: {e}")
                        item['timestamp'] = datetime.now()

                self._short_term_memory.append(Message(**item))
            logger.debug(f"Loaded {len(self._short_term_memory)} messages from {memory_file}")
        except Exception as e:
            logger.error(f"Failed to load memory: {e}")

    def save_memory(self, memory_file: Optional[Path] = None) -> None:
        if not memory_file:
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            memory_file = self._workspace / f"exodus_memory_{timestamp}.json"
        
        try:
            data_to_save = [message.to_dict() for message in self._short_term_memory]
            with open(memory_file, "w", encoding="utf-8") as f:
                json.dump(data_to_save, f, indent=4, ensure_ascii=False)
            logger.debug(f"Saved {len(data_to_save)} messages to {memory_file}")
        except Exception as e:
            logger.error(f"Failed to save memory: {e}")
                
