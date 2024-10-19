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
import regex as re
import langdetect

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

# ISO 639, Set 1 abbreviations
LANG_CODE = {
    "Catalan": "ca",
    "Croatian": "hr",
    "Danish": "da",
    "Dutch": "nl",
    "English": "en",
    "Finnish": "fi",
    "French": "fr",
    "German": "de",
    "Greek": "el",
    "Italian": "it",
    "Lithuanian": "lt",
    "Macedonian": "mk",
    "Norwegian": "no",
    "Polish": "pl",
    "Portuguese": "pt",
    "Romanian": "ro",
    "Slovenian": "sl",
    "Spanish": "es",
    "Swedish": "sv",
    "Ukrainian": "uk"
}

SPACY_MODEL_NAME = {
    "ca": "ca_core_news_sm",
    "hr": "hr_core_news_sm",
    "da": "da_core_news_sm",
    "nl": "nl_core_news_sm",
    "en": "en_core_web_sm",
    "fi": "fi_core_news_sm",
    "fr": "fr_core_news_sm",
    "de": "de_core_news_sm",
    "el": "el_core_news_sm",
    "it": "it_core_news_sm",
    "lt": "lt_core_news_sm",
    "mk": "mk_core_news_sm",
    "no": "nb_core_news_sm",
    "pl": "pl_core_news_sm",
    "pt": "pt_core_news_sm",
    "ro": "ro_core_news_sm",
    "sl": "sl_core_news_sm",
    "es": "es_core_news_sm",
    "sv": "sv_core_news_sm",
    "uk": "uk_core_news_sm",
}

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

def srt_subtitles( fpath, separator="" ):
    """
    helper that reads an srt file and returns a list of srt senteces where each
    item's index matches the srt line number

    fpath( str ): path to the subtitle file
    separator( str ): a special string that can be used after a document is passed
                      through spaCy's nlp lemmatizer so that the original separation
                      of the lines can be recovered. Best if it's a madeup word like
                      "Endlineword".
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
                    subtitles += [ separator ] * num

                line = f.readline()
                continue

            line = line.strip()

            if line.isnumeric() and int( line ) == num + 1:
                # remove any HTML tags
                subtitle = re.sub( TAG_REGEX, "", subtitle ).strip()

                subtitles.append( subtitle.strip().replace( "\n", " " ) + separator )

                num += 1
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
            subtitles.append( subtitle.strip().replace( "\n", " " ) + separator)

    return subtitles

def detect_corpus_languages( dirpath ):
    """
    looks at every .srt file under dirpath and detects the text language; returns
    a set of codes of the detected languages
    """
    file_lang = {}
    fnames = os.listdir( dirpath )
    if ".DS_Store" in fnames:
        fnames.remove( ".DS_Store" )

    for fname in fnames:
        text_lines = srt_subtitles( dirpath + "/" + fname )
        # join into a string before passing to language detector
        lang = langdetect.detect( "\n".join( text_lines ) )
        file_lang[ fname ] = lang

    return file_lang

def ensure_model_downloaded( model_name ):
    """
    helper for process_dir_new
    """
    if model_name not in spacy.cli.info()[ "pipelines" ]:
        print( "Downloading model name:", model_name )
        spacy.cli.download( model_name )

def analyze_file_new( fpath, model, remove_punct=False ):
    """
    TODO:
    """
    file_stats = { "wsid": {} }
    likely_names = {}

    subs = srt_subtitles( fpath, separator=" Endlineword" )

    # join the srt lines into a single string and pass to spacy model for spacing
    # and lemmatization
    doc = model( "\n".join( subs ) )

    # srt line counter for easy lookup later
    line_counter = 0
    # total word counter in file
    word_counter = 0
    # word position in sentence
    pos_counter = 0

    def save_word( word ):
        # helper that saves the stats for a particular word;
        # exists because a doc token may have more than one word e.g. "well-lit"
        if word not in file_stats[ "wsid" ]:
            file_stats[ "wsid" ][ word ] = [ line_counter ]
        else:
            file_stats[ "wsid" ][ word ].append( line_counter )

        # if word is upper case, it is possibly a name
        if is_namecase( doc[ i ].text ):
            if word in likely_names:
                likely_names[ word ].append( pos_counter )
            else:
                likely_names[ word ] = [ pos_counter ]

    for i in range( len( doc ) ):
        if doc[ i ].text == "Endlineword":
            line_counter += 1
            pos_counter = 0
            continue

        # if token is sentence start, or the previous character is a punctuation
        # mark that acts as a sentence start -> reset the word position counter
        if ( doc[ i ].is_sent_start or
             (  doc[ i ].i > 0 and doc[ i ].nbor( -1 ).is_punct and
                    doc[ i ].nbor( -1 ).is_sent_start ) or
             ( doc[ i ].i > 0 and doc[ i ].nbor( -1 ).text == "-" ) ):
            pos_counter = 0

        if ( ( doc[ i ].is_punct ) or ( doc[ i ] is None ) or
             ( doc[ i ].text == ' ' ) or ( not has_alpha( doc[ i ].text ) ) ):
            continue

        # handle special case in German with apostrophe that replaces a vowel
        # e.g. "nächt'gen", "unharmon'sche", "heft'gen"
        if ( re.match( r"[\p{Latin}]{1,50}'[\p{Latin}]{2,50}", doc[ i ].text )
             and model.meta[ "lang" ] == "de"  ):
            # better to save the .text than .lemma_ in this particular case because
            # the model has a difficult time getting the right lemma for words
            # contracted in this way
            save_word( doc[ i ].text.lower() )
            pos_counter += 1
            word_counter += 1
            continue

        # remove punctuation and separate potential hyphenated words by replacing
        # every non-Latin or non-Cyrillic alphabet with " ", then splitting
        words = re.sub( r"[^\p{Latin}\p{Cyrillic}]", " ",
                        doc[ i ].lemma_.lower() ).split()

        if len( words ) == 1:
            save_word( words[ 0 ] )
            pos_counter += 1
            word_counter += 1
        else:
            # lemmatize again with the joined words now separated
            # e.g. what would otherwise be lemmatize as "Himmels-Liebe" now is
            # "himmels"->"himmel", "liebe"->"liebe"
            minidoc = model( " ".join( words ) )
            for token in minidoc:
                # sometimes single letter words are inexplicably lemmatized as
                # punctuation marks e.g. "s" -> "--"
                if not has_alpha( token.lemma_ ):
                    continue

                save_word( token.lemma_.lower() )

                # increment counters for each token added
                pos_counter += 1
                word_counter += 1
            # END looping through split token words
    # END looping through document tokens

    # if any possible name is also encountered in lowercase, it does not only appear
    # as a proper noun in this document; mark it as a non-name
    definitely_not_names = set()
    for name in likely_names:
        if len( file_stats[ "wsid" ][ name ] ) > len( likely_names[ name ] ):
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
    #   - were encountered in different positions in their respecive lines
    # are considered names
    for word in definitely_not_names:
        del likely_names[ word ]

    file_stats[ "total_words" ] = word_counter
    file_stats[ "likely_names" ] = likely_names
    return file_stats

def process_dir_new( dirpath, target_lang=None,
                     cached_data_path="cached-data/file_stats.json" ):
    """
    a new, more efficient way to analyze files in a directory, calling a new set of
    helper functions

    if target_lang is None, ignore other languages, otherwise analyze all
    """
    # get a dictionary of file -> language
    file_to_lang = detect_corpus_languages( dirpath )

    # just target language if specified, or all detected languages otherwise
    lang_list = [ target_lang ] if target_lang else list( file_to_lang.values() )

    # make sure spaCy model is downloaded for any languages where one is needed
    for lang in lang_list:
        model_name = SPACY_MODEL_NAME[ lang ]
        ensure_model_downloaded( model_name )

    # try to load cached source file stats; if not available, create new dict
    file_stats = None
    if os.path.isfile( cached_data_path ):
        with open( cached_data_path ) as json_file:
            file_stats = json.load( json_file )
    else:
        file_stats = {}

    # file stats dict is keyed by language; make sure an entry exists for any
    # language currently being analyzed
    time_0 = time.time()
    total_files = len( os.listdir( dirpath ) )
    processed_files = 0
    print( f"Processing srt files...{processed_files}/{total_files}",
           flush=True, end="" )
    for lang in lang_list:
        if lang not in file_stats:
            file_stats[ lang ] = {}

        model = spacy.load( SPACY_MODEL_NAME[ lang ] )

        for file in os.listdir( dirpath ):
            if ( file not in file_stats[ lang ] and
                 file_to_lang.get( file, None ) == lang ):
                file_stats[ lang ][ file ] =\
                    analyze_file_new( dirpath + "/" + file, model )

                processed_files += 1
                print( f"\rProcessing srt files...{processed_files}/{total_files}",
                        flush=True, end="" )

    print( f"\rProcessed. Time taken: {time.time() - time_0:.2f} seconds.", flush=True )

    with open( cached_data_path, "w" ) as json_file:
        json.dump( file_stats, json_file )

    return file_stats

def get_doc_word_stats( data_path, file, name_filtering=False, corpus=None ):
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
    if corpus is None:
        corpus = process_dir_new( data_path )[ "en" ]

    word_collection = corpus[ file ][ "wsid" ]
    likely_names = corpus[ file ][ "likely_names" ]

    words_in_doc = corpus[ file ][ "total_words" ]

    doc_word_stats = []

    for word in word_collection:
        if word == "__total__":
            continue

        word_stats = {}

        word_stats[ 'count' ] = len( word_collection[ word ] )
        word_stats[ 'words_in_doc' ] = words_in_doc
        word_stats[ 'frequency' ] = word_stats[ 'count' ] /\
                                        word_stats[ 'words_in_doc' ]
        word_stats[ 'word_occs_in_docs' ] = 0
        word_stats[ 'word_occ_ids' ] = word_collection[ word ]

        for other_doc_name, other_doc in corpus.items():
            if word in other_doc[ "wsid" ]:
                word_stats[ 'word_occs_in_docs' ] += 1

        word_stats[ 'tf-idf' ] = word_stats[ 'frequency' ] *\
            math.log( len( corpus ) / word_stats[ 'word_occs_in_docs' ] )

        # tank the TF-IDF score of any word that has been deemed a likely name;
        # it is most likely irrelevant to a language learner watching the movie
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
                print( "Selection not understood – please try again. Make sure to "
                       "type the\nword exactly as it appears above, or simply "
                       "introduce its number." )

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

    data_dir_path = "data/"
    name_filtering_enabled = True

    subtitles = srt_subtitles( data_dir_path + fname_srt )

    # extract stats for the current doc and sort by tf-idf descendingly
    doc_word_stats = get_doc_word_stats( data_dir_path, fname_srt,
                                         name_filtering_enabled )

    main_menu( num_words, fname_srt, subtitles, doc_word_stats, data_dir_path,
               name_filtering_enabled )

if __name__ == "__main__":
    main( sys.argv )

