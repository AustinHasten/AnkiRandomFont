from aqt.qt import Qt, QWidget, QVBoxLayout, QScrollArea, QHBoxLayout, QPushButton, QCheckBox, QButtonGroup, QRadioButton
from anki.hooks import wrap
from aqt import mw, gui_hooks
from aqt.utils import showText
from aqt.previewer import Previewer
from .finderWidgets import DeckFinderWidget, NoteTypeFinderWidget, CardStateFinderWidget, TagFinderWidget, SuccessRateFinderWidget, PassFinderWidget, FieldFinderWidget
from .utils import MyGroupBox

# NOTE CardLayout appears to pass 0 rather than the real card.id to card_will_show,
#   so don't think we can edit text in cardlayout?
# NOTE Should panels have unique config keys instead in case two fall under the same thing?
# would mean you gotta update those keys if they change for whatever reason

originalPreviewerBridgeCmd = Previewer._on_bridge_cmd


def previewerAns(self, cmd: str):
    if cmd == 'ans':
        self._state = 'answer'
        self.render_card()


class DefaultFinderPanel(QWidget):
    defaults = {
        'logic': 0,
        'negate': False,
        'applyToPreviewer': True,
    }

    def __init__(self, modifyQ, modifyA, configRoot, name):
        super().__init__()
        self.modifyQ = modifyQ
        self.modifyA = modifyA
        self.config = configRoot.addBranch(name, self.defaults)
        self.widgetsConfig = self.config.addBranch('widgets')
        self.name = name
        self.finders = []
        gui_hooks.card_will_show.append(self.checkCard)
        self.buildGUI()
        self.readConfig()

        self.previewerToggled(self.previewerCheck.checkState().value)

    def checkCard(self, text, card, kind):
        if kind in ('clayoutQuestion', 'clayoutAnswer'):
            return text
        doesMatch = self.confirmMatch(card)
        if not doesMatch:
            return text
        if kind in ('reviewQuestion', 'previewQuestion'):
            return self.modifyQ(text)
        elif kind in ('reviewAnswer', 'previewAnswer'):
            return self.modifyA(text)

    def confirmMatch(self, card):
        matches = [f.checkMatch(card) for f in self.finders if f.isChecked()]
        if not matches:  # Should mean that no finders are checked
            doesMatch = False
        elif self.logic() == 'or':
            doesMatch = any(matches)
        elif self.logic() == 'and':
            doesMatch = all(matches)
        else:
            raise Exception('Invalid logic')

        if self.negateCheckBox.isChecked():
            doesMatch = not doesMatch
        return doesMatch

    def unhook(self):
        gui_hooks.card_will_show.remove(self.checkCard)

    def buildGUI(self):
        # Holds the inner layout, after which other stuff can be added
        self.outerLayout = QVBoxLayout(self)
        # Holds the finder widgets
        self.innerWidget = QWidget()

        # Make outerLayout scroll
        self.scroll = QScrollArea()
        self.scroll.setWidget(self.innerWidget)
        self.scroll.setWidgetResizable(True)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Create finders
        self.deckFinder = DeckFinderWidget(self.widgetsConfig)
        self.noteTypeFinder = NoteTypeFinderWidget(self.widgetsConfig)
        self.cardStateFinder = CardStateFinderWidget(self.widgetsConfig)
        self.tagFinder = TagFinderWidget(self.widgetsConfig)
        self.successRateFinder = SuccessRateFinderWidget(self.widgetsConfig)
        self.passNumberFinder = PassFinderWidget(self.widgetsConfig)
        self.fieldFinder = FieldFinderWidget(self.widgetsConfig)

        # Maintain a list of finders to act on all of them at once
        self.finders.append(self.deckFinder)
        self.finders.append(self.noteTypeFinder)
        self.finders.append(self.cardStateFinder)
        self.finders.append(self.tagFinder)
        self.finders.append(self.successRateFinder)
        self.finders.append(self.passNumberFinder)
        self.finders.append(self.fieldFinder)

        # TODO Fix these whole below section. It's so messy
        self.logicGroupBoxOuter = MyGroupBox('Logic', QHBoxLayout)
        self.logicGroupBoxInner = MyGroupBox('', QHBoxLayout)
        self.logicGroupBoxOuter.layout.addWidget(self.logicGroupBoxInner)

        self.orRadio = QRadioButton('or')
        self.andRadio = QRadioButton('and')
        self.logicGroupBoxInner.layout.addWidget(self.orRadio)
        self.logicGroupBoxInner.layout.addWidget(self.andRadio)
        self.logicButtonGroup = QButtonGroup()
        self.logicButtonGroup.addButton(self.orRadio, id=0)
        self.logicButtonGroup.addButton(self.andRadio, id=1)

        self.negateCheckBox = QCheckBox('Negate')
        self.logicGroupBoxOuter.layout.addWidget(self.negateCheckBox)

        self.applyToGroupBox = MyGroupBox('Apply to', QHBoxLayout)
        self.reviewerCheck = QCheckBox('Reviewer')
        self.reviewerCheck.setChecked(True)
        self.reviewerCheck.setEnabled(False)
        self.previewerCheck = QCheckBox('Previewer')
        self.applyToGroupBox.layout.addWidget(self.reviewerCheck)
        self.applyToGroupBox.layout.addWidget(self.previewerCheck)

        self.previewBtn = QPushButton('Preview this Search')

        self.innerLayout = QVBoxLayout(self.innerWidget)
        self.innerLayout.addWidget(self.applyToGroupBox)
        self.innerLayout.addWidget(self.logicGroupBoxOuter)
        for finder in self.finders:
            self.innerLayout.addWidget(finder)
        self.outerLayout.addWidget(self.scroll)
        self.outerLayout.addWidget(self.previewBtn)

        # Signals/slots
        self.previewerCheck.stateChanged.connect(self.previewerToggled)
        self.previewBtn.pressed.connect(self.previewPressed)

        # Finishing touches
        self.outerLayout.setContentsMargins(0, 0, 0, 0)
        self.innerLayout.setContentsMargins(5, 5, 5, 5)

    def previewerToggled(self, state):
        if state == Qt.CheckState.Checked.value:
            Previewer._on_bridge_cmd = wrap(originalPreviewerBridgeCmd, previewerAns, "after")
        else:
            Previewer._on_bridge_cmd = originalPreviewerBridgeCmd

    def logic(self):
        return self.logicButtonGroup.checkedButton().text()

    def previewPressed(self):
        allcids = mw.col.db.list('SELECT id FROM cards')
        allcards = [mw.col.get_card(cid) for cid in allcids]
        matchingCards = [card for card in allcards if self.confirmMatch(card)]
        bigstr = f'{len(matchingCards)} results: \n\n'
        for card in matchingCards:
            did = card.odid if card.odid else card.did
            deckName = mw.col.decks.get(did)['name']
            note = card.note()
            noteType = card.note_type()
            sortField = note.items()[noteType['sortf']]

            bigstr += f'Card: {card.id}\n'
            bigstr += f'    Deck: {deckName}\n'
            bigstr += f'    {sortField[0]}: {sortField[1]}\n'
            bigstr += f'    NoteType:  {noteType["name"]}\n'
            bigstr += f'    Tags: {note.tags}\n\n'
        showText(bigstr)

    def readConfig(self):
        self.logicButtonGroup.button(self.config.read('logic')).setChecked(True)
        self.negateCheckBox.setChecked(self.config.read('negate'))
        previewerState = self.config.read('applyToPreviewer')
        self.previewerCheck.setChecked(previewerState)

    def writeConfig(self):
        self.config.writes((
            ('logic', self.logicButtonGroup.checkedId()),
            ('negate', self.negateCheckBox.isChecked()),
            ('applyToPreviewer', self.previewerCheck.isChecked()),
        ))
        for finder in self.finders:
            finder.writeConfig()
