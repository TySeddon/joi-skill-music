import yaml

def get_setting(key, resident_id=None):
    if resident_id is None:
        # if we are trying to lookup an environment key (not specific to resident)
        with open("enviro.yaml", 'rt') as stream:
            config = yaml.safe_load(stream.read())
            return config[key]
    else:
        # if we are trying to lookup a key specific to resident
        with open(f"{resident_id}.yaml", 'rt') as stream:
            config = yaml.safe_load(stream.read())
            return config[key]

