import unittest

# sys path manipulation necessary for importing function defined in parent dir
import os, sys 
sys.path.insert( 0, os.getcwd() )

from user_sessions import (
    load_user_sessions,
    add_user_session,
    delete_user_session,
    save_user_sessions
)

class TestUserSessions( unittest.TestCase ):
    """
    test the mechanism for creating and modifying user sessions, separate from GUI
    """
    def setUp( self ):
        # clean up if left over for some reason (e.g. interrupted run of this test)
        if os.path.isfile( "test_user_sessions.json" ):
            os.unlink( "test_user_sessions.json" )

    def test_user_sessions( self ):
        session_dict = load_user_sessions( "test_user_sessions.json" )

        self.assertCountEqual( session_dict,
                               { "sessions": {}, "deck_id": {} } )

        sessionA = { "decks" : [ "Alice", "Bob" ],
                     "target_lang": "Finnish",
                     "native_lang": "English" } 

        sessionB = { "decks": [ "Chris" ],
                     "target_lang": "Spanish",
                     "native_lang": "Catalan" }

        sessionC = { "decks": [ "Dana", "Eric" ],
                     "target_lang": "Croatian",
                     "native_lang": "German" }

        for name, session in [ ( "sessionA", sessionA ),
                               ( "sessionB", sessionB ),
                               ( "sessionC", sessionC ) ]:
            add_user_session( session_dict,
                              name,
                              session[ "decks" ],
                              session[ "target_lang" ],
                              session[ "native_lang" ] )

        save_user_sessions( session_dict, path="test_user_sessions.json" )
        session_dict = load_user_sessions( "test_user_sessions.json" )

        self.assertCountEqual( session_dict[ "sessions" ],
            { "sessionA": sessionA,
              "sessionB": sessionB,
              "sessionC": sessionC } )

        delete_user_session( session_dict, "sessionB" )
        save_user_sessions( session_dict, path="test_user_sessions.json" )
        session_dict = load_user_sessions( "test_user_sessions.json" )

        self.assertCountEqual( session_dict[ "sessions" ],
            { "sessionA": sessionA,
              "sessionC": sessionC } )

        # deck IDs should not be removed on session deletion, so verify all present
        for name in [ "Alice", "Bob", "Chris", "Dana", "Eric" ]:
            self.assertIn( name, session_dict[ "deck_id" ] )

    def tearDown( self ):
        os.unlink( "test_user_sessions.json" )


if __name__ == "__main__":
    unittest.main()
