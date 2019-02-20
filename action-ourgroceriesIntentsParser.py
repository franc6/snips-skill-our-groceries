#!/usr/bin/env python2

from hermes_python.hermes import Hermes
from hermes_python.ontology import *
from io import open
from subprocess import Popen, PIPE, STDOUT
import our_groceries_client
import ConfigParser
import json
import re

CONFIG_INI = "config.ini"
CONFIG_ENCODING = "utf-8"
config = None

class SnipsConfigParser(ConfigParser.SafeConfigParser):
    def to_dict(self):
        return {section: {option_name : option for option_name, option in self.items(section)} for section in self.sections()}

class HiddenPrints:
    def __enter__(self):
        self._original_stdout = sys.stdout
        sys.stdout = open(os.devnull, 'w')

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout.close()
        sys.stdout = self._original_stdout

def readConfigurationFile(fileName):
    try:
        with open(fileName, encoding=CONFIG_ENCODING) as f:
            confParser = SnipsConfigParser()
            confParser.readfp(f)
            return confParser.to_dict()
    except (IOError, ConfigParser.Error) as e:
        return dict()

def getItemsPayload(client, listNames):
    itemNames = []
    for listName in listNames:
        items = client._get_list_data(listName)
        for item in items:
            itemNames.append(item['value'])
    itemNames = list(set(itemNames))
    return [ 'addFromVanilla', { 'our_groceries_item_name': itemNames }];

def getListsPayload(listNames):
    return [ 'addFromVanilla', { 'our_groceries_list_name': listNames }];

def getUpdatePayload(hermes):
    operations = []
    client = our_groceries_client.OurGroceriesClient()
    client.authenticate(config['secret']['username'], config['secret']['password'], config['secret']['defaultlist'])

    listNames = []
    for listInfo in client._lists:
        listNames.append(listInfo['name'])

    operations.append(getListsPayload(listNames))
    operations.append(getItemsPayload(client, listNames))
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
        return
    # Set whichList to defaultlist if it's None or matches 'our groceries'
    # The API would use the same list if we passed None, but the code below
    # would fail when giving the response.
    if (whichList is None) or (whichList == 'our groceries'):
        whichList = config['secret']['defaultlist']

    client = our_groceries_client.OurGroceriesClient()
    client.authenticate(config['secret']['username'], config['secret']['password'], config['secret']['defaultlist'])
    client.add_to_list(what, quantity, whichList)

    # Respond that we added it to the list
    sentence = "Added {q} {w} to the {l} list.".format(q=quantity, w=what, l=whichList)
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
        return
    # Set whichList to defaultlist if it's None or matches 'our groceries'
    # The API would use the same list if we passed None, but the code below
    # would fail when giving the response.
    if (whichList is None) or (whichList == 'our groceries'):
        whichList = config['secret']['defaultlist']

    client = our_groceries_client.OurGroceriesClient()
    client.authenticate(config['secret']['username'], config['secret']['password'], config['secret']['defaultlist'])
    items = client._get_list_data(whichList)
    for item in items:
        crossedOff = item.get('crossedOff', False)
        # Note our two primary regular expressions are commented out below
        # and combined into regex.  The uncommented regex line below this
        # is just building the expression all at once.
        #regex1 = r"^" + re.escape(what) + r" *$"
        #regex2 = r"^" + re.escape(what) + r"\ \((\d+)\)$"
        #regex = r"(" + regex1 + r")|(" + regex2 + r")"
        regex = r"(^" + re.escape(what) + r" *$)|(^" + re.escape(what) + r"\ \((\d+)\)$)"
        res = re.search(regex, item['value'], re.IGNORECASE)
        # Note the following two conditions are not combined because we want to
        # break the loop even if the item is crossed off.  If it's crossed off,
        # we don't need to keep looking for a match -- you can't have the same
        # item on the list with different case.  Perhaps with different
        # spelling, but we're not doing sounds like checking here. :(
        if res is not None:
            if not crossedOff:
                quantity = res.group(3)
                if quantity is None:
                    quantity = "1"
                sentence = "There {v} {q} {w} on the {l} list".format(v="are" if int(quantity) > 1 else "is", q=quantity, w=what, l=whichList)
            break
    if sentence is None:
        sentence = "{w} is not on the {l} list.".format(w=what, l=whichList)

    # Respond that we added it to the list
    hermes.publish_end_session(intentMessage.session_id, sentence)

def updateLists(hermes):
    payload = getUpdatePayload(hermes) + '\n'
    p = Popen(['/usr/bin/mosquitto_pub', '-t', 'hermes/injection/perform', '-l'], stdin=PIPE, stdout=PIPE, stderr=STDOUT)
    stdout = p.communicate(input=payload.encode('utf-8'))[0]

def intentCallback(hermes, intentMessage):
    with HiddenPrints():
        if intentMessage.intent.intent_name == 'franc:addToList':
            addToList(hermes, intentMessage)
        elif intentMessage.intent.intent_name == 'franc:checkList':
            checkList(hermes, intentMessage)

if __name__=="__main__":
    config = readConfigurationFile(CONFIG_INI)
    with Hermes("localhost:1883") as h:
        updateLists(h)
        h.subscribe_intents(intentCallback).start()

# TODO: Need to find a way to periodically invoke updateLists
