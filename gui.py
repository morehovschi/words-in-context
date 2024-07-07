import sys
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QTextEdit,
    QPushButton,
    QFileDialog,
    QMessageBox
)
from PyQt5.QtGui import QTextOption, QFont
from extract_words import srt_subtitles, get_doc_word_stats, separate_fpath
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
                                                source_lang="en",
                                                target_lang="ro" )
        self.translation_done.emit( translated_text )

class MainWindow( QWidget ):
    def __init__( self, sub_fpath ):
        super().__init__()
        self.sub_fpath = sub_fpath
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

        name_filtering = True

        self.srt_subtitles = srt_subtitles( self.sub_fpath )
        data_path, file, _ = separate_fpath( self.sub_fpath )
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
            example = self.srt_subtitles[ occ_idx ] + "\n"
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

        self.back_text_edit.setText( translated_word + "\n\n" + translated_example )

        self.translate_button.setText( "Translate" )
        self.translate_button.setEnabled( True )

    def keyPressEvent(self, event):
        """
        override parent class's method that is called when user presses keys

        currently only reacts to Cmd + B / Ctrl + B when user selects a piece of
        text to be made bold
        """
        if ( ( event.modifiers() == Qt.ControlModifier or
               event.modifiers() == Qt.MetaModifier) and
             event.key() == Qt.Key_B ):
            self.toggleBold()

    def toggleBold( self ):
        """
        makes selected text bold
        """

        editor = self.focusWidget()  # Get the currently focused widget

        if isinstance( editor, QTextEdit ):
            cursor = editor.textCursor()

            if cursor.hasSelection():
                char_format = cursor.charFormat()

                if char_format.fontWeight() == QFont.Bold:
                    char_format.setFontWeight( QFont.Normal )
                else:
                    char_format.setFontWeight( QFont.Bold )

                cursor.mergeCharFormat( char_format )

def select_subtitle_file():
    """
    shows user a dialog box prompting for file selection
    """

    options = QFileDialog.Options()
    options |= QFileDialog.ReadOnly
    file_dialog = QFileDialog()
    file_dialog.setOptions( options )
    file_dialog.setWindowTitle( "Select Subtitle File" )
    file_dialog.setDirectory( "data/" )  # Default directory to open
    file_dialog.setNameFilter( "Subtitle Files (*.srt)" )

    if file_dialog.exec_() == QFileDialog.Accepted:
        return file_dialog.selectedFiles()[0]
    return None

if __name__ == "__main__":
    app = QApplication( sys.argv )

    sub_fpath = select_subtitle_file()
    if not sub_fpath:
        QMessageBox.warning( None, "No File Selected",
                             "No subtitle file selected. Exiting." )
        sys.exit()

    mainWindow = MainWindow( sub_fpath=sub_fpath )
    mainWindow.show()
    sys.exit( app.exec_() )
