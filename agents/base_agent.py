"""
Base Agent - Foundation for all specialized agents.
"""
from datetime import datetime

class BaseAgent:
    def __init__(self, name, model_router=None, vector_db=None):
        self.name = name
        self.model_router = model_router
        self.vector_db = vector_db

    def log(self, message, level='INFO'):
        """Unified logging for agents."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        icons = {'INFO': 'ℹ️', 'SUCCESS': '✅', 'ERROR': '❌', 'WARN': '⚠️'}
        icon = icons.get(level, 'ℹ️')
        print(f"  {icon} [{self.name}] {message}")

    def execute_safe(self, *args, **kwargs):
        """Wrapper to catch and log execution errors gracefully."""
        self.log("Starting execution", 'INFO')
        try:
            result = self.execute(*args, **kwargs)
            self.log("Completed successfully", 'SUCCESS')
            return result
        except Exception as e:
            self.log(f"Execution failed: {e}", 'ERROR')
            return None

    def execute(self, *args, **kwargs):
        """Override this in child agents."""
        raise NotImplementedError

    def validate_input(self, data):
        """Basic input validation."""
        if not data:
            self.log("No input data provided", 'WARN')
            return False
        return True