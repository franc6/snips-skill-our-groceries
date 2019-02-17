import our_groceries_client
client = our_groceries_client.OurGroceriesClient()
client.authenticate(conf['secret']['username'], conf['secret']['password'], conf
['secret']['defaultList'])
what = intentMessage.slots.what.first().rawValue
list = intentMessage.slots.list.first().rawValue
quantity = intentMessage.slots.quantity.first().rawValue()
client.add_to_list(what, quantity, list)

