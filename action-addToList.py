#!/usr/bin/env python2

from hermes_python.hermes import Hermes
from hermes_python.ontology import *
import our_groceries_client
import ConfigParser

CONFIG_INI = "config.ini"
CONFIG_ENCODING = "utf-8"

class SnipsConfigParser(ConfigParser.SafeConfigParser):
    def to_dict(self):
        return {section: {option_name : option for option_name, option in self.items(section)} for section in self.sections()}

def readConfigurationFile(fileName):
    try:
        with io.open(fileName, encoding=CONFIG_ENCODING) as f:
            confParser = SnipsConfigParser()
            confParser.readfp(f)
            return confParser.to_dict()
    except (IOError, ConfigParser.Error) as e:
        return dict()

def addToList(hermes, intentMessage):
    what = intentMessage.slots.what.first().rawValue
    list = intentMessage.slots.list.first().rawValue
    quantity = intentMessage.slots.quantity.first().value()
    config = readConfigurationFile(CONFIG_INI)
    client = our_groceries_client.OurGroceriesClient()
    client.authenticate(config['secret']['username'], config['secret']['password'], config['secret']['defaultList'])
    client.add_to_list(what, int(float(quantity)), list)
    sentence = 'Added ' + quanity + " " + what + "to " + list
    hermes.publish_end_session(intent_message.session_id, sentence)

if __name__=="__main__":
    with Hermes("localhost:1883") as h:
        h.subscribe_intent("franc:addToList",addToList).start()

