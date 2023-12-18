from aqt import mw
from aqt.qt import QVBoxLayout, QHBoxLayout, QGridLayout, QComboBox, QSpinBox, QCheckBox, QButtonGroup, QRadioButton, QLineEdit
from .utils import CollapsibleGroupBox, strip_tags, MyGroupBox
import re

# TODO Only strip_tags if contents or length is checked

# NOTE With field finder, if fieldname regex matches multiple,
# it will use the field that comes first in the field order in Anki


class MetaFinderWidget(CollapsibleGroupBox):
    def __init__(self, configRoot):
        super().__init__(self.label, self.layoutType)
        self.config = configRoot.addBranch(self.label, self.defaults)
        self.buildGUI()
        self.readConfig()

    def checkMatch(self, cid):
        raise Exception('Not Implemented')


class FieldFinderWidget(MetaFinderWidget):
    label = 'Field'
    layoutType = QVBoxLayout
    defaults = {
        'enabled': False,
        'contentsEnabled': False,
        'lengthEnabled': False,
        'kanjiEnabled': False,
        'nameText': '',
        'contentsText': '',
        'lengthComparator': '==',
        'lengthValue': 0,
        'kanjiComparator': '==',
        'kanjiValue': 0,
    }

    def checkMatch(self, card):
        fieldNamePattern = self.fieldNameInput.text()
        if not fieldNamePattern:
            return False

        for fieldName, fieldValue in card.note().items():
            if re.search(fieldNamePattern, fieldName):
                fieldValue = strip_tags(fieldValue)
                if self.contentsGroupBox.isChecked():
                    if not re.search(self.contentsInput.text(), fieldValue):
                        return False
                if self.lengthGroupBox.isChecked():
                    # NOTE Remove spaces. I don't feel they should be counted
                    fieldLen = len(fieldValue.replace(' ', ''))
                    comparator = self.lengthComparators.currentText()
                    target = self.lengthSpin.value()
                    if not eval(f'{fieldLen} {comparator} {target}'):
                        return False
                if self.kanjiGroupBox.isChecked():
                    comparator = self.kanjiComparators.currentText()
                    target = self.kanjiSpin.value()
                    kanjiNum = len(re.findall('[一-龯]', fieldValue))
                    if not eval(f'{kanjiNum} {comparator} {target}'):
                        return False
                return True
        return False

    def buildGUI(self):
        self.fieldNameGroupBox = MyGroupBox('Field Name (regex)', QHBoxLayout)
        self.fieldNameInput = QLineEdit()
        self.fieldNameInput.setPlaceholderText('REGEX')
        self.fieldNameGroupBox.layout.addWidget(self.fieldNameInput)

        self.contentsGroupBox = CollapsibleGroupBox('Field Contents (regex)', QHBoxLayout)
        self.contentsInput = QLineEdit()
        self.contentsInput.setPlaceholderText('REGEX')
        self.contentsGroupBox.layout.addWidget(self.contentsInput)

        self.lengthGroupBox = CollapsibleGroupBox('Field Contents Length', QGridLayout)
        self.lengthComparators = QComboBox()
        self.lengthComparators.addItems(['<', '<=', '==', '>=', '>', '!='])
        self.lengthSpin = QSpinBox()
        self.lengthSpin.setMaximum(999)
        self.lengthGroupBox.layout.addWidget(self.lengthComparators, 0, 0, 1, 1)
        self.lengthGroupBox.layout.addWidget(self.lengthSpin, 0, 1, 1, 3)

        self.kanjiGroupBox = CollapsibleGroupBox('Number of Kanji in Field Contents', QGridLayout)
        self.kanjiComparators = QComboBox()
        self.kanjiComparators.addItems(['<', '<=', '==', '>=', '>', '!='])
        self.kanjiSpin = QSpinBox()
        self.kanjiGroupBox.layout.addWidget(self.kanjiComparators, 0, 0, 1, 1)
        self.kanjiGroupBox.layout.addWidget(self.kanjiSpin, 0, 1, 1, 3)

        self.layout.addWidget(self.fieldNameGroupBox)
        self.layout.addWidget(self.contentsGroupBox)
        self.layout.addWidget(self.lengthGroupBox)
        self.layout.addWidget(self.kanjiGroupBox)

    def readConfig(self):
        self.setChecked(self.config.read('enabled'))
        self.contentsGroupBox.setChecked(self.config.read('contentsEnabled'))
        self.lengthGroupBox.setChecked(self.config.read('lengthEnabled'))
        self.kanjiGroupBox.setChecked(self.config.read('kanjiEnabled'))
        self.fieldNameInput.setText(self.config.read('nameText'))
        self.contentsInput.setText(self.config.read('contentsText'))
        self.lengthComparators.setCurrentText(self.config.read('lengthComparator'))
        self.lengthSpin.setValue(self.config.read('lengthValue'))
        self.kanjiComparators.setCurrentText(self.config.read('kanjiComparator'))
        self.kanjiSpin.setValue(self.config.read('kanjiValue'))

    def writeConfig(self):
        self.config.writes((
            ('enabled', self.isChecked()),
            ('contentsEnabled', self.contentsGroupBox.isChecked()),
            ('lengthEnabled', self.lengthGroupBox.isChecked()),
            ('kanjiEnabled', self.kanjiGroupBox.isChecked()),
            ('nameText', self.fieldNameInput.text()),
            ('contentsText', self.contentsInput.text()),
            ('lengthComparator', self.lengthComparators.currentText()),
            ('lengthValue', self.lengthSpin.value()),
            ('kanjiComparator', self.kanjiComparators.currentText()),
            ('kanjiValue', self.kanjiSpin.value()),
        ))


class DeckFinderWidget(MetaFinderWidget):
    label = 'Deck Name (regex)'
    layoutType = QHBoxLayout
    defaults = {
        'enabled': False,
        'text': ''
    }

    def checkMatch(self, card):
        pattern = self.input.text()
        if not pattern:
            return False
        did = card.odid if card.odid else card.did
        deckName = mw.col.decks.get(did)['name']
        return bool(re.search(pattern, deckName))

    def buildGUI(self):
        self.input = QLineEdit()
        self.input.setPlaceholderText('REGEX')
        self.layout.addWidget(self.input)

    def readConfig(self):
        self.setChecked(self.config.read('enabled'))
        self.input.setText(self.config.read('text'))

    def writeConfig(self):
        self.config.writes((
            ('enabled', self.isChecked()),
            ('text', self.input.text()),
        ))


class NoteTypeFinderWidget(MetaFinderWidget):
    label = 'Note Type (regex)'
    layoutType = QHBoxLayout
    defaults = {
        'enabled': False,
        'text': ''
    }

    def checkMatch(self, card):
        pattern = self.input.text()
        if not pattern:
            return False
        return bool(re.search(pattern, card.note_type()['name']))

    def buildGUI(self):
        self.input = QLineEdit()
        self.input.setPlaceholderText('REGEX')
        self.layout.addWidget(self.input)

    def readConfig(self):
        self.setChecked(self.config.read('enabled'))
        self.input.setText(self.config.read('text'))

    def writeConfig(self):
        self.config.writes((
            ('enabled', self.isChecked()),
            ('text', self.input.text()),
        ))


class TagFinderWidget(MetaFinderWidget):
    label = 'Tags (regex)'
    defaults = {
        'enabled': False,
        'text': '',
        'logic': 0
    }
    layoutType = QHBoxLayout

    def checkMatch(self, card):
        cardTags = card.note().tags
        tagMatches = []
        for tagPattern in self.input.text().split(' '):
            tagMatch = False
            for cardTag in cardTags:
                if re.search(tagPattern, cardTag):
                    tagMatch = True
                    break
            tagMatches.append(tagMatch)
        logic = self.logicButtonGroup.checkedButton().text()
        if logic == 'or':
            return any(tagMatches)
        elif logic == 'and':
            return all(tagMatches)
        else:
            raise Exception('invalid logic')

    def buildGUI(self):
        self.input = QLineEdit()
        self.input.setPlaceholderText('Space-separated REGEX')

        self.logicGroupBox = MyGroupBox('', QHBoxLayout)
        self.orRadio = QRadioButton('or')
        self.andRadio = QRadioButton('and')
        self.logicButtonGroup = QButtonGroup()
        self.logicButtonGroup.addButton(self.orRadio, id=0)
        self.logicButtonGroup.addButton(self.andRadio, id=1)
        self.logicGroupBox.layout.addWidget(self.orRadio)
        self.logicGroupBox.layout.addWidget(self.andRadio)

        self.layout.addWidget(self.input)
        self.layout.addWidget(self.logicGroupBox)

    def readConfig(self):
        self.setChecked(self.config.read('enabled'))
        self.input.setText(self.config.read('text'))
        self.logicButtonGroup.button(self.config.read('logic')).setChecked(True)

    def writeConfig(self):
        self.config.writes((
            ('enabled', self.isChecked()),
            ('text', self.input.text()),
            ('logic', self.logicButtonGroup.checkedId()),
        ))


class CardStateFinderWidget(MetaFinderWidget):
    label = 'Card States'
    layoutType = QHBoxLayout
    defaults = {
        'enabled': False,
        'options': []
    }
    cardStates = [
        ('New', 0),
        ('Learning', 1),
        ('Reviewing', 2),
        ('Relearning', 3)
    ]

    def checkMatch(self, card):
        return card.queue in self.selectedOptions()

    def buildGUI(self):
        self.optionBoxes = QButtonGroup()
        self.optionBoxes.setExclusive(False)
        for txt, val in self.cardStates:
            box = QCheckBox(txt)
            self.optionBoxes.addButton(box, id=len(self.optionBoxes.buttons()))
            self.layout.addWidget(box)

    def selectedOptions(self):
        return [self.optionBoxes.id(b) for b in self.optionBoxes.buttons() if b.isChecked()]

    def readConfig(self):
        self.setChecked(self.config.read('enabled'))
        for option in self.config.read('options'):
            self.optionBoxes.button(option).setChecked(True)

    def writeConfig(self):
        self.config.writes((
            ('enabled', self.isChecked()),
            ('options', self.selectedOptions()),
        ))


class SuccessRateFinderWidget(MetaFinderWidget):
    label = 'Success Rate'
    layoutType = QGridLayout
    defaults = {
        'enabled': False,
        'comparator': '==',
        'value': 0
    }

    def buildGUI(self):
        self.comparators = QComboBox()
        self.comparators.addItems(['<', '<=', '==', '>=', '>', '!='])
        self.layout.addWidget(self.comparators, 0, 0, 1, 1)

        self.spinBox = QSpinBox()
        self.spinBox.setMaximum(100)
        self.spinBox.setSuffix('%')
        self.layout.addWidget(self.spinBox, 0, 1, 1, 3)

    def checkMatch(self, card):
        if card.reps == 0:
            successRate = 100  # TODO Should this be 100 or 0?
        else:
            qry = f'SELECT count(*) FROM revlog WHERE cid = {card.id} AND ease > 1'
            passes = int(mw.col.db.first(qry)[0])
            successRate = passes / card.reps
        comparator = self.comparators.currentText()
        target = self.spinBox.value() / 100
        return eval(f'{successRate} {comparator} {target}')

    def readConfig(self):
        self.setChecked(self.config.read('enabled'))
        self.comparators.setCurrentText(self.config.read('comparator'))
        self.spinBox.setValue(self.config.read('value'))

    def writeConfig(self):
        self.config.writes((
            ('enabled', self.isChecked()),
            ('comparator', self.comparators.currentText()),
            ('value', self.spinBox.value()),
        ))


class PassFinderWidget(MetaFinderWidget):
    label = '# of Passes'
    layoutType = QGridLayout
    defaults = {
        'enabled': False,
        'comparator': '==',
        'value': 0
    }

    def buildGUI(self):
        self.comparators = QComboBox()
        self.comparators.addItems(['<', '<=', '==', '>=', '>', '!='])

        self.spinBox = QSpinBox()
        self.spinBox.setMaximum(100)

        self.layout.addWidget(self.comparators, 0, 0, 1, 1)
        self.layout.addWidget(self.spinBox, 0, 1, 1, 3)

    def checkMatch(self, card):
        qry = f'SELECT count(*) FROM revlog WHERE cid = {card.id} AND ease > 1'
        passes = int(mw.col.db.first(qry)[0])
        comparator = self.comparators.currentText()
        target = self.spinBox.value()
        return eval(f'{passes} {comparator} {target}')

    def readConfig(self):
        self.setChecked(self.config.read('enabled'))
        self.comparators.setCurrentText(self.config.read('comparator'))
        self.spinBox.setValue(self.config.read('value'))

    def writeConfig(self):
        self.config.writes((
            ('enabled', self.isChecked()),
            ('comparator', self.comparators.currentText()),
            ('value', self.spinBox.value()),
        ))
