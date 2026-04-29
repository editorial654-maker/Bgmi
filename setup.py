import os
import zipfile
import subprocess
import sys

def run_command(command, cwd=None):
    print(f"Running: {command}")
    try:
        subprocess.check_call(command, shell=True, cwd=cwd)
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {e}")

def main():
    # 1. Unzip the folder
    if os.path.exists('Dipak.zip'):
        print("Extracting Dipak.zip...")
        with zipfile.ZipFile('Dipak.zip', 'r') as zip_ref:
            zip_ref.extractall('.')
    else:
        print("Error: Dipak.zip not found!")
        return

    # 2. Install dependencies
    print("Installing telebot...")
    run_command(f"{sys.executable} -m pip install telebot")

    # 3. Change directory and run
    # Note: chmod +x is often not needed for .py files in cloud environments
    # but we will ensure the files are accessible.
    folder = 'Dipak'
    if os.path.isdir(folder):
        print(f"Entering {folder} and starting m.py...")
        
        # Give permissions to everything in the folder
        for root, dirs, files in os.walk(folder):
            for f in files:
                os.chmod(os.path.join(root, f), 0o755)
        
        # Change directory and run the script
        os.chdir(folder)
        run_command(f"{sys.executable} m.py")
    else:
        print(f"Error: Folder '{folder}' not found after unzipping.")

if __name__ == "__main__":
    main()
