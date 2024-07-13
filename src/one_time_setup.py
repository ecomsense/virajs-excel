import os
import platform
import venv
import sys
import traceback

def create_venv_folder(folder_path):
    venv_folder = os.path.join(folder_path, "venv")
    if not os.path.exists(venv_folder):
        os.makedirs(venv_folder)
    else:
        print("Folder Already exists...")
    return venv_folder

def create_virtualenv(venv_folder_path):
    venv.create(venv_folder_path, with_pip=True)

def get_envPath(venv_folder_path):
    system_os = platform.system()
    if system_os == "Windows":
        activate_script = os.path.join(os.path.abspath(venv_folder_path), "Scripts", "activate")
    else:
        activate_script = os.path.join(venv_folder_path, "bin", "activate")
    return activate_script

def install_requirements(venv_folder_path, requirements_file_path):
    env = get_envPath(venv_folder_path)
    print("Please wait for 1-2 mins to install all dependencies")
    os.system(f"{env} && pip install -r {requirements_file_path}")
    print("dependencies installed successfully")



if __name__ == "__main__":
    try:
        folder_path = "../../"
        venv_folder_path = create_venv_folder(folder_path)
        create_virtualenv(os.path.abspath(venv_folder_path))
        requirements_file_path = "../requirements.txt"
        install_requirements(venv_folder_path, requirements_file_path)
    except:
        traceback.print_exc()