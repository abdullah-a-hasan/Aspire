# Aspire: an MT-based  bilingual corpus aligner
### *Create translation memories from bilingual content*

Aspire is a translation alignment tool that creates translation memories from a source and a target text based on machine translation.

Aspire can be used as a web app or a command-line program. Each implementation has its own features and limitations.


## Aspire as a web app
### Security warning
Make sure to add and change usernames and passwords as needed by modifying ```apsire_web_app\users.py```. Password will be visible in the code. The web app runs on lacalhost by default. If you need to make the app publically accessible, it's your responsibility to set up a secure connection (HTTPS) between the user and the local app. The web app itself does not provide any encryption or security features.

### Features
* Align plain text or provide source and target URLs to align web pages
* Easily choose alignment algorithm and fine-tune parameters 
* Segmentation is automatic and can be customized by modifying the default SRX file: ```apsire_web_app/web_dynamic/py_srx_segmenter/default_rules.srx```
* Export TMX or XLS translation memories
* Review alignments to approve or reject pairs
* View alignment scores
### Limitations
* One alignment operation at a time
* Basic user authentication

### Installing the web app
## General requirements
###### Google Translate API
Aspire's web app uses the Google Cloud Translate API, which is a paid service by Google. **You are responsible for defining your own spending limits and usage quotas.** To proceed with account setup, follow these steps:
1. Create a [Google Cloud](https://cloud.google.com/) account
2. Create a project and enable the Google Cloud Translate API.
3. Follow [these steps](https://cloud.google.com/iam/docs/creating-managing-service-account-keys#iam-service-account-keys-create-console) to obtain a JSON file containing authentication credentials.
4. Rename the JSON file and store it in ```apsire_web_app/web_dynamic/google_trans_api_auth/creds.json```
###### Python 3.8 on Windoes 10 or Ubuntu 20.04
Other versions may work but were not tested.

## Installing on Windows 10
In addition to Python 3.8, you need to install [Microsoft Build Tools 2015 Update 3](https://visualstudio.microsoft.com/vs/older-downloads/). Scroll down to *Other Tools, Frameworks, and Redistributables* to find it.
After installing the build tools, start the Windows Command Prompt in Aspire's root folder and run:
```
python -m venv asp-env
call asp-env\Scripts\activate.bat
pip install wheel==0.36.2
pip install -r apsire_web_app\requirements.txt
pip install -r aspire_aligner\requirements.txt
```
## Running on Windows 10
```
call asp-env\Scripts\activate.bat
cd apsire_web_app
set FLASK_APP=flask_app.py
python -m flask run
```

## Installing on Ubuntu 20.04.1
cd into Aspire's root folder, then run the following commands:
```
sudo apt-get install python3-venv build-essential python3-dev
python3 -m venv asp-env
source asp-env/bin/activate
pip install wheel==0.36.2
pip install cython==0.29.21
pip install -r apsire_web_app/requirements.txt
pip install -r aspire_aligner/requirements.txt
```
## Running on Ubuntu
```
source asp-env/bin/activate
cd apsire_web_app
export FLASK_APP=flask_app.py
python3 -m flask run
```
## Using the web app
Warning: refer to the security section above.
Point the browser to the default URL, typically: http://127.0.0.1:5000/
Use one of the username/password combinations you entered in ```apsire_web_app\users.py```

## Aspire as a command line tool
### Features
* Align multiple plain text files
* Names of source, target, and MT files can be read from an Excel sheet
* Segmentation is automatic and can be customized using an SRX file
* Export TMX or XLS translation memories
* Can be built and utilized by other applications.

### Limitations
* For advanced users
* Does not offer segmentation. Plain text files need to be pre-segmented.
* Does not automatically fetch machine translation. Machine translation should be provided as a plain text file.

### Usage
Create a virtual environment and install ```requirements.txt```.

Then run ```python aspire_aligner\main.py -h``` for usage information.

### Learn more
This tool was presented at the Kent State University Translation in Transition conference.
For information about accuracy, refer to the [conference abstract](https://devrobgilb.com/Files/TT5_Oct_2020_BookOfAbstracts.pdf). 
