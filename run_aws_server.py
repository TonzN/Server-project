import subprocess
import os

key = os.path.expanduser(r"~\.ssh\id_ed25519")

subprocess.run([
    "cmd",
    "/c",
    "start",
    "cmd",
    "/k",
    f'ssh -i "{key}" administrator@85.190.97.54'
])