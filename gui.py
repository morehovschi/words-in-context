import os
import sys
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QUrl
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QTextEdit,
    QPushButton,
    QFileDialog,
    QMessageBox,
    QDialog,
    QTableWidget,
    QTableWidgetItem,
    QAbstractItemView,
    QHeaderView,
    QSizePolicy,
    QLabel,
    QCheckBox
)
from PyQt5.QtGui import QTextOption, QFont
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from googletrans import Translator
from gtts import gTTS

from extract_words import (
    srt_subtitles,
    get_doc_word_stats,
    separate_fpath,
    process_dir
)
from export import Flashcard, export_to_anki

# deployment-specific data: the target user Decks
from user_data import USER_DECKS

# initialize translator (for translating to Romanian)
translator = Translator()

class AudioThread( QThread ):
    """
    TODO:
    """
    audio_done = pyqtSignal()

    def __init__( self, source_text, audio_filename ):
        super().__init__()
        self.source_text = source_text
        self.audio_filename = audio_filename

    def run( self ):
        # clean up any previously created temporary audio
        if os.path.isfile( self.audio_filename ):
            os.unlink( self.audio_filename )

        audio = gTTS( text=self.source_text, lang="en", slow=False )
        audio.save( self.audio_filename )
        self.audio_done.emit()

class TranslationThread( QThread ):
    """
    thread that executes translation when "Translate" is clicked
    """
    translation_done = pyqtSignal( str )

    def __init__( self, text_to_translate ):
        super().__init__()
        self.text_to_translate = text_to_translate

    def run( self ):
        translated_text = translator.translate( self.text_to_translate,
                                                src="en",
                                                dest="ro" ).text
        self.translation_done.emit( translated_text )

class FlashcardViewer( QDialog ):
    """
    TODO:
    """
    def __init__( self, flashcards ):
        super().__init__()
        self.setWindowTitle( "Flashcards" )
        self.setGeometry( 100, 100, 1100, 600 )
        self.flashcards = flashcards

        layout = QVBoxLayout()

        self.flashcards_table = QTableWidget()
        self.flashcards_table.setColumnCount( 2 )
        self.flashcards_table.setHorizontalHeaderLabels( [ "Select", "Flashcard" ] )
        self.flashcards_table.setColumnWidth( 0, 50 )
        self.flashcards_table.setColumnWidth( 1, 450 )
        self.flashcards_table.verticalHeader().setVisible( False )
        self.flashcards_table.setSelectionMode( QAbstractItemView.NoSelection )
        self.flashcards_table.horizontalHeader().setSectionResizeMode( 1, QHeaderView.Stretch )

        self.load_flashcards( flashcards )

        layout.addWidget( self.flashcards_table )

        self.delete_button = QPushButton( "Delete Selected" )
        self.delete_button.clicked.connect( self.delete_selected )
        layout.addWidget( self.delete_button )

        self.setLayout( layout )

        # Apply style sheet for brighter borders
        self.flashcards_table.setStyleSheet( """
            QTableWidget {
                border: none;
            }
            QTableWidget::item {
                border: 1px solid #888;  /* Bright grey border */
            }
            QHeaderView::section {
                font-size: 14px;
            }
        """ )

    def load_flashcards( self, flashcards ):
        self.flashcards_table.setRowCount( len( flashcards ) )
        for index, flashcard in enumerate( flashcards ):
            checkbox_item = QTableWidgetItem()
            checkbox_item.setFlags( Qt.ItemIsUserCheckable | Qt.ItemIsEnabled )
            checkbox_item.setCheckState( Qt.Unchecked )
            self.flashcards_table.setItem( index, 0, checkbox_item )

            flashcard_html = f"""
            <div style="margin-bottom: 5px;">{flashcard.front}</div>
            <hr style="border: 1px solid #bbb;">
            <div style="margin-top: 5px;">{flashcard.back}</div>
            """
            flashcard_text_edit = QTextEdit()
            flashcard_text_edit.setHtml( flashcard_html )
            flashcard_text_edit.setReadOnly( True )
            flashcard_text_edit.setWordWrapMode( QTextOption.WrapAtWordBoundaryOrAnywhere )
            flashcard_text_edit.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Expanding )

            # Set the border for QTextEdit (flashcard content) to be brighter grey
            flashcard_text_edit.setStyleSheet( """
                QTextEdit {
                    border: 1px solid #888;  /* Bright grey border */
                    background-color: #2e2e2e; /* Assuming a dark background color */
                    color: white; /* Text color */
                    padding: 5px; /* Add padding to avoid content touching the border */
                }
            """ )

            self.flashcards_table.setCellWidget( index, 1, flashcard_text_edit )

            # Adjust the row height based on content
            flashcard_text_edit.document().setTextWidth( self.flashcards_table.columnWidth( 1 ) )
            row_height = int(  flashcard_text_edit.document().size().height() + 10  )
            self.flashcards_table.setRowHeight( index, row_height )

    def delete_selected( self ):
        rows_to_delete = []
        for row in range( self.flashcards_table.rowCount() ):
            if self.flashcards_table.item( row, 0 ).checkState() == Qt.Checked:
                rows_to_delete.append( row )

        for row in sorted( rows_to_delete, reverse=True ):
            self.flashcards_table.removeRow( row )
            del self.flashcards[ row ]

class MainWindow( QWidget ):
    translation_complete = pyqtSignal()

    def __init__( self, sub_fpath ):
        super().__init__()
        self.sub_fpath = sub_fpath

        self.flashcards = []
        self.doc_word_stats = None
        self.srt_subtitles = None
        self.top_words = None
        self.translation_thread = None
        self.audio_thread = None
        self.flashcard_viewer = None
        self.corpus = None  # whole word corpus for all subtitle files
        self.name_filtering = True

        self.initUI()

    def initUI( self ):
        self.setWindowTitle( "Subtitle Word Picker" )
        self.setGeometry( 50, 50, 1200, 700 )

        # left layout
        self.left_section = QVBoxLayout()
        self.word_list = QListWidget()
        self.nf_button = QCheckBox()
        self.nf_button.setChecked( self.name_filtering )
        self.nf_button.setText( "Name filtering enabled" )
        self.left_section.addWidget( self.word_list )
        self.left_section.addWidget( self.nf_button )

        # middle layout
        self.middle_section = QListWidget()
        self.middle_section.setWordWrap( QTextOption.WordWrap )

        # layout for the two buttons in the right section
        button_layout = QHBoxLayout()
        self.listen_button = QPushButton( "Listen" )
        self.translate_button = QPushButton( "Translate" )
        button_layout.addWidget( self.listen_button )
        button_layout.addWidget( self.translate_button )

        # initialize the elements for the right section

        # 1. add save and view buttons
        save_view_button_layout = QHBoxLayout()
        self.save_card_button = QPushButton( "Save card" )
        self.view_cards_button = QPushButton( "View cards" )
        save_view_button_layout.addWidget( self.save_card_button )
        save_view_button_layout.addWidget( self.view_cards_button )

        # 2. flashcard counter and export button
        counter_export_layout = QHBoxLayout()
        self.flashcard_counter = QLabel( "0" )
        self.export_button = QPushButton( "Export" )
        self.export_button.setEnabled( False )
        counter_export_layout.addWidget( QLabel( "Flashcards:" ) )
        counter_export_layout.addWidget( self.flashcard_counter )
        counter_export_layout.addWidget( self.export_button )

        # 3. combine save/view and counter/export layouts
        save_view_counter_export_layout = QVBoxLayout()
        save_view_counter_export_layout.addLayout( save_view_button_layout )
        save_view_counter_export_layout.addLayout( counter_export_layout )

        # set up right layout combining the elements above
        right_layout = QVBoxLayout()
        self.front_text_edit = QTextEdit()
        self.back_text_edit = QTextEdit()
        right_layout.addWidget( self.front_text_edit )
        right_layout.addLayout( button_layout )
        right_layout.addWidget( self.back_text_edit )
        right_layout.addLayout( save_view_counter_export_layout )

        # set up top level layout
        layout = QHBoxLayout( self )
        layout.addLayout( self.left_section )
        layout.addWidget( self.middle_section )
        layout.addLayout( right_layout )

        # connect signals and slots
        self.nf_button.toggled.connect( self.toggle_name_filtering )
        self.word_list.itemSelectionChanged.connect(
            self.update_examples )
        self.middle_section.itemSelectionChanged.connect( self.display_example )
        self.listen_button.clicked.connect( self.listen_to_example )
        self.translate_button.clicked.connect( self.translate_example )
        self.save_card_button.clicked.connect( self.save_card )
        self.view_cards_button.clicked.connect( self.view_cards )
        self.export_button.clicked.connect( self.export_flashcards )

        self.media_player = QMediaPlayer()

        # extract the top words in the analyzed file
        self.load_top_words()

        if self.word_list.count() > 0:
            self.word_list.setCurrentRow( 0 )  # select first word by default
            self.update_examples()
            self.display_example()

    def toggle_name_filtering( self ):
        """
        gets called when user checks/unchecks "Name filtering"
        """
        self.name_filtering = self.nf_button.isChecked()
        self.load_top_words()
        if self.word_list.count() > 0:
            self.word_list.setCurrentRow( 0 )  # select first word by default
            self.update_examples()
            self.display_example()


    def load_top_words( self ):
        """
        get the list of individual srt subtitles (list index is subtitle number)
        and the word stats for this document;

        the stats for an individual doc reference other docs as well (see TF-IDF
        calculation), so this function can take a while on its first run; during
        this first run, .json files are created which are later re-used for faster
        load time
        """

        self.srt_subtitles = srt_subtitles( self.sub_fpath )
        data_path, file, _ = separate_fpath( self.sub_fpath )

        if self.corpus is None:
            self.corpus = process_dir( data_path )
        self.doc_word_stats = get_doc_word_stats( data_path, file,
                                                  self.name_filtering,
                                                  corpus=self.corpus )

        self.word_list.clear()
        self.top_words = []
        for i, word_stats in enumerate( self.doc_word_stats[ 1: ] ):
            self.top_words.append( f'{ i+1 }.  "{ word_stats[ 0 ] }"' )

        self.word_list.addItems( self.top_words )

    def update_examples( self ):
        """
        get the selected word and its associated index in the list
        """

        selected_word_idx = self.word_list.currentRow()

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

        selected_word = self.word_list.currentItem().text()
        # unpack the word to only the contents of the quotation marks
        # ex. '8. "wing"' -> 'wing'
        selected_word = selected_word[ selected_word.find( '"' ) + 1 :
                                       selected_word.rfind( '"' ) ]

        selected_example = self.middle_section.currentItem().text()
        # trim example number from the beginning
        selected_example =\
            selected_example[ selected_example.find( "." ) + 1 : ].strip()

        return selected_word, selected_example

    def display_example( self ):
        """
        fill the front text box (upper right) with the original word and the
        selected contextual example where it occurs
        """

        selected_word, selected_example = self.get_current_word_and_example()
        front_text = selected_word + "\n\n" + selected_example

        self.front_text_edit.clear()
        self.front_text_edit.setFontWeight( QFont.Normal )
        self.front_text_edit.setPlainText( front_text )

        # clear previous translations when displaying a new example
        self.back_text_edit.clear()

    def translate_example( self ):
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

        self.translation_thread.translation_done.connect( self.on_translation_done )
        self.translation_thread.start()

    def on_translation_done( self, translated_text ):
        """
        gets called whenever the translation thread has finished its job

        updates the translation text box
        """

        # sometimes the translater capitalizes the translated word for no reason;
        # below is a dirty hack around that
        translated_word, translated_example = translated_text.split( "\n\n" )
        translated_word = translated_word.lower()

        # on Windows, the font weight is sometimes bold after the user previously
        # marked certain words as bold; reset the font weight here
        self.back_text_edit.setFontWeight( QFont.Normal )

        self.back_text_edit.setPlainText(
            translated_word + "\n\n" + translated_example )

        self.translate_button.setText( "Translate" )
        self.translate_button.setEnabled( True )

        # this signal is used by tests
        self.translation_complete.emit()

    def listen_to_example( self ):
        """
        TODO:
        """
        self.listen_button.setText( "Creating audio..." )
        self.listen_button.setEnabled( False )

        selected_word, selected_example = self.get_current_word_and_example()
        self.audio_thread = AudioThread( selected_word + ". " + selected_example,
                                         "tmp-audio.mp3" )
        self.audio_thread.audio_done.connect( self.on_audio_ready )
        self.audio_thread.start()

    def on_audio_ready( self ):
        """
        TODO:
        """
        # clear any audio files that the QMediaPlayer may have cached
        # (necessary on Windows)
        self.media_player.stop()
        self.media_player.setMedia( QMediaContent() )

        tmp_audio_path = "tmp-audio.mp3"
        if "nt" not in os.name:
            # prepend to the path if not on Windows
            tmp_audio_path = os.getcwd() + "/" + tmp_audio_path

        self.media_player.setMedia( QMediaContent(
            QUrl.fromLocalFile( tmp_audio_path ) ) )

        self.media_player.setVolume( 50 )
        self.media_player.play()

        self.listen_button.setText( "Listen" )
        self.listen_button.setEnabled( True )

    # override
    def keyPressEvent(self, event):
        """
        override parent class's method that is called when user presses keys

        currently only reacts to Cmd + B / Ctrl + B when user selects a piece of
        text to be made bold
        """
        if ( ( event.modifiers() == Qt.ControlModifier or
               event.modifiers() == Qt.MetaModifier) and
             event.key() == Qt.Key_B ):
            self.toggle_bold()

    def toggle_bold( self ):
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

    @staticmethod
    def clean_up_temp_audio():
        """
        TODO:
        """
        if os.path.isfile( "tmp-audio.mp3" ):
            os.unlink( "tmp-audio.mp3" )

    def save_card( self ):
        """
        TODO:
        """
        front_text = self.front_text_edit.toHtml()
        back_text = self.back_text_edit.toHtml()
        if front_text and back_text:
            new_flashcard = Flashcard( front_text, back_text )
            self.flashcards.append( new_flashcard )

        self.update_flashcard_counter()

    def view_cards(self):
        """
        TODO:
        """
        self.flashcard_viewer = FlashcardViewer( self.flashcards )
        self.flashcard_viewer.exec_()
        self.update_flashcard_counter()

    def update_flashcard_counter(self):
        """
        TODO:
        """
        self.flashcard_counter.setText( str( len( self.flashcards ) ) )
        self.export_button.setEnabled( len( self.flashcards ) > 0 )

    def export_flashcards(self):
        export_to_anki( self.flashcards, USER_DECKS )
        self.flashcards.clear()
        self.update_flashcard_counter()

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

    app.setStyleSheet( "QWidget { font-size: 17px; }" )

    sub_fpath = select_subtitle_file()
    if not sub_fpath:
        QMessageBox.warning( None, "No File Selected",
                             "No subtitle file selected. Exiting." )
        sys.exit()

    mainWindow = MainWindow( sub_fpath=sub_fpath )
    app.aboutToQuit.connect( MainWindow.clean_up_temp_audio )
    mainWindow.show()
    sys.exit( app.exec_() )
