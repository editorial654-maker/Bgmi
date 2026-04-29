import os
import zipfile
import subprocess
import sys
import shutil

def run_command(command, cwd=None):
    """Utility to run shell commands and stream output."""
    print(f"Executing: {command}")
    try:
        subprocess.check_call(command, shell=True, cwd=cwd)
    except subprocess.CalledProcessError as e:
        print(f"Error occurred: {e}")
        sys.exit(1)

def main():
    zip_file = "Dipak.zip"
    extract_to = "Dipak"
    
    # 1. Unzip 'Dipak.zip'
    if os.path.exists(zip_file):
        print(f"--- Unzipping {zip_file} ---")
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            zip_ref.extractall(".")
    else:
        print(f"Error: {zip_file} not found!")
        return

    # 2. Install telebot
    print("--- Installing dependencies ---")
    run_command(f"{sys.executable} -m pip install telebot")

    # 3. chmod +x * and run m.py
    if os.path.exists(extract_to):
        print(f"--- Setting permissions in {extract_to} ---")
        # Recursively give execute permissions
        for root, dirs, files in os.walk(extract_to):
            for f in files:
                os.chmod(os.path.join(root, f), 0o755)
        
        # 4. Change directory and run m.py
        print(f"--- Starting m.py inside {extract_to} ---")
        os.chdir(extract_to)
        # We use sys.executable to ensure we use the same python version
        run_command(f"{sys.executable} m.py")
    else:
        print(f"Error: Extraction folder '{extract_to}' not found.")

if __name__ == "__main__":
    main()
