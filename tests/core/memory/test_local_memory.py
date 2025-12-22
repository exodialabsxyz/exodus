import pytest
from datetime import datetime
from pathlib import Path

from exodus.core.models.memory import Message
from exodus.core.memory.local_json_memory import LocalJsonMemoryManager

class TestLocalJSONMemory:
    """Test Local JSON Memory"""

    @pytest.fixture
    def memory_manager(self):
        manager = LocalJsonMemoryManager()
        yield manager

    def test_add_and_get_memory(self, memory_manager):
        msg = Message(role="user", content="Test content", timestamp=datetime.now())
        memory_manager.add_memory(msg)
        
        memories = memory_manager.get_memory()
        assert len(memories) == 1
        assert memories[0].content == "Test content"
        assert memories[0].role == "user"

    def test_save_and_load_memory(self, memory_manager):
        msg = Message(role="system", content="Persist me", timestamp=datetime.now())
        memory_manager.add_memory(msg)
        
        save_path = Path("test_memory.json")
        memory_manager.save_memory(save_path)
        
        assert save_path.exists()
        
        memory_manager.clear_memory()
        assert len(memory_manager.get_memory()) == 0
        
        memory_manager.load_memory(save_path)
        loaded = memory_manager.get_memory()
        
        assert len(loaded) == 1
        assert loaded[0].content == "Persist me"
        assert isinstance(loaded[0].timestamp, datetime)

        save_path.unlink()