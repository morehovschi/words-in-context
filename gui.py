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
    QCheckBox,
    QComboBox,
    QDialogButtonBox
)
from PyQt5.QtGui import QTextOption, QFont, QFontMetrics
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from googletrans import Translator
from gtts import gTTS

from extract_words import (
    srt_subtitles,
    get_doc_word_stats,
    separate_fpath,
    process_dir,
    LANG_CODE
)
from export import (
    Flashcard,
    export_to_anki,
    write_flashcard_to_backup,
    read_flashcard_backup
)

from user_sessions import (
    AVAILABLE_LANGUAGES,
    load_user_sessions,
    add_user_session,
    delete_user_session,
    save_user_sessions
)

import warnings

# name of the file where the session backup is stored
BACKUP_FNAME = "backup_pickle"

# suppress a specific warning that is produced when writing rich text to Anki deck
# file when exporting flash cards
warnings.filterwarnings( "ignore", category=UserWarning )

# initialize translator (for translating to Romanian)
translator = Translator()

def show_restore_dialog( num_flashcards ):
    """
    shows user a dialog asking whether they want to restore the previous session.

    MISSING-TEST: the backend of the session backup has an associated unit test, but
                  its integration with the GUI (i.e. this function) does not yet.

    Returns:
        response (bool): True (yes, use the previous session) or False (discard the
                         previous session and delete the backup file).
    """

    msg_box = QMessageBox()
    msg_box.setIcon( QMessageBox.Question )
    msg_box.setWindowTitle( "Restore Session" )
    msg_box.setText( f"A previously unsaved session containing {num_flashcards} "\
                     "flashcards was found. Would you like to restore it or "\
                     "discard it?" )

    msg_box.setStandardButtons( QMessageBox.Yes | QMessageBox.No )
    msg_box.setDefaultButton( QMessageBox.Yes )
    msg_box.button( QMessageBox.Yes ).setText( "Restore" )
    msg_box.button( QMessageBox.No ).setText( "Discard" )
    response = msg_box.exec()
    return response == QMessageBox.Yes

def select_subtitle_file():
    """
    shows user a dialog box prompting for file selection

    MISSING-TEST
    """
    options = QFileDialog.Options()
    options |= QFileDialog.ReadOnly
    file_dialog = QFileDialog()
    file_dialog.setOptions( options )
    file_dialog.setWindowTitle( "Select Subtitle File" )
    file_dialog.setDirectory( "data/" )  # Default directory to open
    file_dialog.setNameFilter( "Subtitle Files (*.srt)" )

    if file_dialog.exec_() == QFileDialog.Accepted:
        return file_dialog.selectedFiles()[ 0 ]

    return None

class AudioThread( QThread ):
    """
    create an audio file reading out the source text in the target language

    MISSING-TEST
    """
    audio_done = pyqtSignal()

    def __init__( self, source_text, audio_filename, lang ):
        super().__init__()
        self.source_text = source_text
        self.audio_filename = audio_filename
        self.lang = lang

    def run( self ):
        # clean up any previously created temporary audio
        if os.path.isfile( self.audio_filename ):
            os.unlink( self.audio_filename )

        audio = gTTS( text=self.source_text, lang=self.lang, slow=False )
        audio.save( self.audio_filename )
        self.audio_done.emit()

class TranslationThread( QThread ):
    """
    thread that executes translation when "Translate" is clicked
    """
    translation_done = pyqtSignal( tuple )

    def __init__( self, word_to_translate, sentence_to_translate, target_lang,
                  native_lang ):
        super().__init__()
        self.word_to_translate = word_to_translate
        self.sentence_to_translate = sentence_to_translate
        self.target_lang = target_lang
        self.native_lang = native_lang

    def run( self ):
        trans_word = translator.translate( self.word_to_translate,
                                           src=self.target_lang,
                                           dest=self.native_lang ).text
        trans_sentence = translator.translate( self.sentence_to_translate,
                                               src=self.target_lang,
                                               dest=self.native_lang ).text
        self.translation_done.emit( ( trans_word, trans_sentence ) )

class SingleLineTextEdit( QTextEdit ):
    """
    custom text edit that is only one row in height

    used by SessionCreationDialog to get session name from user
    """
    def __init__( self ):
        super( SingleLineTextEdit, self ).__init__()
        # Calculate the height dynamically based on the font size
        self.adjust_height_to_font()

        # Set the word wrap to NoWrap to prevent multiline
        self.setWordWrapMode( QTextOption.NoWrap )

    def adjust_height_to_font( self ):
        # Get the font metrics for the current font
        font_metrics = QFontMetrics( self.font() )
        # Calculate the required height for a single line of text
        text_height = font_metrics.height()
        # Set the fixed height of the QTextEdit based on this
        self.setFixedHeight( text_height+15 )  # Adding padding if needed

    def keyPressEvent( self, event ):
        # Reject the characters '\n' (Enter key) and ','
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            event.ignore()  # Ignore the Enter key
        elif event.text() == ',':
            event.ignore()  # Ignore comma
        else:
            super( SingleLineTextEdit, self ).keyPressEvent( event )

class SessionCreationDialog( QDialog ):
    """
    instantiated by SessionSelectionDialog whenever "New Session" is clicked

    when it is done it returns to the parent dialog:
        session_name, formatted_deck_names, target_language, native_language
    via the get_selection method
    """

    def __init__( self, parent=None ):
        super().__init__( parent )
        self.setWindowTitle( "Language and Deck Selection" )

        # Layout for the dialog
        layout = QVBoxLayout( self )

        layout.addWidget( QLabel( "Enter session name:" ) )
        self.session_name_edit = SingleLineTextEdit()
        layout.addWidget( self.session_name_edit )

        # TextEdit for entering card deck names
        layout.addWidget( QLabel( "Enter card deck name(s), comma-separated:" ) )
        self.deck_names_edit = QTextEdit( self )
        layout.addWidget( self.deck_names_edit )

        # Dropdown for selecting the target language
        layout.addWidget( QLabel( "Select target language:" ) )
        self.target_language_combo = QComboBox( self )
        self.target_language_combo.addItems( AVAILABLE_LANGUAGES )
        self.target_language_combo.setCurrentText( "English" )
        layout.addWidget( self.target_language_combo )

        # Dropdown for selecting the native language
        layout.addWidget( QLabel( "Select native language:" ) )
        self.native_language_combo = QComboBox( self )
        self.update_native_language_options()
        layout.addWidget( self.native_language_combo )

        # Update native language options when target language changes
        self.target_language_combo.currentTextChanged.connect(
            self.update_native_language_options )

        # OK and Cancel buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self )
        self.button_box.accepted.connect( self.accept )
        self.button_box.rejected.connect( self.reject )
        layout.addWidget( self.button_box )

        # Disable OK button initially
        self.button_box.button( QDialogButtonBox.Ok ).setEnabled( False )

        # Connect text change signal to check if OK button can be enabled
        self.session_name_edit.textChanged.connect( self.check_deck_names )
        self.deck_names_edit.textChanged.connect( self.check_deck_names )

    def update_native_language_options( self ):
        """
        update native language options excluding the selected target language.
        """
        current_target = self.target_language_combo.currentText()
        self.native_language_combo.clear()
        self.native_language_combo.addItems(
            [ lang for lang in AVAILABLE_LANGUAGES if lang != current_target ] )
        self.native_language_combo.setCurrentText( "Romanian" )

    def check_deck_names( self ):
        """
        enable or disable the OK button based on whether session name and deck names
        are entered.
        """
        session_name = self.session_name_edit.toPlainText().strip()
        deck_names = self.deck_names_edit.toPlainText().strip()
        self.button_box.button( QDialogButtonBox.Ok ).setEnabled(
            bool( session_name and deck_names ) )

    def get_selection( self ):
        """
        return the selected deck names, target language, and native language.
        """
        session_name = self.session_name_edit.toPlainText().strip()
        # split the deck names by \n or comma
        deck_names = self.deck_names_edit.toPlainText().strip()
        deck_names = deck_names.replace( "\n", "," ).split( "," )
        formatted_deck_names = []
        for name in deck_names:
            if len( name ) == 0:
                continue
            formatted_deck_names.append( name.strip() )

        target_language = self.target_language_combo.currentText()
        native_language = self.native_language_combo.currentText()
        return session_name, formatted_deck_names, target_language, native_language

class SessionSelectionDialog( QDialog ):
    """
    mandatory dialog at app launch for selecting the user session

    a user session defines the target and native languages, as well as the names
    of the target Anki decks
    """
    def __init__( self, user_sessions_file="test_user_sessions.json" ):
        """
        instantiate necessary variables and define the visual aspect of the dialog;

        default user sessions file points to a test file in order to prevent
        unintentional modification/deletion of deployment sessions
        """
        super().__init__()
        self.setWindowTitle( "Session Selection" )

        self.user_session_file = user_sessions_file
        self.session_dict = load_user_sessions( path=self.user_session_file )

        layout = QHBoxLayout( self )

        left_section = QVBoxLayout()
        self.session_list = QListWidget()
        left_buttons = QHBoxLayout()
        self.new_session_button = QPushButton( "New session" )
        self.delete_session_button = QPushButton( "Delete session" )
        self.new_session_button.setFocusPolicy( Qt.NoFocus )
        self.delete_session_button.setFocusPolicy( Qt.NoFocus )
        self.delete_session_button.setEnabled( False )

        left_buttons.addWidget( self.new_session_button )
        left_buttons.addWidget( self.delete_session_button )
        left_section.addWidget( self.session_list )
        left_section.addLayout( left_buttons )

        right_section = QVBoxLayout()
        self.deck_name_list = QListWidget()
        # make the target deck names read-only in this widget
        self.deck_name_list.setEditTriggers(
            QAbstractItemView.NoEditTriggers )
        # make deck names not selectable
        self.deck_name_list.setSelectionMode(
            QAbstractItemView.NoSelection )
        self.target_language_name = QLabel()
        self.native_language_name = QLabel()
        self.proceed_button = QDialogButtonBox( QDialogButtonBox.Ok, self )
        self.proceed_button.button( QDialogButtonBox.Ok ).setText(
            "Proceed to session" )
        self.proceed_button.button( QDialogButtonBox.Ok ).setEnabled( False )
        right_section.addWidget( self.deck_name_list )
        right_section.addWidget( self.target_language_name )
        right_section.addWidget( self.native_language_name )
        right_section.addWidget( self.proceed_button, alignment=Qt.AlignHCenter )

        layout.addLayout( left_section )
        layout.addLayout( right_section )

        # connect signals and slots
        self.new_session_button.clicked.connect( self.create_new_session )
        self.delete_session_button.clicked.connect(
            self.on_delete_session_clicked )
        self.session_list.itemSelectionChanged.connect(
            self.display_current_session )
        self.proceed_button.accepted.connect( self.accept )

        self.update_session_list()

    def display_current_session( self ):
        if not self.session_list.selectedItems():
            self.deck_name_list.clear()
            self.target_language_name.setText( "" )
            self.native_language_name.setText( "" )
            self.delete_session_button.setEnabled( False )
            self.proceed_button.button( QDialogButtonBox.Ok ).setEnabled( False )
            return

        self.deck_name_list.clear()
        selected_session = self.session_list.currentItem().text()
        decks = self.session_dict[ "sessions" ][ selected_session ][ "decks" ]
        for deck_name in decks:
            self.deck_name_list.addItem( deck_name )

        self.target_language_name.setText( "Target: " +\
            self.session_dict[ "sessions" ][ selected_session ][ "target_lang" ] )
        self.native_language_name.setText( "Native: " +\
            self.session_dict[ "sessions" ][ selected_session ][ "native_lang" ] )

        self.delete_session_button.setEnabled( True )
        self.proceed_button.button( QDialogButtonBox.Ok ).setEnabled( True )

    def update_session_list( self ):
        selected_session_idx = None
        if self.session_list.selectedItems():
            selected_session_idx = self.session_list.currentRow()

        self.session_list.clear()

        for session_name in self.session_dict[ "sessions" ]:
            self.session_list.addItem( session_name )

        if ( ( selected_session_idx is not None ) and
             ( selected_session_idx < self.session_list.count() ) ):
            self.session_list.setCurrentRow( selected_session_idx )

        self.display_current_session()

    def create_new_session( self ):
        creation_dialog = SessionCreationDialog()

        if creation_dialog.exec_() == QDialog.Accepted:
            session_name, deck_names, target_lang, native_lang =\
                creation_dialog.get_selection()
        else:
            return

        add_user_session( self.session_dict, session_name, deck_names, target_lang,
                          native_lang )
        self.update_session_list()

        # save update to disk
        save_user_sessions( self.session_dict, path=self.user_session_file )

    def delete_session( self ):
        if not self.session_list.selectedItems():
            return

        session_name = self.session_list.currentItem().text()
        self.session_list.clearSelection()
        delete_user_session( self.session_dict, session_name )
        self.update_session_list()

        # save update to disk
        save_user_sessions( self.session_dict, path=self.user_session_file )

    def on_delete_session_clicked( self ):
        # confirmation dialog before actually deleting
        delete_session_dialog = QMessageBox.question(
            self,
            "Delete Session",
            "Are you sure you want to delete "
            f'"{self.session_list.currentItem().text()}"?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if delete_session_dialog == QMessageBox.Yes:
            self.delete_session()

    def get_selection( self ):
        session_name = self.session_list.currentItem().text()
        target_lang =\
            self.session_dict[ "sessions" ][ session_name ][ "target_lang" ]
        native_lang =\
            self.session_dict[ "sessions" ][ session_name ][ "native_lang" ]

        # get deck name->id mapping for the current session
        deck_name_to_id = {}
        for deck_name in self.session_dict[ "sessions" ][ session_name ][ "decks" ]:
            deck_name_to_id[ deck_name ] =\
                self.session_dict[ "deck_id" ][ deck_name ]

        return session_name, deck_name_to_id, target_lang, native_lang

class FlashcardViewer( QDialog ):
    """
    child dialog of MainWindow displaying the currently saved flashcards

    allows deleting flashcards

    MISSING-TEST
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
    back_text_cleared = pyqtSignal()

    def __init__( self, sub_fpath, target_lang, native_lang, deck_name_to_id,
                  out_path="out-data/", flashcards=None ):
        super().__init__()
        self.sub_fpath = sub_fpath
        self.target_lang = target_lang
        self.native_lang = native_lang
        self.deck_name_to_id = deck_name_to_id

        self.flashcards = flashcards if flashcards else []
        self.doc_word_stats = None
        self.srt_subtitles = None
        self.top_words = None
        self.translation_thread = None
        self.audio_thread = None
        self.flashcard_viewer = None
        self.corpus = None  # whole word corpus for all srt files in target lang
        self.out_path = out_path
        if target_lang != "de":
            self.name_filtering = True
        else:
            self.name_filtering = False

        self.deprioritize_sound_desc = False

        self.initUI()

    def initUI( self ):
        self.setWindowTitle( "Words in Context" )
        self.setGeometry( 50, 50, 1200, 700 )

        # left layout
        self.left_section = QVBoxLayout()
        self.word_list = QListWidget()
        self.nf_button = QCheckBox()
        self.nf_button.setChecked( self.name_filtering )
        if self.target_lang == "de":
            self.nf_button.setEnabled( False )
            self.nf_button.setText( "Name filtering unavailable for German" )
        else:
            nf_state = "enabled" if self.name_filtering else "disabled"
            self.nf_button.setText( "Name filtering " + nf_state )
        self.left_section.addWidget( self.word_list )
        self.left_section.addWidget( self.nf_button )

        # middle layout
        self.middle_section = QVBoxLayout()
        self.info_label = QLabel()
        self.example_list = QListWidget()
        self.deprioritize_sound_desc_box = QCheckBox()
        self.deprioritize_sound_desc_box.setChecked(
            self.deprioritize_sound_desc )
        dsd = self.deprioritize_sound_desc
        self.deprioritize_sound_desc_box.setText(
            ( "*" if dsd else "" ) + "Deprioritize sound descriptions " +
            ( "enabled" if dsd else "disabled" ) )
        self.example_list.setWordWrap( QTextOption.WordWrap )
        self.middle_section.addWidget( self.info_label )
        self.middle_section.addWidget( self.example_list )
        self.middle_section.addWidget( self.deprioritize_sound_desc_box )

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
        layout.addLayout( self.middle_section )
        layout.addLayout( right_layout )

        # connect signals and slots
        self.word_list.itemSelectionChanged.connect(
            self.update_examples )
        self.example_list.itemSelectionChanged.connect( self.display_example )
        self.listen_button.clicked.connect( self.listen_to_example )
        self.translate_button.clicked.connect( self.translate_example )
        self.save_card_button.clicked.connect( self.save_card )
        self.view_cards_button.clicked.connect( self.view_cards )
        self.export_button.clicked.connect( self.export_flashcards )

        # the option to enable name filtering is unavailable for German
        # (name filtering is a best effort name detection algorithm focusing on
        # words starting in a capital letter in the middle of the sentence; this
        # does not work for German because all nouns are capitalized)
        if self.target_lang != "de":
            self.nf_button.toggled.connect( self.toggle_name_filtering )

        self.deprioritize_sound_desc_box.toggled.connect(
            self.toggle_deprioritize_sound_desc )

        self.media_player = QMediaPlayer()

        # extract the top words in the analyzed file
        self.load_top_words()

        if self.word_list.count() > 0:
            self.word_list.setCurrentRow( 0 )  # select first word by default
            self.update_examples()
            self.display_example()

        # in case flashcards are loaded from a previous session
        self.update_flashcard_counter()

    def toggle_name_filtering( self ):
        """
        gets called when user checks/unchecks "Name filtering"
        """
        self.name_filtering = self.nf_button.isChecked()
        state = "enabled" if self.name_filtering else "disabled"

        self.nf_button.setText( "Name filtering " + state )
        self.load_top_words()
        if self.word_list.count() > 0:
            self.word_list.setCurrentRow( 0 )  # select first word by default
            self.update_examples()
            self.display_example()

    def toggle_deprioritize_sound_desc( self ):
        """
        gets called when user checks/unchecks "Deprioritize sound descriptions"
        """
        self.deprioritize_sound_desc = self.deprioritize_sound_desc_box.isChecked()
        dsd = self.deprioritize_sound_desc
        self.deprioritize_sound_desc_box.setText(
            ( "*" if dsd else "" ) + "Deprioritize sound descriptions " +
            ( "enabled" if dsd else "disabled" ) )

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
        data_path, file, ext = separate_fpath( self.sub_fpath )

        if self.corpus is None:
            self.corpus =\
                process_dir( data_path,
                             target_lang=self.target_lang )[ self.target_lang ]
        self.doc_word_stats = get_doc_word_stats(
            data_path, file+ext, self.name_filtering, corpus=self.corpus,
            deprioritize_sound_desc=self.deprioritize_sound_desc )

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
        selected_word_stats = self.doc_word_stats[ selected_word_idx + 1 ][ 1 ]

        # update label at the top of middle section with stats about word in the doc
        self.info_label.setText(
            '<div style="line-height: 1.15;">'
            f'Count in this doc: {selected_word_stats["count"]}<br>'
            f'Docs containing word: {selected_word_stats["word_occs_in_docs"]}<br>'
            f'TF-IDF{"*"if self.deprioritize_sound_desc else ""}: '
               f'{selected_word_stats["tf-idf"]:.2E}'
            '</div>'
        )

        # use the index to find the indices of the subtitles where the word occurs
        # in the source subtitle file
        occ_ids = selected_word_stats[ "word_occ_ids" ]
        examples = []
        for i, occ_idx in enumerate( occ_ids ):
            example = self.srt_subtitles[ occ_idx ] + "\n"
            examples.append( f"{ i+1 }.  " + example )

        self.example_list.clear()
        self.example_list.addItems( examples )

        if self.example_list.count() > 0:
            self.example_list.setCurrentRow( 0 )  # select first example by default

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

        selected_example = self.example_list.currentItem().text()
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
        # this signal is used by tests
        self.back_text_cleared.emit()

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
        self.translation_thread = TranslationThread( selected_word,
                                                     selected_example,
                                                     self.target_lang,
                                                     self.native_lang )

        self.translation_thread.translation_done.connect( self.on_translation_done )
        self.translation_thread.start()

    def on_translation_done( self, translated_items ):
        """
        gets called whenever the translation thread has finished its job

        updates the translation text box
        """

        # sometimes the translater capitalizes the translated word for no reason;
        # below is a dirty hack around that
        translated_word, translated_example = translated_items
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
        instantiate an audio thread that creates an audio file from the example
        word and sentence
        """
        self.listen_button.setText( "Creating audio..." )
        self.listen_button.setEnabled( False )

        selected_word, selected_example = self.get_current_word_and_example()
        self.audio_thread = AudioThread( selected_word + ". " + selected_example,
                                         "tmp-audio.mp3", self.target_lang )
        self.audio_thread.audio_done.connect( self.on_audio_ready )
        self.audio_thread.start()

    def on_audio_ready( self ):
        """
        play generated audio - called when audio thread is done creating it
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
        a temporary audio file may have been created if the "Listen" button has
        been clicked; clean it up

        called upon MainWindow closing
        """
        if os.path.isfile( "tmp-audio.mp3" ):
            os.unlink( "tmp-audio.mp3" )

    def save_card( self ):
        """
        save the front and the back text (with any user modifications) as an
        instance of custom class Flashcard
        """
        front_text = self.front_text_edit.toHtml()
        back_text = self.back_text_edit.toHtml()

        if front_text and back_text:
            new_flashcard = Flashcard( front_text, back_text )
            self.flashcards.append( new_flashcard )

            write_flashcard_to_backup( BACKUP_FNAME, self.flashcards[ -1 ],
                                       self.sub_fpath, self.target_lang,
                                       self.native_lang, self.deck_name_to_id )

        self.update_flashcard_counter()

    def view_cards( self ):
        """
        open a FlashcardViewer dialog to view and potentially delete any currently
        saved flashcards
        """
        self.flashcard_viewer = FlashcardViewer( self.flashcards )
        self.flashcard_viewer.exec_()
        self.update_flashcard_counter()

    def update_flashcard_counter( self ):
        """
        update the flashcard counter

        limitation: is only called upon clicking "Save card" or closing the
        FlashcardViewer i.e. if you have the FlashcardViewer still open and are
        deleting cards, the number will only update once you close the
        FlashcardViewer
        """
        self.flashcard_counter.setText( str( len( self.flashcards ) ) )
        self.export_button.setEnabled( len( self.flashcards ) > 0 )

    def export_flashcards( self ):
        export_to_anki( self.flashcards, self.deck_name_to_id,
                        self.out_path + separate_fpath( self.sub_fpath )[ 1 ] )

        # session export successful, so clear the backup
        os.unlink( BACKUP_FNAME )

        self.flashcards.clear()
        self.update_flashcard_counter()

if __name__ == "__main__":
    app = QApplication( sys.argv )

    app.setStyleSheet( "QWidget { font-size: 17px; }" )

    # tracker variable for use when session backup is found
    restore = False

    # session preference initialization
    if os.path.isfile( BACKUP_FNAME ):
        # previous session crashed or was closed without saving
        saved_data = read_flashcard_backup( BACKUP_FNAME )

        sub_fpath = saved_data[ 0 ]
        target_lang = saved_data[ 1 ]
        native_lang = saved_data[ 2 ]
        deck_name_to_id = saved_data[ 3 ]
        flashcards = saved_data[ 4 ]

        # ask user if they want to use found backup
        restore = show_restore_dialog( len( flashcards ) )

    # if no backup from prev session found, or user chose to discard found backup;
    # remove backup file if any and get the preferences from user
    if not restore:
        if os.path.isfile( BACKUP_FNAME ):
            os.unlink( BACKUP_FNAME )

        selection_dialog = SessionSelectionDialog(
            user_sessions_file="user_sessions.json" )

        if selection_dialog.exec_() == QDialog.Accepted:
            session_name, deck_name_to_id, target_lang_name, native_lang_name =\
                selection_dialog.get_selection()
        else:
            QMessageBox.warning( None, "No Session Selected",
                                 "No session selected. Exiting." )
            sys.exit()

        sub_fpath = select_subtitle_file()
        if not sub_fpath:
            QMessageBox.warning( None, "No File Selected",
                                 "No subtitle file selected. Exiting." )
            sys.exit()

        # convert language names to abbreviated codes
        target_lang = LANG_CODE[ target_lang_name ]
        native_lang = LANG_CODE[ native_lang_name ]

        # starting fresh session, so no flashcards saved from before
        flashcards = None
    # END session preference initialization

    mainWindow = MainWindow( sub_fpath=sub_fpath,
                             target_lang=target_lang,
                             native_lang=native_lang,
                             deck_name_to_id=deck_name_to_id,
                             flashcards=flashcards )

    app.aboutToQuit.connect( MainWindow.clean_up_temp_audio )
    mainWindow.show()
    sys.exit( app.exec_() )
