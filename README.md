## Introduction
this app is for semi-automatic trading with zerodha. This is tested on python>3.9 and <=3.12.0. 

## Setup
### 1. Setup your broker account
setup TOTP for your zerodha account. This is necessary to programatically access your broker account and do trade functions.
copy the alpha numeric representation of TOTP to your clipboard, as mentioned in step 13.8 of [zerodha totp setup](https://support.zerodha.com/category/your-zerodha-account/login-credentials/login-credentials-of-trading-platforms/articles/time-based-otp-setup). Remember to store this TOTP code from clipboard to some file in your system. We will need it later.

### 2. Install python 3.9.13 or version 3.12 below or equal to python 3.9.0.
you need to download [python 3.9.13](https://www.python.org/downloads/release/python-3913/) and install the appropriate version for your operating system.

### 3. Install git 
[Git](https://git-scm.com/) is required so you can clone any Github repository. We also need it to provide continuous integration and delivery. Usually you need to download [64-bit version of Git](https://github.com/git-for-windows/git/releases/download/v2.44.0.windows.1/Git-2.44.0-64-bit.exe)
The default choice of installation is fine for most cases. You may opt out from experimental features, while installing Git

### 4. Download this repository from Github 
```
# you can give any folder name & create new folder in any folder.

mkdir C:\ecomsense\
cd C:\ecomsense
mkdir terminal
cd terminal
git clone https://github.com/ecomsense/virajs-excel.git
```
if successful, you should be able to see a new directory `virajs-excel` under the current directory `ecomsense`


## 5. To setup project.
There are two options available if one not work then you can try with another
### 1. Script to setup project dependencies/libraries.
```
cd viraj-excel
```
run `one_time_setup.bat` and wait for sometime to complete the download.

## OR

### 2. prepare the `virtualenv`
Virtualenv is a method to contain the python program, so that the system python is not disturbed in any way.
Create the necessary directories and set up the virtual environment.
```
# you can give any folder name
cd C:\ecomsense\terminal
python -m venv venv
```

#### 1. Activate the environment
issue the below command from `terminal` folder
```
venv\Scripts\activate
```
this will activate the virtual environment. Notice that the prompt is now prepended with `(venv)`


#### 2. Install dependencies
Our program is dependent on several packages to run properly. You need to install them before we are able to run it.
```
cd virajs-excel
pip install -r requirements.txt
```

### 6. Run the application
Before we run the application, the credential file needs to be created. Please copy the `virajs-excel.yml` sent to you through whatsapp to `terminal` folder which you created in earlier. Modify it suitably according to your stock broker credentials.
```
cd src
python main.py
```

### 7. Create Shortcuts
There are two bat files `run_algo.bat` and `update.bat` in this folder `virajs-excel`. create desktop shortcuts for them. This way one can run the program by clicking on the `run_algo` without having to run complicated commands from the command line. The `update` shortcut can be clicked whenever the user wants to get the latest updates.

## What do we need to do start the program
If we have successfully installed the application, clicking on the `run_algo` will start the program. It is basically an one liner which activates the virtualenv and starts the python script `main.py` which is inside `terminal\virajs-excel\src`
 
