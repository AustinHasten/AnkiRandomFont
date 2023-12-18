from html.parser import HTMLParser
from io import StringIO
import re
from aqt import mw
from aqt.qt import QWidget, QHBoxLayout, QGroupBox


class MyGroupBox(QGroupBox):
    def __init__(self, label, layoutType):
        super().__init__(label)
        self.containerWidget = QWidget()
        self.dummyLayout = QHBoxLayout(self)  # Could be anything, it just holds the single container widget
        self.dummyLayout.addWidget(self.containerWidget)
        # self.dummyLayout.setContentsMargins(10, 10, 10, 10)

        self.layout = layoutType(self.containerWidget)
        # self.layout.setContentsMargins(10, 10, 10, 10)
        self.setStyleSheet('padding:0px;')


class CollapsibleGroupBox(MyGroupBox):
    def __init__(self, label, layoutType):
        super().__init__(label, layoutType)
        self.setCheckable(True)
        # self.toggled.connect(self.toggle)

    def toggle(self, on):
        if on:
            self.containerWidget.show()
            self.layout.setContentsMargins(5, 5, 5, 5)
            self.setStyleSheet('padding:0px;')
        else:
            self.containerWidget.hide()
            self.layout.setContentsMargins(0, 0, 0, 0)
            self.setStyleSheet('border:0;padding:0px;margin:0px;')


def listsToSet(lists, logic):
    ''' Take a list of lists and return a set that is either the intersection or the union of that. '''
    r = set([item for sublist in lists for item in sublist])  # set(Flatten list of lists)
    if logic == 'or':
        return r
    elif logic == 'and':
        return r.intersection(*lists)
    else:
        raise Exception('Invalid logic option')


class ConfigPath():
    def __init__(self, parentBranch=None, key=None, defaults={}):
        self.parentBranch = parentBranch
        if self.parentBranch:
            self.root = parentBranch.path
        else:
            self.root = []

        self.key = key
        if self.key:
            self.path = self.root + [self.key]
        else:
            self.path = self.root

        self.defaults = defaults

        self.branches = []

    def addBranch(self, key, defaults={}):
        self.branches.append(ConfigPath(self, key, defaults))
        return self.branches[-1]

    def updateKey(self, newKey: str):
        # Move the key in the config file
        config = mw.addonManager.getConfig(__name__)
        root = self.descend(config, self.root)
        root[newKey] = root.pop(self.key)
        mw.addonManager.writeConfig(__name__, config)

        self.key = newKey
        self.path = self.root + [newKey]
        for branch in self.branches:
            branch.updateRoot(self.path)

    def updateRoot(self, newRoot):
        self.root = newRoot
        self.path = self.root + [self.key]
        for branch in self.branches:
            branch.updateRoot(self.path)

    def descend(self, d: dict, path=None):
        if not path:
            path = self
        for p in path:
            if p not in d:
                d[p] = {}
            d = d[p]
        return d

    def read(self, key: str = None):
        config = mw.addonManager.getConfig(__name__)
        root = self.descend(config)
        if key:
            return (self.defaults | root)[key]
        return (self.defaults | root)

    def write(self, key: str, val):
        config = mw.addonManager.getConfig(__name__)
        root = self.descend(config)
        root[key] = val
        mw.addonManager.writeConfig(__name__, config)

    def writes(self, pairs):
        config = mw.addonManager.getConfig(__name__)
        root = self.descend(config)
        for key, val in pairs:
            root[key] = val
        mw.addonManager.writeConfig(__name__, config)

    def delete(self):
        config = mw.addonManager.getConfig(__name__)
        root = self.descend(config, self.root)
        del root[self.key]
        mw.addonManager.writeConfig(__name__, config)
        self.parentBranch.branches.remove(self)

    def __iter__(self):
        return (x for x in self.path)


class MLStripper(HTMLParser):
    '''
    Stolen from https://stackoverflow.com/questions/753052/strip-html-from-strings-in-python
    Used to strip HTML from fields in order to accurately search them and get their lengths
    '''

    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.text = StringIO()

    def handle_data(self, d):
        self.text.write(d)

    def get_data(self):
        return self.text.getvalue()


def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    # Strip out furigana
    withFuri = s.get_data()
    withoutFuri = re.sub(r'\[(.*?)\]', '', withFuri)
    return withoutFuri
