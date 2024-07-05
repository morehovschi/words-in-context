import sys
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QTextEdit,
    QPushButton
)
from PyQt5.QtGui import QTextOption
from extract_words import srt_subtitles, get_doc_word_stats
from easynmt import EasyNMT

# initialize translator (for translating to Romanian)
translator = EasyNMT( "opus-mt" )

class TranslationThread( QThread ):
    translation_done = pyqtSignal( str )

    def __init__( self, text_to_translate ):
        super().__init__()
        self.text_to_translate = text_to_translate

    def run(self):
        # Simulate a long translation process
        translated_text = translator.translate( self.text_to_translate,
                                                target_lang="ro" )
        self.translation_done.emit( translated_text )

class MainWindow( QWidget ):
    def __init__( self ):
        super().__init__()
        self.initUI()

    def initUI( self ):
        self.setWindowTitle( "Subtitle Word Picker" )
        self.setGeometry( 100, 100, 800, 600 )

        # left and middle layout
        layout = QHBoxLayout( self )
        self.left_section = QListWidget()
        self.middle_section = QListWidget()
        self.middle_section.setWordWrap( QTextOption.WordWrap )

        # right section layout
        right_layout = QVBoxLayout()
        self.front_text_edit = QTextEdit()
        self.translate_button = QPushButton( "Translate" )
        self.back_text_edit = QTextEdit()
        self.right_section = QTextEdit()

        # set up right layout
        right_layout.addWidget( self.front_text_edit )
        right_layout.addWidget( self.translate_button )
        right_layout.addWidget( self.back_text_edit )

        # set up top level layout
        layout.addWidget( self.left_section )
        layout.addWidget( self.middle_section )
        layout.addLayout( right_layout )

        # connect signals and slots
        self.left_section.itemSelectionChanged.connect( self.updateExamples )
        self.middle_section.itemSelectionChanged.connect( self.displayExample )
        self.translate_button.clicked.connect( self.translateExample )

        self.doc_word_stats = None
        self.srt_subtitles = None
        self.top_words = None

        # extract the top words in the analyzed file
        self.loadTopWords()

        if self.left_section.count() > 0:
            self.left_section.setCurrentRow( 0 )  # select first word by default
            self.updateExamples()
            self.displayExample()

    def loadTopWords( self ):
        """
        get the list of individual srt subtitles (list index is subtitle number)
        and the word stats for this document;

        the stats for an individual doc reference other docs as well (see TF-IDF
        calculation), so this function can take a while on its first run; during
        this first run, .json files are created which are later re-used for faster
        load time
        """

        data_path = "data/"
        file = "a-bucket-of-blood-1959"
        name_filtering = True

        self.srt_subtitles = srt_subtitles( data_path + file + ".srt" )
        self.doc_word_stats = get_doc_word_stats( data_path, file, name_filtering )

        self.top_words = []
        for i, word_stats in enumerate( self.doc_word_stats[ 1: ] ):
            self.top_words.append( f'{ i+1 }.  "{ word_stats[ 0 ] }"' )

        self.left_section.addItems( self.top_words )

    def updateExamples( self ):
        """
        get the selected word and its associated index in the list
        """

        selected_word = self.left_section.currentItem().text()
        selected_word_idx = self.top_words.index( selected_word )

        # use the index to find the indices of the subtitles where the word occurs
        # in the source subtitle file
        occ_ids = self.doc_word_stats[ selected_word_idx + 1 ][ 1 ][ "word_occ_ids" ]

        examples = []
        for i, occ_idx in enumerate( occ_ids ):
            example = self.srt_subtitles[ occ_idx ]
            # workaround for a sentence display issue where the spaces around
            # periods and commas are too small
            example = example.replace( ".", ". " ).replace( ",",", " )
            example += "\n"

            examples.append( f"{ i+1 }.  " + example )

        self.middle_section.clear()
        self.middle_section.addItems( examples )

        if self.middle_section.count() > 0:
            self.middle_section.setCurrentRow( 0 )  # select first example by default

    def get_current_word_and_example( self ):
        """
        convenience method to access the currently selected word and its
        and its corresponding example
        """

        selected_word = self.left_section.currentItem().text()
        # unpack the word to only the contents of the quotation marks
        # ex. '8. "wing"' -> 'wing'
        selected_word = selected_word[ selected_word.find( '"' ) + 1 :
                                       selected_word.rfind( '"' ) ]

        selected_example = self.middle_section.currentItem().text()
        # trim example number from the beginning
        selected_example =\
            selected_example[ selected_example.find( "." ) + 1 : ].strip()

        return selected_word, selected_example

    def displayExample( self ):
        """
        fill the front text box (upper right) with the original word and the
        selected contextual example where it occurs
        """

        selected_word, selected_example = self.get_current_word_and_example()
        front_text = selected_word + "\n\n" + selected_example
        self.front_text_edit.setPlainText( front_text )

        # clear previous translations when displaying a new example
        self.back_text_edit.clear()

    def translateExample( self ):
        """
        initializes a translation thread with the word and example to translate
        when the user clicks "Translate"

        also changes the text on the button to "Translating..." until translation
        is doe
        """
        self.translate_button.setText( "Translating..." )
        self.translate_button.setEnabled( False )

        selected_word, selected_example = self.get_current_word_and_example()
        self.translation_thread = TranslationThread( selected_word + "\n\n" +
                                                     selected_example )

        self.translation_thread.translation_done.connect( self.onTranslationDone )
        self.translation_thread.start()

    def onTranslationDone( self, translated_text ):
        """
        gets called whenever the translation thread has finished its job

        updates the translation text box
        """

        # sometimes the translater capitalizes the translated word for no reason;
        # below is a dirty hack around that
        translated_word, translated_example = translated_text.split( "\n\n" )
        translated_word = translated_word.lower()

        # hack around an issue where spaces near periods and commas are too small
        translated_example =\
            translated_example.replace( ".", ". " ).replace( ",", ", " ).strip()

        self.back_text_edit.setText( translated_word + "\n\n" + translated_example )

        self.translate_button.setText( "Translate" )
        self.translate_button.setEnabled( True )

if __name__ == "__main__":
    app = QApplication( sys.argv )
    mainWindow = MainWindow()
    mainWindow.show()
    sys.exit( app.exec_() )
