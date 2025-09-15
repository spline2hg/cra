"""Example file with security and complexity issues for testing major refactoring."""

import os
import pickle
import subprocess
from typing import Any, Dict

import yaml


class SecurityProblems:
    """Class with various security and complexity issues."""

    def __init__(self, config_file: str):
        self.config_file = config_file
        self.data = {}

    def load_config_insecure(self):
        """Load configuration with security issues."""
        # Pickle usage - security risk
        with open(self.config_file, "rb") as f:
            self.data = pickle.load(f)

    def execute_command_insecure(self, user_input: str):
        """Execute system command - major security risk."""
        #subprocess with shell=True
        result = subprocess.run(f"ls {user_input}", shell=True, capture_output=True)
        return result.stdout

    def get_password_insecure(self):
        """Get password insecurely."""
        # Hardcoded password
        password = "admin123"
        return password

    def broad_exception_handling(self, filename: str):
        """Function with overly broad exception handling."""
        try:
            with open(filename, "r") as f:
                data = yaml.safe_load(f)
                return self.process_data(data)
        except Exception as e:
            print(f"Something went wrong: {e}")
            return None


def sql_injection_risk(user_id: str):
    """Function with potential SQL injection."""
    query = f"SELECT * FROM users WHERE id = {user_id}"
    return query


def eval_usage(user_code: str):
    """Dangerous eval usage."""
    return eval(user_code)


# Global variables that could be security risks
SECRET_KEY = "hardcoded-secret-key-123"
API_TOKEN = "sk-1234567890abcdef"


if __name__ == "__main__":
    # Example usage with security issues
    app = SecurityProblems("config.pkl")
    app.load_config_insecure()

    user_input = input("Enter directory: ")
    app.execute_command_insecure(user_input)
