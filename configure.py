"""Configure pre-commit hooks."""

import subprocess
import sys

subprocess.run([sys.executable, "-m", "pip", "install", "pre-commit"], check=True)
print("pre-commit version:")
subprocess.run(["pre-commit", "--version"], check=True)
print("python version:")
subprocess.run([sys.executable, "--version"], check=True)

subprocess.run(["pre-commit", "install"], check=True)
