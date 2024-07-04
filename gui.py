import sys
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QTextEdit,
    QPushButton
)

class MainWindow( QWidget ):
    def __init__( self ):
        super().__init__()
        self.initUI()

    def initUI( self ):
        self.setWindowTitle( "Text Analyzer" )
        self.setGeometry( 100, 100, 800, 600 )

        # Layout
        layout = QHBoxLayout( self )
        self.left_section = QListWidget()
        self.middle_section = QListWidget()
        self.right_section = QTextEdit()
        self.translate_button = QPushButton( "Translate" )

        # Set up layout
        layout.addWidget( self.left_section )
        layout.addWidget( self.middle_section )
        layout.addWidget( self.right_section )
        layout.addWidget( self.translate_button )

        # Connect signals and slots
        self.left_section.itemSelectionChanged.connect( self.updateExamples )
        self.translate_button.clicked.connect( self.translateExample )

        # Load data ( replace with your data loading logic )
        self.loadTopWords()
        if self.left_section.count() > 0:
            self.left_section.setCurrentRow( 0 )  # Select first word by default
            self.updateExamples()

    def loadTopWords( self ):
        # Replace with your logic to load top words
        top_words = ["Word1", "Word2", "Word3", "Word4", "Word5", "Word6", "Word7", "Word8", "Word9", "Word10",
                     "Word11", "Word12", "Word13", "Word14", "Word15", "Word16", "Word17", "Word18", "Word19", "Word20"]
        self.left_section.addItems( top_words )

    def updateExamples( self ):
        # Replace with your logic to update examples based on selected word
        selected_word = self.left_section.currentItem().text()
        # Dummy examples ( replace with your logic )
        examples = [f"{selected_word} example 1", f"{selected_word} example 2", f"{selected_word} example 3"]
        self.middle_section.clear()
        self.middle_section.addItems( examples )
        if self.middle_section.count() > 0:
            self.middle_section.setCurrentRow( 0 )  # Select first example by default

    def translateExample( self ):
        # Replace with your translation logic
        selected_example = self.middle_section.currentItem().text()
        translated_text = f'Translation of "{selected_example}" goes here.'
        self.right_section.setPlainText( translated_text )

if __name__ == "__main__":
    app = QApplication( sys.argv )
    mainWindow = MainWindow()
    mainWindow.show()
    sys.exit( app.exec_() )
