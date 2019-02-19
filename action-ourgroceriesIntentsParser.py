#!/usr/bin/env python2

from hermes_python.hermes import Hermes
from hermes_python.ontology import *
from io import open
from subprocess import check_output, STDOUT
import our_groceries_client
import ConfigParser
import json
import re

CONFIG_INI = "/usr/share/snips/assistant/snippets/franc.Our_Groceries/config.ini"
CONFIG_ENCODING = "utf-8"
config = None

class SnipsConfigParser(ConfigParser.SafeConfigParser):
    def to_dict(self):
        return {section: {option_name : option for option_name, option in self.items(section)} for section in self.sections()}

def readConfigurationFile(fileName):
    try:
        with open(fileName, encoding=CONFIG_ENCODING) as f:
            confParser = SnipsConfigParser()
            confParser.readfp(f)
            return confParser.to_dict()
    except (IOError, ConfigParser.Error) as e:
        return dict()

def getListsPayload(hermes):
    config = readConfigurationFile(CONFIG_INI)
    client = our_groceries_client.OurGroceriesClient()
    client.authenticate(config['secret']['username'], config['secret']['password'], config['secret']['defaultlist'])
    listNames = []
    for listInfo in client._lists:
        listNames.append(listInfo['name'])

    operation = [ 'addFromVanilla', { 'our_groceries_list_name': listNames }];
    operations = [ operation ]
    payload = { 'operations': operations }
    return json.dumps(payload)

def addToList(hermes, intentMessage):
    quantity = 1
    what = None
    whichList = None
    for (slot_value, slot) in intentMessage.slots.items():
        if (slot_value == 'what'):
            what = slot[0].raw_value
        elif (slot_value == 'list'):
            whichList = slot[0].slot_value.value.value
        elif (slot_value == 'quantity'):
            quantity = int(float(slot[0].slot_value.value.value))
    if (what is None):
        print "Nothing to add!"
        return
    # Set whichList to defaultlist if it's None or matches 'our groceries'
    # The API would use the same list if we passed None, but the code below
    # would fail when giving the response.
    if (whichList is None) or (whichList == 'our groceries'):
        whichList = config['secret']['defaultlist']

    config = readConfigurationFile(CONFIG_INI)
    client = our_groceries_client.OurGroceriesClient()
    client.authenticate(config['secret']['username'], config['secret']['password'], config['secret']['defaultlist'])
    client.add_to_list(what, quantity, whichList)

    # Respond that we added it to the list
    sentence = 'Added ' + str(quantity) + " " + what + "to " + whichList
    hermes.publish_end_session(intentMessage.session_id, sentence)

def checkList(hermes, intentMessage):
    quantity = '1'
    what = None
    whichList = None
    sentence = None
    for (slot_value, slot) in intentMessage.slots.items():
        if (slot_value == 'what'):
            what = slot[0].raw_value
        elif (slot_value == 'list'):
            whichList = slot[0].slot_value.value.value
    if (what is None):
        print "Nothing to check for!"
        return
    # Set whichList to defaultlist if it's None or matches 'our groceries'
    # The API would use the same list if we passed None, but the code below
    # would fail when giving the response.
    if (whichList is None) or (whichList == 'our groceries'):
        whichList = config['secret']['defaultlist']

    config = readConfigurationFile(CONFIG_INI)
    client = our_groceries_client.OurGroceriesClient()
    client.authenticate(config['secret']['username'], config['secret']['password'], config['secret']['defaultlist'])
    items = client._get_list_data(whichList)
    for item_data in items:
        crossedOff = item_data.get('crossedOff', False)
        if (re.sub(r"[0-9|\(|\)\w]", "", item_data['value'].upper()) == re.sub(r"[\w]", "", what.upper())) and not crossedOff:
            res = re.search(what + "\(({})\)", item_data['value'])
            if res is not None:
                quantity = res.group(1)
            else:
                quantity = "1"
                sentence = "There are " + quantity + " " + what + " on the " + whichList + " list."
            break
    if sentence is None:
        sentence = what + " is not on the " + whichList + " list."

    # Respond that we added it to the list
    hermes.publish_end_session(intentMessage.session_id, sentence)

def updateLists(hermes):
    payload = getListsPayload(hermes)
    result = check_output(['/usr/bin/mosquitto_pub', '-t', 'hermes/injection/perform', '-m', payload], stderr=STDOUT)

def intentCallback(hermes, intentMessage):
    if intentMessage.intent.intent_name == 'franc:addToList':
        addToList(hermes, intentMessage)
    elif intentMessage.intent.intent_name == 'franc:checkList':
        checkList(hermes, intentMessage)

if __name__=="__main__":
    with Hermes("localhost:1883") as h:
        updateLists(h)
        h.subscribe_intents(intentCallback).start()

# TODO: Need to find a way to periodically invoke updateLists
