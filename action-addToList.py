#!/usr/bin/env python2

from hermes_python.hermes import Hermes
from hermes_python.ontology import *
from io import open
from subprocess import Popen, PIPE, STDOUT
import our_groceries_client
import ConfigParser
import json

CONFIG_INI = "/usr/share/snips/assistant/snippets/franc.Our_Groceries/config.ini"
CONFIG_ENCODING = "utf-8"

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

    operation = [ 'add', { 'our_groceries_list_name': listNames }];
    operations = [ operation ]
    payload = { 'operations': operations }
    return json.dumps(payload)

def addToList(hermes, intentMessage):
    # Dump the intent's slots for debugging purposes
    for (slot_value, slot) in intentMessage.slots.items():
        print('Slot {} -> \n\tRaw: {} \tValue: {}'.format(slot_value, slot[0].raw_value, slot[0].slot_value.value.value))

    what = intentMessage.slots.what.first().raw_value
    list = intentMessage.slots.list.first().raw_value
    quantity = intentMessage.slots.quantity.first().slot_value.value.value
    config = readConfigurationFile(CONFIG_INI)
    client = our_groceries_client.OurGroceriesClient()
    client.authenticate(config['secret']['username'], config['secret']['password'], config['secret']['defaultlist'])
    client.add_to_list(what, int(float(quantity)), list)
    sentence = 'Added ' + quanity + " " + what + "to " + list
    hermes.publish_end_session(intentMessage.session_id, sentence)

if __name__=="__main__":
    with Hermes("localhost:1883") as h:
        payload = getListsPayload(h)
        print("Dumping payload: " + payload)
        p = Popen(['/usr/bin/mosquitto_pub', '-t', 'hermes/injection/perform', '-m', payload], stdout=PIPE, stdin=PIPE, stderr=STDOUT)
        output = p.communicate()[0]
        print(output)
        h.subscribe_intent("franc:addToList",addToList).start()

