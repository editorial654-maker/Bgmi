import subprocess
import os
import sys

def run_command(command):
    """Executes a shell command and prints output."""
    print(f"Executing: {command}")
    try:
        # shell=True is used here to match the behavior of a terminal
        subprocess.run(command, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error occurred while executing: {command}\n{e}")
        sys.exit(1)

def main():
    # 1. Unzip the file
    if os.path.exists('Dipak.zip'):
        run_command("unzip -o 'Dipak.zip'")
    else:
        print("Error: Dipak.zip not found!")
        return

    # 2. Change directory and perform actions
    # Note: We use the path directly because cd in a subprocess 
    # doesn't persist to the next subprocess call.
    folder_name = 'Dipak'
    
    if os.path.isdir(folder_name):
        # Install telebot
        run_command("pip install telebot")
        
        # Change permissions (chmod +x) for all files inside the folder
        run_command(f"chmod +x {folder_name}/*")
        
        # 3. Run the python script m.py inside the folder
        print(f"Moving into {folder_name} and starting m.py...")
        os.chdir(folder_name)
        run_command("python m.py")
    else:
        print(f"Error: Folder {folder_name} was not created after unzipping.")

if __name__ == "__main__":
    main()
