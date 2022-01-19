# joi-skill-music

## Install Skill
From the Raspberry Pi 
    mycroft-msm https://github.com/TySeddon/joi-skill-music.git

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


## Update requirements.txt

    pip freeze > requirements.txt

## Load Required Packages
Create your virtual environment, then load all the required dependencies with:

    pip install -r requirements.txt
