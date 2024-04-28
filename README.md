## Introduction
this app is for semi-automatic trading with zerodha. This is tested on python>3.9 and <=3.10.0. 
  
### 1. Setup your broker account
setup TOTP for your zerodha account. This is necessary to programatically access your broker account and do trade functions.
copy the alpha numeric representation of TOTP to your clipboard, as mentioned in step 13.8 of [zerodha totp setup](https://support.zerodha.com/category/your-zerodha-account/login-credentials/login-credentials-of-trading-platforms/articles/time-based-otp-setup). Remember to store this TOTP code from clipboard to some file in your system. We will need it later.

### 2. Install python 3.9.13
you need to download [python 3.9.13](https://www.python.org/downloads/release/python-3913/) and install the appropriate version for your operating system.

### 3. Install git 
[Git](https://git-scm.com/) is required so you can clone any Github repository. We also need it to provide continuous integration and delivery. Usually you need to download [64-bit version of Git](https://github.com/git-for-windows/git/releases/download/v2.44.0.windows.1/Git-2.44.0-64-bit.exe)
The default choice of installation is fine for most cases. You may opt out from experimental features, while installing Git


### 4. prepare the `virtualenv`
Virtualenv is a method to contain the python program, so that the system python is not disturbed in any way.
Create the necessary directories and set up the virtual environment.
```
mkdir C:\ecomsense\ # or you can give any folder name
cd C:\ecomsense
python -m venv env
cd env
```

### 5. Activate the environment
issue the below command from `env` folder
```
Scripts/activate
```
this will activate the virtual environment. Notice that the prompt is now prepended with `(env)`

### 6. Download this repository from Github 
```
git clone https://github.com/pannet1/virajs-excel.git
```
if successful, you should be able to see a new directory `virajs-excel` under the current directory `env`

### 7. Install dependencies
Our program is dependent on several packages to run properly. You need to install them before we are able to run it.
```
cd virajs-excel
pip install -r requirements.txt
```

### 8. Run the application
Before we run the application, the credential file needs to be created. Please copy the `excel-virajs.yml` sent to you through whatsapp and modify it suitably.
```

python main.py
```

