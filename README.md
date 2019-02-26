# snips-skill-our-groceries
Snips actions for interacting with Our Groceries

If you're not using my Our Groceries app, you'll need to modify this somewhat.  The username attached to the intents it cares about will be different.  Additionally, you should ensure that your intents have two special entities for your slots.  The "what" slot should use a custom entity named "our_groceries_item_name", and the "list" slot should use a custom entity named "our_groceries_list_name".  These special entities are updated with your existing lists and items on Our Groceries.

If you'd like to help with translations, please fork this repository and submit pull requests.  The code hasn't been internationalized/localized yet, but the plan is to just use GNU gettext.  Please note these translations will be spoken by snips, so proper grammar is important.
