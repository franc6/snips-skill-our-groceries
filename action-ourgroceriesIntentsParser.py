#!/usr/bin/env python3
import gettext
import json
import locale
import re
from subprocess import Popen, PIPE, STDOUT
import sys

import our_groceries_client

from snipskit.hermes.apps import HermesSnipsApp
from snipskit.config import AppConfig
from snipskit.hermes.decorators import intent

# Set up localse
locale.setlocale(locale.LC_ALL, '')
# Set gettext to be the right thing for python2 and python3
if sys.version_info[0] < 3:
    gettext = gettext.translation('messages', localedir='locales').ugettext
else:
    gettext.bindtextdomain('messages', 'locales')
    gettext = gettext.gettext

class OurGroceriesApp(HermesSnipsApp):
    injection_lock = False
    #injection_timer = RepeatTimer(3600, self.inject_lists_and_items, self)

    @intent('franc:addToList')
    def add_to_list(self, hermes, intent_message):
        if self.injection_lock:
            sentence = gettext("STR_UPDATING_WAIT_ADD")
            hermes.publish_end_session(intent_message.session_id, sentence)
            return

        quantity = 1
        what = None
        which_list = None
        if intent_message.slots is not None:
            try:
                what = intent_message.slots.what[0].raw_value
            except (TypeError, LookupError, ValueError):
                pass
            try:
                which_list = intent_message.slots.list[0].slot_value.value.value
            except (TypeError, LookupError, ValueError):
                pass
            try:
                quantity = int(float(intent_message.slots.quantity[0].slot_value.value.value))
            except (TypeError, LookupError, ValueError):
                pass

        # Set whichList to defaultlist if it's None or matches
        # gettext("STR_DEFAULT_LIST") The API would use the same list if we
        # passed None, but the code below would fail when giving the
        # response.
        if (which_list is None) or \
           (which_list.casefold() == gettext("STR_DEFAULT_LIST").casefold()):
            which_list = self.config['secret']['defaultlist']

        if what is None:
            sentence = gettext("STR_ADD_MISSING_WHAT").format(l=which_list)
            hermes.publish_end_session(intent_message.session_id, sentence)
            return

        client = our_groceries_client.OurGroceriesClient()
        client.authenticate(self.config['secret']['username'],
                            self.config['secret']['password'],
                            self.config['secret']['defaultlist'])
        client.add_to_list(what, quantity, which_list)

        # Respond that we added it to the list
        sentence = gettext("STR_ADD_SUCCESS_DETAILS") \
            .format(q=quantity, w=what, l=which_list)
        hermes.publish_end_session(intent_message.session_id, sentence)

    @intent('franc:checkList')
    def check_list(self, hermes, intent_message):
        if self.injection_lock:
            sentence = gettext("STR_UPDATING_WAIT_ADD")
            hermes.publish_end_session(intent_message.session_id, sentence)
            return

        sentence = None
        quantity = '1'
        what = None
        which_list = None
        if intent_message.slots is not None:
            try:
                what = intent_message.slots.what[0].raw_value
            except (TypeError, LookupError, ValueError):
                pass
            try:
                which_list = intent_message.slots.list[0].slot_value.value.value
            except (TypeError, LookupError, ValueError):
                pass

        # Set whichList to defaultlist if it's None or matches
        # gettext("STR_DEFAULT_LIST") The API would use the same list if we
        # passed None, but the code below would fail when giving the
        # response.
        if (which_list is None) or \
           (which_list.casefold() == gettext("STR_DEFAULT_LIST").casefold()):
            which_list = self.config['secret']['defaultlist']

        if what is None:
            sentence = gettext("STR_CHECK_MISSING_WHAT").format(l=which_list)
            hermes.publish_end_session(intent_message.session_id, sentence)
            return

        client = our_groceries_client.OurGroceriesClient()
        client.authenticate(self.config['secret']['username'],
                            self.config['secret']['password'],
                            self.config['secret']['defaultlist'])
        items = client._get_list_data(which_list)
        for item in items:
            crossed_off = item.get('crossedOff', False)
            # Note our two primary regular expressions are commented out
            # below and combined into regex.  The uncommented regex line
            # below this is just building the expression all at once.
            #regex1 = r"^" + re.escape(what) + r" *$"
            #regex2 = r"^" + re.escape(what) + r"\ \((\d+)\)$"
            #regex = r"(" + regex1 + r")|(" + regex2 + r")"
            regex = r'(^' + re.escape(what) + r' *$)|(^' + re.escape(what) + r'\ \((\d+)\)$)'
            res = re.search(regex, item['value'], re.IGNORECASE)
            # Note the following two conditions are not combined because we
            # want to break the loop even if the item is crossed off.  If
            # it's crossed off, we don't need to keep looking for a match --
            # you can't have the same item on the list with different case.
            # Perhaps with different spelling, but we're not doing sounds
            # like checking here. :(
            if res is not None:
                if not crossed_off:
                    quantity = res.group(3)
                    if quantity is None:
                        quantity = '1'
                    sentence = gettext("STR_CHECK_SUCCESS_DETAILS") \
                        .format(q=quantity, w=what, l=which_list)
                break

        if sentence is None:
            sentence = gettext("STR_CHECK_NOT_FOUND").format(w=what, l=which_list)

        # Respond that we added it to the list
        hermes.publish_end_session(intent_message.session_id, sentence)

    def initialize(self):
        self.inject_lists_and_items()
        #self.injection_timer.start()

    def get_items_payload(self, client, list_names):
        item_names = []
        for list_name in list_names:
            items = client._get_list_data(list_name)
            for item in items:
                item_names.append(item['value'])
        item_names = list(set(item_names))
        return ['addFromVanilla', {'our_groceries_item_name': item_names}]

    def get_lists_payload(self, list_names):
        return ['addFromVanilla', {'our_groceries_list_name': list_names}]

    def get_update_payload(self):
        operations = []
        client = our_groceries_client.OurGroceriesClient()
        client.authenticate(self.config['secret']['username'],
                            self.config['secret']['password'],
                            self.config['secret']['defaultlist'])

        list_names = []
        for list_info in client._lists:
            list_names.append(list_info['name'])

        operations.append(self.get_lists_payload(list_names))
        operations.append(self.get_items_payload(client, list_names))
        payload = {'operations': operations}
        return json.dumps(payload)

    def inject_lists_and_items(self):
        self.injection_lock = True
        payload = self.get_update_payload() + '\n'
        pipe = Popen(['/usr/bin/mosquitto_pub',
                      '-t',
                      'hermes/injection/perform',
                      '-l'
                      ],
                     stdin=PIPE,
                     stdout=PIPE,
                     stderr=STDOUT)
        pipe.communicate(input=payload.encode('utf-8'))
        self.injection_lock = False

if __name__ == "__main__":
    OurGroceriesApp(config=AppConfig())
