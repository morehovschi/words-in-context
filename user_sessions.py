import os
import json
import random

AVAILABLE_LANGUAGES = [ 
    "Catalan", "Croatian", "Danish", "Dutch", "English", "Finnish", "French",
    "German", "Greek", "Italian", "Lithuanian", "Macedonian", "Norwegian", "Polish",
    "Portuguese", "Romanian", "Slovenian", "Spanish", "Swedish", "Ukrainian"
]

def load_user_sessions( path="test_user_sessions.json" ):
    """
    load previously saved user sessions or create a blank one;

    default path points to test file in order to avoid messing up user sessions that
    are in use
    """
    if os.path.isfile( path ):
        with open( path ) as json_file:
            return json.load( json_file )
    else:
        # return empty collection – executed on first run
        #
        # The 'deck_id' collection is used because Anki differentiates decks by
        # (integer) ID which means it is possible to have different decks with
        # the same name as long as the IDs are different. From a user perspective,
        # it seems better if a certain deck name always maps to the same ID, so the
        # name -> ID mapping is kept track off here.
        return { "sessions": {}, "deck_id": {} }

def add_user_session( session_dict, session_name, deck_names, target_lang,
                      native_lang ):

    # if no ID associated with this deck name, assign new one
    for deck_name in deck_names:
        if deck_name not in session_dict[ "deck_id" ]:
            session_dict[ "deck_id" ][ deck_name ] =\
                random.randint( 0, int( 2.00e+9 ) )

    # add new session to session dict
    session_dict[ "sessions" ][ session_name ] =\
        { "decks": list( set( deck_names ) ),  # convert to set to remove duplicates
          "target_lang": target_lang,
          "native_lang": native_lang }

def delete_user_session( session_dict, session_name ):
    """
    add extra processing before deleting the session with key session name if
    necessary
    """
    del session_dict[ "sessions" ][ session_name ]

def save_user_sessions( session_dict, path="test_user_sessions.json" ):
    """
    add extra processing before saving the dict if necessary;
    
    default path points to test file in order to avoid messing up user sessions that
    are in use
    """
    with open( path, "w" ) as json_file:
        json.dump( session_dict, json_file )
