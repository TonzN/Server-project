import subprocess

for i in range(2):
    subprocess.Popen(
        ["cmd", "/K", "python", "main.py"],
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    )

        