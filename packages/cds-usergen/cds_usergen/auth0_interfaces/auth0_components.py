import solara
from solara.alias import rv
from solara.lab import use_task, Task, computed

from . import auth0

from ..components import ValidatedTextInput
from ..validation import validate_username, username_error_message, numDigits

"""
 TODO: Get Class info
  - display class info for the teachers
  - we need the class code (this will be the email domain)
  - we need to check if the class already has users assigned to it an how many
  - our auth0 call does not allow name-collision
"""



def get_connection():
    bearer_token = auth0.get_bearer_token(
        auth0.DOMAIN, auth0.CLIENT_ID, auth0.CLIENT_SECRET
    )
    cid, connection_info = auth0.get_connection_id(
        auth0.DOMAIN, 
        bearer_token, 
        auth0.CONNECTION_NAME
    )
    connection_options = auth0.get_connection(auth0.DOMAIN, bearer_token, cid)
    if connection_options.get('options', {}).get('validation',{}).get('username').get('max', None) is not None:
        auth0.MAX_USERNAME_LENGTH = connection_options.get('options', {}).get('validation',{}).get('username').get('max')
    return cid, bearer_token


@solara.component
def MakeConnection(ready, connection_id):
    async def load_connection():
        cid, token = get_connection()
        connection_id.value = cid
        auth0.BEAERER_TOKEN = token
    loaded = use_task(load_connection, dependencies=[])
    
    if not loaded.finished:
        solara.Warning("Connecting to Auth0...")
    elif loaded.finished:
        ready.set(True)
    else:
        solara.Error("Panic!")