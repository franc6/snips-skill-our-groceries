#!/usr/bin/env python2
"""Snips skill action.

Subscribes to franc:addToList and franc:checkList intents and processes them.
"""
import ConfigParser
from io import open
import json
import re
from subprocess import Popen, PIPE, STDOUT
from threading import Timer
from hermes_python.hermes import Hermes
from hermes_python.ontology import *
import our_groceries_client

CONFIG_INI = "config.ini"
CONFIG_ENCODING = "utf-8"
__all__ = []


class RepeatTimer(object):
    """Class to repeatedly run a given function via a timer"""
    def __init__(self, interval, function, *args, **kwargs):
        """Initialize the object

        interval: Time between running, in seconds
        function: A function to call when the timer goes off
        args, kwargs: The arguments to pass to function
        """
        self._timer = None
        self.interval = interval
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.is_running = False

    def _run(self):
        """_run is called when the timer goes off, and invokes self.function"""
        self.is_running = False
        self.start()  # Start the timer again!
        self.function(*self.args, **self.kwargs)

    def start(self):
        """Checks that the timer isn't running, and if not, creates a timer,
           and starts it"""
        if not self.is_running:
            self._timer = Timer(self.interval, self._run)
            self._timer.start()
            self.is_running = True

    def stop(self):
        """Kills the timer"""
        if self.is_running:
            if self._timer is not None:
                self._timer.cancel()
            self.is_running = False


class SnipsConfigParser(ConfigParser.SafeConfigParser):
    """Subclass ConfigParser.SafeConfigParser to add to_dict method."""
    def to_dict(self):
        """Returns a dictionary of sections and options from the config file"""
        return {section: {option_name : option for option_name,
                          option in self.items(section)} for section in self.sections()}


def read_configuration_file(file_name):
    """Reads and parses CONFIG_INI.  Returns a dictionary based on its contents"""
    try:
        with open(file_name, encoding=CONFIG_ENCODING) as file:
            config_parser = SnipsConfigParser()
            config_parser.readfp(file)
            return config_parser.to_dict()
    except (IOError, ConfigParser.Error):
        return dict()

def get_items_payload(client, list_names):
    """Gets all items from the given lists, and formats them for injection"""
    item_names = []
    for list_name in list_names:
        items = client._get_list_data(list_name)
        for item in items:
            item_names.append(item['value'])
    item_names = list(set(item_names))
    return ['addFromVanilla', {'our_groceries_item_name': item_names}]

def get_lists_payload(list_names):
    """Formats the given list names as needed for injection"""
    return ['addFromVanilla', {'our_groceries_list_name': list_names}]

def get_update_payload(hermes):
    """Retrives list names and items names, formatting them for injection"""
    operations = []
    client = our_groceries_client.OurGroceriesClient()
    client.authenticate(hermes.skill_config['secret']['username'],
                        hermes.skill_config['secret']['password'],
                        hermes.skill_config['secret']['defaultlist'])

    list_names = []
    for list_info in client._lists:
        list_names.append(list_info['name'])

    operations.append(get_lists_payload(list_names))
    operations.append(get_items_payload(client, list_names))
    payload = {'operations': operations}
    return json.dumps(payload)

def add_to_list(hermes, intent_message):
    """Adds the given item and quantity to the given list"""
    while hermes.doing_injection:
        sentence = \
            "I am updating your lists and will add your item in a moment."
        hermes.publish_continue_session(intent_message.session_id, sentence)
        sleep(10)
    quantity = 1
    what = None
    which_list = None
    if intent_message.slots:
        what = intent_message.slots.what[0].raw_value
        which_list = intent_message.slots.list[0].value.value
        quantity = int(float(intent_message.slots.quantity[0].value.value))
        #for (slot_value, slot) in intent_message.slots.items():
            #if slot_value == 'what':
                #what = slot[0].raw_value
            #elif slot_value == 'list':
                #which_list = slot[0].slot_value.value.value
            #elif slot_value == 'quantity':
                #quantity = int(float(slot[0].slot_value.value.value))
    if what is None:
        return
    # Set whichList to defaultlist if it's None or matches 'our groceries'
    # The API would use the same list if we passed None, but the code below
    # would fail when giving the response.
    if (which_list is None) or (which_list == 'our groceries'):
        which_list = hermes.skill_config['secret']['defaultlist']

    client = our_groceries_client.OurGroceriesClient()
    client.authenticate(hermes.skill_config['secret']['username'],
                        hermes.skill_config['secret']['password'],
                        hermes.skill_config['secret']['defaultlist'])
    client.add_to_list(what, quantity, which_list)

    # Respond that we added it to the list
    sentence = "I added {q} {w} to the {l} list.".format(q=quantity, w=what, l=which_list)
    hermes.publish_end_session(intent_message.session_id, sentence)

def check_list(hermes, intent_message):
    """Checks the given list for an item and speaks if it's there"""
    while hermes.doing_injection:
        sentence = "I am updating your lists and will check in a moment."
        hermes.publish_continue_session(intent_message.session_id, sentence)
        sleep(10)
        
    quantity = '1'
    what = None
    which_list = None
    sentence = None
    if intent_message.slots:
        what = intent_message.slots.what[0].raw_value
        which_list = intent_message.slots.list[0].value.value
        #for (slot_value, slot) in intent_message.slots.items():
            #if slot_value == 'what':
                #what = slot[0].raw_value
            #elif slot_value == 'list':
                #which_list = slot[0].slot_value.value.value
    if what is None:
        return
    # Set whichList to defaultlist if it's None or matches 'our groceries'
    # The API would use the same list if we passed None, but the code below
    # would fail when giving the response.
    if (which_list is None) or (which_list == 'our groceries'):
        which_list = hermes.skill_config['secret']['defaultlist']

    client = our_groceries_client.OurGroceriesClient()
    client.authenticate(hermes.skill_config['secret']['username'],
                        hermes.skill_config['secret']['password'],
                        hermes.skill_config['secret']['defaultlist'])
    items = client._get_list_data(which_list)
    for item in items:
        crossed_off = item.get('crossedOff', False)
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
            if not crossed_off:
                quantity = res.group(3)
                if quantity is None:
                    quantity = "1"
                sentence = "You have {q} {w} on the {l} list" \
                    .format(q=quantity, w=what, l=which_list)
            break
    if sentence is None:
        sentence = "{w} is not on the {l} list." \
            .format(w=what, l=which_list)

    # Respond that we added it to the list
    hermes.publish_end_session(intent_message.session_id, sentence)

def inject_lists_and_items(hermes):
    """ Injects the lists and items"""
    hermes.doing_injection = True
    payload = get_update_payload(hermes) + '\n'
    pipe = Popen(['/usr/bin/mosquitto_pub',
                  '-t',
                  'hermes/injection/perform',
                  '-l'
                  ],
                 stdin=PIPE,
                 stdout=PIPE,
                 stderr=STDOUT)
    pipe.communicate(input=payload.encode('utf-8'))
    hermes.doing_injection = False

def main(hermes):
    """main function"""
    hermes.skill_config = read_configuration_file(CONFIG_INI)
    hermes.doing_injection = False
    inject_lists_and_items(hermes)
    injection_timer = RepeatTimer(3600, inject_lists_and_items, hermes)
    injection_timer.start()
    hermes.subscribe_intent("franc:addToList", add_to_list) \
        .subscribe_intent("franc:checkList", check_list) \
        .loop_forever()
    # Note this isn't really necessary, but just in case loop_forever()
    # doesn't, we should kill the timer.
    injection_timer.stop()


if __name__ == "__main__":
    with Hermes("localhost:1883") as h:
        main(h)
