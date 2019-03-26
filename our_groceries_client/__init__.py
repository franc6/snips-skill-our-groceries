import requests
import re
import json

class OurGroceriesClient:
    def __init__(self):
        self._session = requests.Session()
        self._team_id = ""
        self._lists = None
        self._default_list_name = None


    def authenticate(self, username, password, default_list=None):
        self._default_list_name = default_list

        headers = {
            'User-Agent':'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36',
            'Referer': 'https://www.ourgroceries.com/sign-in',
            'Origin': 'https://www.ourgroceries.com'
        }
        payload = {
            'emailAddress' : username,
            'action': 'sign-me-in',
            'password' : password,
            'staySignedIn' : 'on'
        }

        response = self._session.post('https://www.ourgroceries.com/sign-in', headers=headers, data=payload)
        #if response.status_code == 200:
            #print('[SUCCESS] authenticated')
        #else:
            #print('[ERROR] authentication failure. Status code {}'.format(response.status_code))

        self._get_team_id(self._get_lists)

    
    def _get_team_id(self, function_success):
        response = self._session.get('https://www.ourgroceries.com/your-lists/')
        if response.status_code == 200:
            #print('[SUCCESS] team id aquired')
            regex = "_teamId = \"([A-Za-z0-9]*)\""
            match = re.search(regex, response.text)
            self._team_id = match.group(1)
            #print("teamId is now set to: {}".format(self._team_id))
            function_success()
        #else:
            #print('[ERROR] Unable to get teamId. Status code {}'.format(response.status_code))
        

    # {"recipes":[],"shoppingLists":[{"activeCount":0,"name":"Duane Reade","id":"IiYWzpD8UeuLOoC-c6iEda"},{"activeCount":1,"name":"Fairway","id":"HeRpch6y09FJ10Vrxkekxt"},{"activeCount":3,"name":"Health Nuts","id":"C-NhAwDy061LKS3K7PZmri"},{"activeCount":0,"name":"Staples","id":"CVa5TtIWkkFJXBb9ILUppr"},{"activeCount":6,"name":"Trader Joes","id":"PStVFIyKkj5K6GPaxUJynn"},{"activeCount":3,"name":"West Side Market","id":"WHfkG3KbqpviqQSiP0B8Rd"},{"activeCount":0,"name":"Whole Foods","id":"qcrVcp5fhT0KecyOACaAkS"}],"command":"getOverview"}
    def _get_lists(self):
        headers = {
            'Accept': 'application/json, text/javascript, */*',
            'Origin': 'https://www.ourgroceries.com',
            'Referer': 'https://www.ourgroceries.com/your-lists/',
            'X-Requested-With': 'XMLHttpRequest',
            'Host': 'www.ourgroceries.com',
            'Content-Type': 'application/json',
        }
        json_data = {
            'command': 'getOverview',
            'teamId': self._team_id,
        }
        response = self._session.post('https://www.ourgroceries.com/your-lists/', headers=headers, json=json_data)
        #if response.status_code == 200:
            #print('[SUCCESS] lists have been obtained')
        #else:
            #print('[ERROR] failure getting lists. Status code {}'.format(response.status_code))
        jsonResponse = json.loads(response.text)
        self._lists = jsonResponse['shoppingLists']
        #print('Lists: {}'.format(self._lists))


    def _get_quantified_item(self, item, quantity):
        if quantity == None:
            return item
        if quantity < 2:
            return item
        return "{} ({})".format(item, quantity)


    def _get_list_id(self, list_name):
        for listinfo in self._lists:
            if listinfo['name'].upper() == list_name.upper():
                return listinfo['id']
        return None
        

    def set_default_list(self, list_name):
        self._default_list_name = list_name


    def add_to_list(self, item, quantity=1, list_name=None):
        # Get the list ID from the name provided
        if list_name == None:
            list_name = self._default_list_name
        list_id = self._get_list_id(list_name)
        if list_id == None:
            raise KeyError('List name was not found')

        # Quantify the item if specified
        item_quantified = self._get_quantified_item(item, quantity)
        #print('qty: {}'.format(item_quantified))

        headers = {
            'Accept': 'application/json, text/javascript, */*',
            'Origin': 'https://www.ourgroceries.com',
            'Referer': 'https://www.ourgroceries.com/your-lists/',
            'X-Requested-With': 'XMLHttpRequest',
            'Host': 'www.ourgroceries.com',
            'Content-Type': 'application/json',
        }
        jsonData = {
            'command': 'insertItem',
            'teamId': self._team_id,
            'listId': list_id,
            'value': item_quantified
        }
        response = self._session.post('https://www.ourgroceries.com/your-lists/', headers=headers, json=jsonData)
        if response.status_code == 200:
            #print('[SUCCESS] item {} (qty {}) has been added to list {}'.format(item, quantity, list_name))
            return True
        else:
            #print('[ERROR] failure adding {} to the list {}. Status code {}'.format(item, list_name, response.status_code))
            return False


    def query_on_list(self, item, list_name=None):
        items = self._get_list_data(list_name)
        for item_data in items:
            crossed_off = item_data.get('crossedOff', False)
            if re.sub(r"[0-9|\(|\)|\w]", "", item_data['value'].upper()) == re.sub(r"[\w]", "", item.upper()) and not crossed_off:
                #print("matched item '{}' to item '{}'".format(item_data['value'], item))
                return True
        #print('no match for item {}'.format(item))
        return False

    
    def _get_list_data(self, list_name=None):
        # Get the list ID from the name provided
        if list_name == None:
            list_name = self._default_list_name
        list_id = self._get_list_id(list_name)
        if list_id == None:
            raise KeyError('List name was not found')

        headers = {
            'Accept' : 'application/json, text/javascript, */*',
            'Referer': 'https://www.ourgroceries.com/your-list',
            'Origin': 'https://www.ourgroceries.com',
            'X-Requested-With' : 'XMLHttpRequest',
            'Host' : 'www.ourgroceries.com',
            'Content-Type' : 'application/json'
        }
        json_data = {
            'command' : 'getList',
            'teamId' : self._team_id,
            'listId' : list_id,
        }
        response = self._session.post('https://www.ourgroceries.com/your-lists/', headers=headers, json=json_data)
        #if response.status_code == 200:
            #print('[SUCCESS] list {} query successful'.format(list_name))
        #else:
            #print('[ERROR] failure getting list {}. Status code {}'.format(list_name, response.status_code))
        json_response = json.loads(response.text)
        list_data = json_response['list']['items']
        #print('List data: {}'.format(list_data))
        return list_data

    
