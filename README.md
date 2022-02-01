# joi-skill-music

## Managing Skill Installations
All of these Mycroft kills Manager (mycroft-msm) commands are executed on the Raspberry Pi

### Install Skill
    cd ~/mycroft-core/bin
    ./mycroft-msm install https://github.com/TySeddon/joi-skill-music.git

### Remove Skill    
    cd ~/mycroft-core/bin
    ./mycroft-msm remove joi-skill-music

### Bash Script to automate updating of skills
In home director create file called update-skills.sh
    #!/bin/sh
    cd ~/mycroft-core/bin
    echo "----Uninstalling joi-skill-music----"
    ./mycroft-msm remove joi-skill-music
    echo "----Installing joi-skill-music----"
    ./mycroft-msm install https://github.com/TySeddon/joi-skill-music.git

Make script executable and writeable
    sudo chmod a+xw update-skills.sh

## One-Time Raspberry Pi setup
    cd ~/mycroft-core        
    source venv-activate.sh  
    pip install munch
    pip install spotipy==2.19.0


### Chrome Configure

#### Install “chrome widevine”
This upgrades browser on Raspberry Pi so that it can play Spotify
    sudo apt update
    sudo apt install libwidevinecdm0    
    sudo reboot

#### Allow Sound to Auto Play
Chromse does not allow videos to automatically play (autoplay).  This can be overridden in settings.
1. Open chrome
2. In URL type "chrome://settings/content/sound"
3. Under "Customized behaviors", "Allowed to play sound", click "Add" button
4. Enter the URLs that are allowed to auto play.
    * localhost:8000
    * 127.0.01:8000
    * joi-test-site.azurewebsites.net

#### Play Protectect Content
1. In your browser address bar, enter chrome://settings/content
2. Under Protected content, switch on Allow site to play protected content.


## Mycroft Terminology

* **utterance** - An utterance is a phrase spoken by the User, after the User says the Wake Word. what's the weather like in Toronto? is an utterance.
* **dialog** - A dialog is a phrase that is spoken by Mycroft. Different Skills will have different dialogs, depending on what the Skill does. For example, in a weather Skill, a dialog might be the.maximum.temperature.is.dialog.
* **intent** - Mycroft matches utterances that a User speaks with a Skill by determining an intent from the utterance. For example, if a User speaks Hey Mycroft, what's the weather like in Toronto? then the intent will be identified as weather and matched with the Weather Skill. When you develop new Skills, you need to define new intents.

## Virtual Environment Setup

### Install Virtual Environment
    pip install virtualenv

### Creating 
    python -m venv venv

### Activate Virtual Environment
    .\venv\Scripts\activate

# Required Packages
    pip install msk
    pip install adapt-parser
    pip install munch
    pip install spotipy


## Update requirements.txt
    pip freeze > requirements.txt

## Load Required Packages
Create your virtual environment, then load all the required dependencies with:
    pip install -r requirements.txt
