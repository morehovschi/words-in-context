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
    helper for process_dir
    """
    if model_name not in spacy.cli.info()[ "pipelines" ]:
        print( "Downloading model name:", model_name )
        spacy.cli.download( model_name )

def analyze_file( fpath, model ):
    """
    analyze the file at fpath using the provided spaCy model and return a dictionary
    with the following keys:
        "wsid" -> dictionary mapping each word to the indices of the sentences where
                  where it appears in the file
        "in_sound_desc" -> dictionary parallel to "wsid" where every occurrence of
                           the word in a line is marked "1" if the word appears in a
                           sound description (within square brackets) and "0"
                           otherwise
        "likely_names" -> dictionary with words that may be names; key: the index of
                          the word within the sentence
        "total_words" -> number of total word occurences in this file
    """
    file_stats = { "wsid": {}, "likely_names": {}, "in_sound_desc": {} }

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
    # whether the word is found within square brackets
    in_sound_desc = False

    def save_word( word ):
        # helper that saves the stats for a particular word;
        # exists because a doc token may have more than one word e.g. "well-lit"
        if word not in file_stats[ "wsid" ]:
            file_stats[ "wsid" ][ word ] = [ line_counter ]
        else:
            file_stats[ "wsid" ][ word ].append( line_counter )

        if word not in file_stats[ "in_sound_desc" ]:
            file_stats[ "in_sound_desc" ][ word ] = [ in_sound_desc ]
        else:
            file_stats[ "in_sound_desc" ][ word ].append( in_sound_desc )

        # if word is upper case, it is possibly a name
        if is_namecase( doc[ i ].text ):
            if word in file_stats[ "likely_names" ]:
                file_stats[ "likely_names" ][ word ].append( pos_counter )
            else:
                file_stats[ "likely_names" ][ word ] = [ pos_counter ]

    for i in range( len( doc ) ):
        if doc[ i ].text == "Endlineword":
            line_counter += 1
            pos_counter = 0
            continue

        if doc[ i ].text == "[":
            in_sound_desc = True

        if doc[ i ].text == "]":
            in_sound_desc = False

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
    for name in file_stats[ "likely_names" ]:
        if len( file_stats[ "wsid" ][ name ] ) > \
           len( file_stats[ "likely_names" ][ name ] ):
            definitely_not_names.add( name )

    for name in file_stats[ "likely_names" ]:
        # if only one occurrence or if all occurrences are at the beginning of
        # the subtitle ==> the word is not a name
        if ( ( len( file_stats[ "likely_names" ][ name ] ) < 2 ) or
             ( not any( file_stats[ "likely_names" ][ name ] )) ):
                definitely_not_names.add( name )

    # after this loop, only words that:
    #   - were only encountered in uppercase AND
    #   - were encountered more than once AND
    #   - were encountered in different positions in their respecive lines
    # are considered names
    for word in definitely_not_names:
        del file_stats[ "likely_names" ][ word ]

    file_stats[ "total_words" ] = word_counter
    return file_stats

def process_dir( dirpath, target_lang=None,
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
                    analyze_file( dirpath + "/" + file, model )

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
        corpus = process_dir( data_path )[ "en" ]

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

