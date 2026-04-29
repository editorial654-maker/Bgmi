import os
import zipfile
import subprocess
import sys
import shutil

def run_command(command, cwd=None):
    """Helper to run shell commands."""
    try:
        subprocess.check_call(command, shell=True, cwd=cwd)
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {command}\n{e}")
        sys.exit(1)

def main():
    zip_filename = 'Dipak.zip'
    folder_name = 'Dipak'

    # 1. Unzip 'Dipak.zip'
    if os.path.exists(zip_filename):
        print(f"--- Extracting {zip_filename} ---")
        with zipfile.ZipFile(zip_filename, 'r') as zip_ref:
            zip_ref.extractall('.')
    else:
        print(f"Error: {zip_filename} not found in the current directory.")
        return

    # 2. Install telebot (pyTelegramBotAPI)
    # Using 'sys.executable -m pip' is the safest way to install in the current environment
    print("--- Installing telebot ---")
    run_command(f"{sys.executable} -m pip install telebot")

    # 3. chmod +x * inside the unzipped folder
    if os.path.exists(folder_name):
        print(f"--- Setting executable permissions in {folder_name} ---")
        # Recursively set +x permissions (rwxr-xr-x)
        for root, dirs, files in os.walk(folder_name):
            for f in files:
                os.chmod(os.path.join(root, f), 0o755)
            for d in dirs:
                os.chmod(os.path.join(root, d), 0o755)
        
        # 4. Run python m.py
        print(f"--- Launching m.py inside {folder_name} ---")
        # Change working directory to 'Dipak' and run 'm.py'
        os.chdir(folder_name)
        run_command(f"{sys.executable} m.py")
    else:
        print(f"Error: Folder '{folder_name}' was not created. Check the zip content.")

if __name__ == "__main__":
    main()
