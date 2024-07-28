"""
This command line app looks through a set of subtitle files (.srt files in data/)
and, for a chosen document (corresponding to a movie or an episode), displays the
top N words ranked by TF-IDF. Once a word is chosen, contextual examples of the word
from the given document are displayed.

The app is intended for language learners who want learn a set of words (as well as
their associated contexts) ahead of watching the movie or episode.
"""

import os
import sys
import spacy
import json
import time
import math
import re

from progress.bar import Bar
from joblib import Parallel, delayed
from googletrans import Translator

TIMESTAMP_REGEX = "[0-9]{2}:[0-9]{2}:[0-9]{2},[0-9]{3} --> [0-9]{2}:[0-9]{2}:[0-9]{2},[0-9]{3}"
NON_ALPHABET_REGEX = "[^a-zA-Z']"
TAG_REGEX = re.compile( r"[<|\/<]*.>" )

# check that English language model available, and download if necessary
# (used for lemmatization)
if "en_core_web_sm" not in spacy.cli.info()[ "pipelines" ]:
    spacy.cli.download( "en_core_web_sm" )

# initialize translator (for translating into Romanian)
translator = Translator()

def has_alpha( string ):
    for char in string:
        if char.isalpha():
            return True
    return False

def is_namecase( string ):
    """
    returns True if first character uppercase and all others lowercase
    """
    return string[ 0 ].isupper() and string[ 1: ].islower()

def separate_fpath( fpath ):
    """ convenience method to separate directory name, file name and extension """

    dir_path = fpath[ :fpath.rfind( '/' ) + 1 ]
    fname = fpath[ fpath.rfind( '/' ) + 1:fpath.rfind( '.' ) ]
    extension = fpath[ fpath.rfind( '.' ): ]

    return dir_path, fname, extension

def srt_subtitles( fpath ):
    """
    helper that reads an srt file and returns a list of srt senteces where each
    item's index matches the srt line number
    """

    subtitles = []
    with open( fpath, "r", encoding="utf-8", errors="ignore" ) as f:
        counting = False
        num = None
        timestamp = None  # timestamp is only used for validating format
        subtitle = ""

        line = f.readline()
        while line:
            if not counting:
                # potentially remove utf 65279, found once at the beginning of the
                # file and any newline characters or spaces
                line = line.replace( chr( 65279 ), "" ).strip()
                if line.isnumeric():
                    counting = True
                    num = int( line )
                    # add $num empty items at the beginning so that subtitle indices
                    # in the list match subtitle numbers in the file
                    subtitles += [ "" ] * num

                line = f.readline()
                continue

            line = line.strip()

            if line.isnumeric() and int( line ) == num + 1:
                # remove any HTML tags
                subtitle = re.sub( TAG_REGEX, "", subtitle ).strip()

                subtitles.append( subtitle )

                num +=1
                timestamp = None
                subtitle = ""
            elif re.search( TIMESTAMP_REGEX, line ):
                timestamp = line
            else:
                if has_alpha( line ) and timestamp:
                    subtitle += line.strip() + " "

            line = f.readline()

        # if timestamp not None, there is still the last subtitle in the file that
        # has not yet been added to the list
        if timestamp:
            subtitles.append( subtitle.strip() )

    return subtitles

def count_words( fpath ):
    """
    Opens the subtitle file at $fpath and returns a dictionary of two dictionaries:
        1. "wsid": for each word in the doc, a list of the ids of the subtitles
           where it occurs.
        2. "likely_names": a dictionary of words deemed likely names. The dictionary
           values here are lists of ids of the word within the occurring sentence.
    """

    # load English language model, for lemmatization;
    #
    # this function is called in parallel, so each of its instances needs to load
    # a separate instance of the spacy model, to avoid shared memory issues
    nlp = spacy.load( "en_core_web_sm" )

    word_subtitle_ids = {}
    likely_names = {}

    subtitles = srt_subtitles( fpath )

    total_words = 0

    for sub_number, subtitle in enumerate( subtitles ):
        if not subtitle:
            continue

        # one subtitle can have more than one dialogue line
        # e.g.: "- Hello. Carrying any fruits or vegetables? - No."
        for line in subtitle.split( "- " ):
            if not line:
                continue

            doc = nlp( line )

            # position in sentence of actual word (ignoring punct or other signs)
            wordpos = 0

            for token in doc:
                # it is possible for a line to contain multiple sentences; wordpos
                # wordpos is reset then in order to help recognize words that are
                # always capitalized, regardless of sentence position (likely names)
                if ( ( token.i > 0 ) and
                     ( token.is_sent_start or
                       ( token.nbor( -1 ).is_punct and
                            token.nbor( -1 ).is_sent_start ) ) ):
                    wordpos = 0

                if ( token.is_punct ) or ( token is None ) or ( token.text == ' ' ) or\
                   ( token.text == "\n" ):
                    continue

                # lemmatize, filter out things like attached dashes, change to lowercase
                lemma = re.sub( NON_ALPHABET_REGEX, "", token.lemma_.lower() )

                if lemma in word_subtitle_ids:
                    word_subtitle_ids[ lemma ].append( sub_number )
                elif lemma:  # only add new lemma if not empty string
                     word_subtitle_ids[ lemma ] = [ sub_number ]

                # if word is upper case, it is possibly a name
                if is_namecase( token.text ):
                    if lemma in likely_names:
                        likely_names[ lemma ].append( wordpos )
                    else:
                        likely_names[ lemma ] = [ wordpos ]

                wordpos += 1
                total_words += 1

	# the total number of words in the file has special key
    word_subtitle_ids[ "__total__" ] = total_words

    # if any possible name is also encountered in lowercase, it does not only appear
    # as a proper noun in this document; mark it as a non-name
    definitely_not_names = set()
    for name in likely_names:
        if len( word_subtitle_ids[ name ] ) > len( likely_names[ name ] ):
            definitely_not_names.add( name )

    for name in likely_names:
        # if only one occurrence or if all occurrences are at the beginning of
        # the subtitle ==> the word is not a name
        if ( ( len( likely_names[ name ] ) < 2 ) or
             ( not any( likely_names[ name ] )) ):
                definitely_not_names.add( name )

    # after this loop, only words that:
    #   - were only encountered in uppercase AND
    #   - were encountered more than once AND
    #   - were encountered in different positions in their respecive subtitles
    # are considered names
    for word in definitely_not_names:
        del likely_names[ word ]

    return { "wsid": word_subtitle_ids, "likely_names": likely_names }

def analyze_file_subtitle_ids( fpath, cache_path="" ):
    """
    tries to open a serialized dictionary of words and the subtitle numbers where
    they occur; if unsuccessful, creates that dictionary and saves it
    """

    fname = separate_fpath( fpath )[ 1 ]

    try:
        with open( cache_path + fname + '.json' ) as json_file:
            word_stats = json.load( json_file )

    except FileNotFoundError:
        word_stats = count_words( fpath )

        # if cache path provided, store the counter dictionary
        if cache_path:
            with open( cache_path + fname + '.json' , 'w' ) as json_file:
                json.dump( word_stats, json_file )

def process_dir( dirpath ):
    """
    Looks at data directory and counts occurrences of all words in all files and
    stores the counts for each source file as json. If json already available, skips
    the counting step.
    """
    time0 = time.time()

    # count words in each srt file in parallel and output results to json files
    analyzables = []
    for fname in os.listdir( dirpath ):
        if fname.endswith( '.srt' ):
            analyzables.append( fname )
    Parallel( n_jobs=-1 )(
        delayed( analyze_file_subtitle_ids )(
            dirpath + fname , 'cached-data/' )
                 for fname in Bar( 'Counting words in files' ).iter( analyzables )
                         )
    print( 'elapsed:', time.time() - time0, "\n" )

    # dictionary of word count dictionaries for all files in dirpath dir
    corpus_counts = {}

    dir_filenames = []
    for fname in os.listdir( "cached-data/" ):
        if not fname.endswith( ".json" ):
            continue

        with open( "cached-data/" + fname ) as json_file:
            corpus_counts[ separate_fpath( fname )[ 1 ] ] = \
                json.load( json_file )

    return corpus_counts

def get_doc_word_stats( data_path, file, name_filtering=False ):
    """
    given a path to a data directory and the name of a file in it, loads data about
    word occurrences in all files (or, if unavailable, computes and saves it), and
    calculates TF-IDF for eaach word in the given file, in relation to all other
    files.

    the returned object is a list of tuples where [ 0 ] is the word and [ 1 ] is a
    dictionary of various statistics about this word in the given doc, like TF-IDF,
    how often the word occurs in this doc, how many other docs it occurs in etc.
    """
    # dictionary of word count dictionaries for all files in data_path dir
    corpus_counts = process_dir( data_path )

    doc_word_stats = []
    doc = corpus_counts[ file ][ "wsid" ]
    likely_names = corpus_counts[ file ][ "likely_names" ]

    for word in doc:
        if word == "__total__":
            continue

        word_stats = {}

        word_stats[ 'count' ] = len( doc[ word ] )
        word_stats[ 'words_in_doc' ] = doc[ '__total__']
        word_stats[ 'frequency' ] = word_stats[ 'count' ] /\
                                        word_stats[ 'words_in_doc' ]
        word_stats[ 'word_occs_in_docs' ] = 0
        word_stats[ 'word_occ_ids' ] = doc[ word ]

        for other_doc_name, other_doc in corpus_counts.items():
            if word in other_doc[ "wsid" ]:
                word_stats[ 'word_occs_in_docs' ] += 1

        word_stats[ 'tf-idf' ] = word_stats[ 'frequency' ] *\
            math.log( len( corpus_counts ) / word_stats[ 'word_occs_in_docs' ] )

        # tank the TF-IDF score of any word that has been deemed a likely name;
        # it is most likely irrelevant to a lanugage learner watching the movie
        if name_filtering and ( word in likely_names ):
            word_stats[ 'tf-idf' ] = 0

        # replace word count in doc with dictionary of more detailed statistics
        doc_word_stats.append(  ( word, word_stats ) )

    # sort words in doc by tf-idf and prepend None so that indexing starts at 1
    doc_word_stats = [ None ] +\
        sorted( doc_word_stats, key=lambda tup: tup[ 1 ][ 'tf-idf' ], reverse=True )
    return doc_word_stats

def num_displayed_words_menu():
    """
    takes in a new number of words to display from user, if input is in acceptable
    range, returns it; if not, user can try again until a valid number is received
    """
    while True:
        print( "New word window size: ", end="" )
        new_num = input()
        print()

        if ( ( not new_num.isnumeric() ) or
             ( int( new_num ) < 1 ) ):
            print( "Please enter a valid number (integer >= 1)" )
        else:
            return int( new_num )

def word_occurrence_menu( word, occ_ids, subtitles ):
    """
    shows all the occurrences of given $word in the given $subtitles, as determined
    by the list of subtitle ids $occ_ids

    implemented as an additional menu/function because its functionality pertaining
    to a particular word will be expanded soon

    returns bool:
        - False for staying in the main menu
        - True for quitting the whole program
    """
    def print_examples():
        print( f"\nDisplaying occurrences of \"{word}\":" )
        for i, idx in enumerate( occ_ids ):
            print( f"{ i + 1 }. \"{ subtitles[ idx ] }\"" )

    def print_instructions():
        print( "\nOptions:" )
        print( f"-Type a sentence's number [1-{len(occ_ids)}] to see its translation" )
        print( "-Display all examples again: l" )
        print( "-Back: b" )
        print( "-Quit: q\n" )

    print_examples()
    print_instructions()

    while True:
        action = input().strip()

        if ( action.isnumeric() and
             ( int( action ) > 0 ) and
             ( int( action ) <= len( occ_ids ) ) ):
            idx = int( action )

            print( f"Selected sentence:\n \"{ subtitles[ occ_ids[ idx - 1 ] ] }\"" )
            print( "\nTranslating...", end="", flush=True )

            translated = translator.translate( subtitles[ occ_ids[ idx - 1 ] ],
                                               src="en", dest="ro" ).text

            print( "done!\n" )
            print( translated )
            print_instructions()

        elif action.isnumeric():
            print( "Number out of range – please try again" )
        elif action.lower() == "l":
            print_examples()
            print_instructions()
        elif action.lower() == "b":
            return False
        elif action.lower() == "q":
            return True
        else:
            print( "Selection not understood – please try again." )

def main_menu( num_words, fname, subtitles, doc_word_stats, data_dir_path,
               name_filtering_enabled=False ):
    """
    Shows the top $num_words words in the file, as well as associated statistics
    and gives the user the option to print contextual example subtitles for any one
    of the displayed words.
    """
    start_word_idx = 1

    def get_words_in_range( doc_word_stats, start_word_idx, num_words ):
        return doc_word_stats[ max( start_word_idx, 1 ) :
                               min( start_word_idx + num_words,
                                    len( doc_word_stats ) ) ]

    def print_words( word_list, start_word_idx ):
        for i, word_stats in enumerate( word_list ):
            print( '%d. "%s". count in doc: %d. docs containing word: %d.' % (
                    start_word_idx + i, word_stats[ 0 ],
                    word_stats[ 1 ][ 'count' ],
                    word_stats[ 1 ][ 'word_occs_in_docs' ] ),
                'tf-idf:', '{:.2E}'.format( word_stats[ 1 ][ 'tf-idf' ] ) )

    def print_instructions( name_filtering_enabled ):
        nf_string = "enabled" if name_filtering_enabled else "disabled"
        nf_toggle_action = "Disable" if name_filtering_enabled else "Enable"
        last_word_idx = min( start_word_idx + num_words - 1, len( doc_word_stats ) - 1 )

        print( f"\nNote: name filtering is currently {nf_string}." )
        print( "\nOptions:\n-Select a word "\
              f"[{ start_word_idx }-{ last_word_idx }] to see "\
               "contextual examples\n-Change number of displayed words: w"\
              f"\n-Display the previous { num_words } words: p\n-Display the next "\
              f"{ num_words } words: n\n-Display current word "\
              f"list again: l\n-{ nf_toggle_action } name filtering: f\n-Quit: q\n" )

    def print_words_and_instructions( word_list, start_word_idx,
                                      name_filtering_enabled ):
        print_words( word_list, start_word_idx )
        print_instructions( name_filtering_enabled )

    word_list = get_words_in_range( doc_word_stats, start_word_idx, num_words )
    print_words_and_instructions( word_list, start_word_idx,
                                  name_filtering_enabled )

    while True:
        action = input().strip()

        if ( action.isnumeric() and
             int( action ) >= start_word_idx and
             int( action ) <= min( start_word_idx + num_words - 1,
                                   len( doc_word_stats ) - 1 ) ):
            idx = int( action )
            quit_program =\
                word_occurrence_menu( doc_word_stats[ idx ][ 0 ],
                                      doc_word_stats[ idx ][ 1 ][ "word_occ_ids"],
                                      subtitles )
            if quit_program:
                print( "Bye now!")
                return

            print_instructions( name_filtering_enabled )

        elif action.isnumeric():
            print( "Number out of range. Please try again.\n" )

        elif action.lower() == "w":
            num_words = num_displayed_words_menu()

            word_list = get_words_in_range( doc_word_stats, start_word_idx,
                                            num_words )
            print_words_and_instructions( word_list, start_word_idx,
                                          name_filtering_enabled )

        elif action.lower() == "n":
            if start_word_idx < len( doc_word_stats ) - num_words:
                start_word_idx += num_words

            word_list = get_words_in_range( doc_word_stats, start_word_idx,
                                            num_words )
            print_words_and_instructions( word_list, start_word_idx,
                                          name_filtering_enabled )

        elif action.lower() == "p":
            if start_word_idx > 1:
                 start_word_idx -= num_words

            word_list = get_words_in_range( doc_word_stats, start_word_idx,
                                            num_words )
            print_words_and_instructions( word_list, start_word_idx,
                                          name_filtering_enabled )

        elif action.lower() == "l":
            print_words( word_list, start_word_idx )

        elif action.lower() == "q":
            print( "Bye now!" )
            return

        elif action.lower() == "f":
            name_filtering_enabled = not name_filtering_enabled
            doc_word_stats = get_doc_word_stats( data_dir_path,
                                                 fname,
                                                 name_filtering_enabled )

            word_list = get_words_in_range( doc_word_stats, start_word_idx,
                                            num_words )
            print_words_and_instructions( word_list, start_word_idx,
                                          name_filtering_enabled )
        else:
            # here user possibly typed the desired word from the list
            word_idx = None

            for i in range( start_word_idx, start_word_idx + num_words ):
                if doc_word_stats[ i ][ 0 ] == action.lower():
                    word_idx = i
                    break

            if word_idx is not None:
                quit_program = word_occurrence_menu(
                    doc_word_stats[ word_idx ][ 0 ],
                    doc_word_stats[ word_idx ][ 1 ][ "word_occ_ids"],
                    subtitles )

                if quit_program:
                    print( "Bye now!" )
                    return

                print_instructions( name_filtering_enabled )
            else:
                print( "Selection not understood – please try again. Make sure to "\
                       "type the\nword exactly as it appears above, or simply introduce its number." )

def main( argv ):
    if len( argv ) < 2:
        # expected format for name of subtitle files
        fname_srt = 'its-a-wonderful-life-1946.srt'
    else:
        fname_srt = argv[ 1 ]

    if len( argv ) < 3:
        num_words = 20
    else:
        num_words = int( argv[ 2 ] )

    if "--help" in argv:
        print( f"USAGE: python3 { argv[ 0 ] }" +
    		   " <name of .srt file in data/> <num words>" )
        exit( 0 )

    data_dir_path = 'data/'
    fname = separate_fpath( fname_srt )[ 1 ]
    name_filtering_enabled = True

    subtitles = srt_subtitles( data_dir_path + fname_srt )

    # extract stats for the current doc and sort by tf-idf descendingly
    doc_word_stats = get_doc_word_stats( data_dir_path, fname, name_filtering_enabled )

    main_menu( num_words, fname, subtitles, doc_word_stats, data_dir_path, name_filtering_enabled )

if __name__ == "__main__":
    main( sys.argv )

