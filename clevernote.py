import sys
import json
import os.path
import urllib2
import functools

from evernote.api.client import EvernoteClient
import evernote.edam.type.ttypes as Types

CLEVERNOTE_CONSUMER_KEY = ''
CLEVERNOTE_CONSUMER_SECRET = ''
CLEVERNOTE_CALLBACK_URL = ''

CONFIG_FILENAME = os.path.expanduser('.cnrc')

config = None

def load_config():
    global config
    if config is None:
        if os.path.exists(CONFIG_FILENAME):
            try:
                config = json.load(open(CONFIG_FILENAME,'r'))
            except Exception as e:
                print("Problem loading config file %s: %s" % (CONFIG_FILENAME, e))
                sys.exit(1)
        else:
            config = {}
            save_config()


def save_config():
    global config
    json.dump(config, open(CONFIG_FILENAME,'w')
             , sort_keys=True
             , indent=4
             , separators=(',', ': ')
             )


def memoize(obj):
    cache = obj.cache = {}

    @functools.wraps(obj)
    def memoizer(*args, **kwargs):
        key = str(args) + str(kwargs)
        if key not in cache:
            cache[key] = obj(*args, **kwargs)
        return cache[key]
    return memoizer


def cmd_login(args):
    """login - Log in to Evernote; you'll be prompted for username and password"""

    load_config()
    if 'dev_token' in config:
        access_token = config['dev_token']
    elif 'access_token' in config:
        access_token = config['access_token']
    else:
        client = EvernoteClient(
            consumer_key=CLEVERNOTE_CONSUMER_KEY,
            consumer_secret=CLEVERNOTE_CONSUMER_SECRET,
            sandbox=True # Default: True
            )
        request_token = client.get_request_token(CLEVERNOTE_CALLBACK_URL)
        request_url = client.get_authorize_url(request_token)
        verifier_json = json.loads(urllib2.urlopen(request_url).read())
        access_token = client.get_access_token(
             request_token['oauth_token'],
             request_token['oauth_token_secret'],
             #request.GET.get('oauth_verifier', '')
             verifier_json['oauth_verifier']
             )
        client = EvernoteClient(token=access_token)
        config['access_token'] = access_token
    print("Logged in.")


def cmd_logout(args):
    """logout - Nuke your persistent Evernote credentials."""
    
    load_config()
    if 'access_token' in config:
        del config['access_token']
        save_config()
    print("Logged out.")


@memoize
def get_client():
    load_config()
    if 'dev_token' in config:
        access_token = config['dev_token']
    elif 'access_token' in config:
        access_token = config['access_token']
    else:
        print("You need to log in first.")
        sys.exit(1)
    return EvernoteClient(token=access_token)


@memoize
def get_notebooks():
    return get_client().get_note_store().listNotebooks()


def get_current_notebook():
    load_config()
    if 'cur_notebook' not in config:
        cur = [ n.name for n in get_notebooks() if n.defaultNotebook ]
        config['cur_notebook'] = cur[0]
        save_config()
    return config['cur_notebook']


def ask_yn(prompt):
    result = raw_input(prompt)
    return result.lower() in [ 'y', 'yes' ]


def set_current_notebook(name):
    load_config()
    if name not in [ n.name for n in get_notebooks() ]:
        if not ask_yn("Notebook '%s' doesn't exist. Create it?" % name):
            print("Aborted.")
            sys.exit(1)
        notebook = Types.Notebook()
        notebook.name = name
        note_store = get_client().get_note_store()
        notebook = note_store.createNotebook(notebook)
    config['cur_notebook'] = name
    save_config()


def cmd_notebooks(args):
    """notebooks - List existing notebooks. 
    The (evernote) default notebook is marked with a 'D'.
    The (local-only) current notebook is marked with a '+'
    """

    print("Notebooks:")
    for n in get_notebooks():
        print("  %s%s%s" % ( 'D' if n.defaultNotebook else ' '
                           , '+' if n.name == get_current_notebook() else ' '
                           , n.name))


def cmd_notebook(args):
    """notebook [+<notebook>] - if notebook is specified, set the current notebook,
    creating it if necessary. Otherwise, just show the current notebook.
    """
     
    if len(args) > 0:
        name = args[0]
        if name.startswith('+'): name = name[1:]
        set_current_notebook(name)

    print("Current notebook set to '%s'." % get_current_notebook())






def cmd_userinfo(args):
    """userinfo - Show your settings and information."""

    client = get_client()
    userStore = client.get_user_store()
    user = userStore.getUser()
    for field in [ 'name', 'username', 'email', 'timezone', 'privilege', 'active', 'created', 'updated', 'deleted', 'attributes' ]:
        value = str(getattr(user, field, ''))
        print("%s: %s" % (field.capitalize(), value))



def main():
    from cmdpy import CmdfileClient
    CmdfileClient(cmdmodule='clevernote').execute(sys.argv[1:])

