import random
from aqt.qt import Qt, qconnect, QFontDatabase, QGridLayout, QListWidgetItem, QListWidget, QPushButton, QLabel, QLineEdit, QWidget, QFont, QVBoxLayout, QTabWidget, QStackedWidget, QComboBox, QMessageBox, QAction
from aqt import mw
from .finderPanels import DefaultFinderPanel
from .utils import ConfigPath

writingSystems = {QFontDatabase.writingSystemName(v): v for v in QFontDatabase.writingSystems()}
writingSystems = dict(sorted(writingSystems.items()))  # Sort alphabetically by language name rather than int value


class StackWidget(QWidget):
    def __init__(self, language, configRoot):
        super().__init__()
        self.language = language
        fonts = QFontDatabase.families(writingSystems[self.language])
        self.config = configRoot.addBranch(language, {font: True for font in fonts})

        # Create widgets
        self.layout = QGridLayout(self)
        self.fontList = QListWidget()
        self.fontList.setSortingEnabled(True)
        self.enableBtn = QPushButton('Enable All')
        self.disableBtn = QPushButton('Disable All')
        self.exLbl = QLabel('Example text:')
        self.example = QLineEdit()

        # Populate font list
        for font in fonts:
            listItem = QListWidgetItem(font, self.fontList)
            checkState = self.config.read(font)
            listItem.setCheckState(Qt.CheckState.Checked if checkState else Qt.CheckState.Unchecked)

        # Connect slots to signals
        self.enableBtn.pressed.connect(self.enablePressed)
        self.disableBtn.pressed.connect(self.disablePressed)
        self.fontList.currentItemChanged.connect(self.fontSelected)

        # Finishing touches
        self.fontList.setCurrentRow(0)
        self.fontSelected(self.fontList.currentItem())
        ws = writingSystems[self.language]
        self.example.setPlaceholderText(QFontDatabase.writingSystemSample(ws))

        # Add widgets to layout
        self.layout.addWidget(self.fontList, 0, 0, 4, 4)
        self.layout.addWidget(self.enableBtn, 4, 0, 1, 2)
        self.layout.addWidget(self.disableBtn, 4, 2, 1, 2)
        self.layout.addWidget(self.exLbl, 5, 0, 1, 1)
        self.layout.addWidget(self.example, 5, 1, 1, 3)

    def enablePressed(self):
        for f in self.fontListItems():
            f.setCheckState(Qt.CheckState.Checked)

    def disablePressed(self):
        for f in self.fontListItems():
            f.setCheckState(Qt.CheckState.Unchecked)

    def fontSelected(self, currentItem):
        self.example.setFont(QFont(currentItem.text()))

    def fontListItems(self):
        return [self.fontList.item(i) for i in range(self.fontList.count())]

    def enabledFonts(self):
        return [f.text() for f in self.fontListItems() if f.checkState() == Qt.CheckState.Checked]

    def writeConfig(self):
        pairs = []
        for f in self.fontListItems():
            if f.checkState() == Qt.CheckState.Checked:
                pairs.append((f.text(), True))
            else:
                pairs.append((f.text(), False))
        self.config.writes(pairs)


class RandomFontConfigWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.config = ConfigPath()
        self.panelsConfig = self.config.addBranch('panels')
        self.languagesConfig = self.config.addBranch('languages')
        self.buildGUI()

    def buildGUI(self):
        # Create widgets
        self.layout = QVBoxLayout(self)
        self.tabWidget = QTabWidget()
        self.finderPanel = DefaultFinderPanel(self.modifyQ, self.modifyA, self.panelsConfig, 'RandomFont')
        self.tabWidget.addTab(self.finderPanel, 'Search')
        self.stack = QStackedWidget()
        self.languageList = QComboBox()
        self.secondTab = QWidget()
        self.secondTabLayout = QVBoxLayout(self.secondTab)
        self.secondTabLayout.addWidget(self.languageList)
        self.secondTabLayout.addWidget(self.stack)
        self.tabWidget.addTab(self.secondTab, 'Configure Fonts')
        self.saveBtn = QPushButton('Save')

        for wsName, wsValue in writingSystems.items():
            self.languageList.addItem(wsName)
            self.stack.addWidget(StackWidget(wsName, self.languagesConfig))

        self.saveBtn.pressed.connect(self.saveBtnPushed)
        self.languageList.currentIndexChanged.connect(self.languageChanged)

        self.layout.addWidget(self.tabWidget)
        self.layout.addWidget(self.saveBtn)

    def saveBtnPushed(self):
        self.finderPanel.writeConfig()
        for i in range(self.stack.count()):
            self.stack.widget(i).writeConfig()
        QMessageBox.about(self, 'Saved!', 'Saved!')

    def languageChanged(self, i):
        self.stack.setCurrentIndex(i)

    def modifyQ(self, text):
        styles = ''
        for i in range(self.stack.count()):
            widget = self.stack.widget(i)
            language = widget.language

            # Assume checking for the name of the language on the card is more performant
            if language not in text:
                continue

            enabledFonts = widget.enabledFonts()
            if enabledFonts:
                chosenFont = random.choice(enabledFonts)
            else:  # Fallback to default font
                chosenFont = QFontDatabase.systemFont(QFontDatabase.GeneralFont).family()

            # Add a hidden tooltip to show name of font. User to show it with css if wanted.
            text = text + '''
                <span id="{language}FontName" class="tippyhover" style="display:none;">
                    <ruby><rb>{language}Font</rb><rt>{font}</rt></ruby>
                </span>
                <script>
                    var {language}ChosenFont = "{font}";
                    var {language}Tooltip = document.getElementById("{language}FontName");
                </script>
            '''.format(language=language, font=chosenFont)

            # Add css rule to apply the random font to things with the language name as a class
            styles = styles + f".{language} {{font-family: {chosenFont};}}"

        # Apply the css rules
        text = text + '''
            <script>
                /* If I add this to qa instead of document, the stylesheet apparently gets deleted
                   when a new card is shown, which is what I want */
                var qa = document.getElementById("qa");
                var randomFontStyleSheet = document.createElement("style");
                randomFontStyleSheet.innerText = "{}";
                qa.appendChild(randomFontStyleSheet);
            </script>
        '''.format(styles)

        return text

    def modifyA(self, text):
        for i in range(self.stack.count()):
            language = self.stack.widget(i).language
            if language not in text:
                continue
            text = text + f'<script>qa.append({language}Tooltip);</script>'
        return text + '<script>qa.appendChild(randomFontStyleSheet);</script>'


def showConfig():
    widget.show()


mw.myfw = widget = RandomFontConfigWidget()
action = QAction('Configure Random Fonts', mw)
qconnect(action.triggered, showConfig)
mw.form.menuTools.addAction(action)
