# -*- coding: utf-8 -*-

import aqt.editor
from os.path import  join, dirname
from anki.hooks import addHook, remHook, wrap, runFilter
from anki.lang import _
from aqt.qt import *
from aqt.utils import restoreGeom, saveGeom, tooltip, shortcut
from .miutils import miInfo, miAsk
import aqt
from aqt.editor import EditorWebView
import unicodedata
from aqt.editor import _html
from aqt import mw
import re
import warnings
from bs4 import BeautifulSoup

###old darkmode support, currently unused since Anki 2.1.20 offers a dark-mode natively
darkModeCss = '''

    #topbuts 
        button
        {
            
        color:#AFB9C1;
        margin-top:0;
        position:relative;
        top:0;
        padding:3px 8px;
        border:1px solid #3E474D;
        border-top-color:#1c252b;
        border-left-color:#2d363c;
    
            text-shadow:1px 1px #1f272b;
            display: inline-block;
            background: #313d45;
            background: gradient(linear, left top, left bottom, color-stop(3%%,#3D4850), color-stop(4%%,#313d45), color-stop(100%%,#232B30));
            box-shadow: 1px 1px 1px rgba(0,0,0,0.1);
            border-radius: 3px
        }
        button:hover
        {
            color: #fff;
            background: #404F5A);
            background: gradient(linear, left top, left bottom, color-stop(3%%,#4C5A64), color-stop(4%%,#404F5A), color-stop(100%%,#2E3940));
        }
        button:active
        {
            color: #fff;
            background: #252E34;
            background: gradient(linear, left top, left bottom, color-stop(3%%,#20282D), color-stop(51%%,#252E34), color-stop(100%%,#222A30));
            box-shadow: 1px 1px 1px rgba(255,255,255,0.1);
        }
        
        ::-webkit-scrollbar{
            width: 7px;
        }
        ::-webkit-scrollbar:horizontal {
            height: 7px;
        }
        ::-webkit-scrollbar-track {
            background: #313d45;
        }
        ::-webkit-scrollbar-thumb {
            background: #515d71;
            border-radius: 4px;
        }
        
            #topbutsright button
            {
                padding: inherit;
                margin-left: 1px
            }
            #topbuts img
            {
                filter: invert(1);
                -webkit-filter: invert(1)
            }
            a
            {
                color: 00BBFF
            }
            html, body, #topbuts, .field, .fname, #topbutsOuter
            {
                color: #ffffff!important;
                background: #272828!important
            }
             .accentsBlock{line-height:35px;} .museika{width:22px;height:22px;border-radius:50%% ;border:1px #db4130 dashed} .pitch-box{position:relative} .pitch-box,.pitch-drop,.pitch-overbar{display:inline-block} .pitch-overbar{background-color:#db4130;height:1px;width:100%% ;position:absolute;top:-3px;left:0} .pitch-drop{background-color:#db4130;height:6px;width:2px;position:absolute;top:-3px;right:-2px}</style>
                   
'''

def getMigakuHtml():
    MigakuHtml = join(dirname(__file__), "migakuEditor.html")
    with open(MigakuHtml, "r", encoding="utf-8") as MigakuHtmlFile:
        return MigakuHtmlFile.read() 

def getImageResizingJS():
    imageResizingJS = join(dirname(__file__), "imageResizing.js")
    with open(imageResizingJS, "r", encoding="utf-8") as imageResizingJSFile:
        return imageResizingJSFile.read() 

def getOverwritesJS():
    overwritesJS = join(dirname(__file__), "overwrite.js")
    with open(overwritesJS, "r", encoding="utf-8") as overwritesJSFile:
        return overwritesJSFile.read() 

def getOtherEditorJS():
    OtherEditorJS = join(dirname(__file__), "otherEditors.js")
    with open(OtherEditorJS, "r", encoding="utf-8") as OtherEditorJSFile:
        return OtherEditorJSFile.read() 

Migaku_HTML = getMigakuHtml()
RESIZING_JS = getImageResizingJS()
OTHER_EDITOR_JS = getOtherEditorJS()
OVERWRITES_JS = getOverwritesJS()


def miSetupWeb(self):
        self.migakuEditorNightMode = False
        if self.mw.pm.night_mode():
                self.migakuEditorNightMode = True
        self.darkModeCss = ''
        self.hiddenColorCss = '''.fieldsHidden a, .fieldsHidden pitch-drop, .fieldsHidden high-pitch,.fieldsHidden pitch-overbar,.fieldsHidden pitch-box, .fieldsHidden span, .fieldsHidden div div{
            background-color: #E4E4E4 !important; 
            color:  #E4E4E4 !important;
        }.fieldsHidden span, .fieldsHidden font {color:  #E4E4E4 !important;} '''
        self.web = EditorWebView(self.widget, self)
        self.web.title = "editor"
        self.web.allowDrops = True
        self.web.onBridgeCmd = self.onBridgeCmd
        self.outerLayout.addWidget(self.web, 1)

        righttopbtns = list()
        righttopbtns.append(self._addButton('text_bold', 'bold', _("Bold text (Ctrl+B)"), id='bold'))
        righttopbtns.append(self._addButton('text_italic', 'italic', _("Italic text (Ctrl+I)"), id='italic'))
        righttopbtns.append(self._addButton('text_under', 'underline', _("Underline text (Ctrl+U)"), id='underline'))
        righttopbtns.append(self._addButton('text_super', 'super', _("Superscript (Ctrl++)"), id='superscript'))
        righttopbtns.append(self._addButton('text_sub', 'sub', _("Subscript (Ctrl+=)"), id='subscript'))
        righttopbtns.append(self._addButton('text_clear', 'clear', _("Remove formatting (Ctrl+R)")))
        # The color selection buttons do not use an icon so the HTML must be specified manually
        tip = _("Set foreground colour (F7)")
        righttopbtns.append('''<button tabindex=-1 class=linkb title="{}"
            type="button" onclick="pycmd('colour');return false;">
            <div id=forecolor style="display:inline-block; background: #000;border-radius: 5px;"
            class=topbut></div></button>'''.format(tip))
        tip = _("Change colour (F8)")
        righttopbtns.append('''<button tabindex=-1 class=linkb title="{}"
            type="button" onclick="pycmd('changeCol');return false;">
            <div style="display:inline-block; border-radius: 5px;"
            class="topbut rainbow"></div></button>'''.format(tip))
        righttopbtns.append(self._addButton('text_cloze', 'cloze', _("Cloze deletion (Ctrl+Shift+C)")))
        righttopbtns.append(self._addButton('paperclip', 'attach', _("Attach pictures/audio/video (F3)")))
        righttopbtns.append(self._addButton('media-record', 'record', _("Record audio (F5)")))
        righttopbtns.append(self._addButton('more', 'more'))
        righttopbtns = runFilter("setupEditorButtons", righttopbtns, self)
        topbuts = """
            <div id="topbutsleft" style="float:left;">
                <button title='%(fldsTitle)s' onclick="pycmd('fields')">%(flds)s...</button>
                <button title='%(cardsTitle)s' onclick="pycmd('cards')">%(cards)s...</button>
            </div>
            <div id="topbutsright" style="float:right;">
                %(rightbts)s
            </div>
        """ % dict(flds=_("Fields"), cards=_("Cards"), rightbts="".join(righttopbtns),
                   fldsTitle=_("Customize Fields"),
                   cardsTitle=shortcut(_("Customize Card Templates (Ctrl+L)")))
        if self.migakuEditorNightMode:  
            self.darkModeCss = '''::-webkit-scrollbar{
            width: 7px;
        }
        ::-webkit-scrollbar:horizontal {
            height: 7px;
        }
        ::-webkit-scrollbar-track {
            background: #181818;
        }
        ::-webkit-scrollbar-thumb {
            background: #5E5E5E;
            border-radius: 4px;
        }
        '''
            self.hiddenColorCss = '''.fieldsHidden a, .fieldsHidden pitch-drop, .fieldsHidden high-pitch,.fieldsHidden pitch-overbar,.fieldsHidden pitch-box, .fieldsHidden span, .fieldsHidden div div{
            background-color: #181818 !important; 
            color:  #181818 !important;
        } .fieldsHidden span, .fieldsHidden font {color: #181818 !important;}
        '''
        bgcol = self.mw.app.palette().window().color().name()
        # then load page
        # use when testing js:
        # global Migaku_HTML, RESIZING_JS
        # Migaku_HTML = getMigakuHtml()
        # RESIZING_JS = getImageResizingJS()
        self.web.stdHtml(Migaku_HTML % (
            bgcol, bgcol, self.hiddenColorCss, self.darkModeCss,
            topbuts, 
            _("Show Duplicates"), RESIZING_JS, OVERWRITES_JS),
                         css=["editor.css"],
                         js=["jquery.js", "editor.js"])

mw.migakuEditorLoadedAfterDictionary = True
mw.migakuEditorLoaded = True

def addScripts(self):
    className = type(self.parentWindow).__name__
    if className == 'MigakuEditCurrent':
        miSetupWeb(self)
        if self.mw.migakuEditorLoadedAfterDictionary and hasattr(self.mw, 'migakuDictionary'):
            self.web.parentEditor = self
            addBodyClick(self)
            addHotkeys(self)
    else:
        ogSetupWeb(self)
        # use when testing js:
        # global OTHER_EDITOR_JS, RESIZING_JS
        # RESIZING_JS = getImageResizingJS()
        # OTHER_EDITOR_JS = getOtherEditorJS()
        # OVERWRITES_JS = getOverwritesJS()
        self.web.eval(OTHER_EDITOR_JS%(RESIZING_JS, OVERWRITES_JS))


bodyClick = '''document.addEventListener("click", function (ev) {
        pycmd("bodyClick")
    }, false);'''


def selectedText(page):    
    text = page.selectedText()
    if not text:
        return False
    else:
        return text

def searchTerm(self):
    text = selectedText(self)
    if text:
        text = re.sub(r'\[[^\]]+?\]', '', text)
        text = text.strip()
        if not mw.migakuDictionary or not mw.migakuDictionary.isVisible():
            mw.dictionaryInit(text)
        mw.migakuDictionary.ensureVisible()
        mw.migakuDictionary.initSearch(text)
        if self.title == 'main webview':
            if mw.state == 'review':
                mw.migakuDictionary.dict.setReviewer(mw.reviewer)
        elif self.title == 'editor':
            target = 'Edit'
            mw.migakuDictionary.dict.setCurrentEditor(self.parentEditor, target)

def addBodyClick(self):
    self.web.eval(bodyClick)

def addHotkeys(self):
    self.parentWindow.hotkeyS = QShortcut(QKeySequence("Ctrl+S"), self.parentWindow)
    self.parentWindow.hotkeyS.activated.connect(lambda: searchTerm(self.web))
    self.parentWindow.hotkeyW = QShortcut(QKeySequence("Ctrl+W"), self.parentWindow)
    self.parentWindow.hotkeyW.activated.connect(self.mw.dictionaryInit)


ogSetupWeb = aqt.editor.Editor.setupWeb 
aqt.editor.Editor.setupWeb = addScripts


addonPath = dirname(__file__)

def miOnHtmlEdit(self, field):
    mainEditor = self.parentWindow
    className = type(mainEditor).__name__        
    if className == 'MigakuEditCurrent':
        
        d = QDialog(self.widget)
        d.setModal(True)
        form = aqt.forms.edithtml.Ui_Dialog()
        form.setupUi(d)
        form.buttonBox.helpRequested.connect(lambda: openHelp("editor"))
        form.textEdit.setPlainText(self.note.fields[field])
        d.show()
        form.textEdit.moveCursor(QTextCursor.End)
        d.exec_()
        html = form.textEdit.toPlainText()
        # filter html through beautifulsoup so we can strip out things like a
        # leading </div>
        with warnings.catch_warnings() as w:
            warnings.simplefilter("ignore", UserWarning)
            html = str(BeautifulSoup(html, "html.parser"))
        self.note.fields[field] = html
        self.note.flush()
        self.loadNote(focusTo=field)
        mainEditor.refreshReviewer()
    else:
        ogHTMLEDIT(self, field)

ogHTMLEDIT = aqt.editor.Editor._onHtmlEdit
aqt.editor.Editor._onHtmlEdit = miOnHtmlEdit

class MigakuEditCurrent(QDialog):
    def __init__(self, mw):
        QDialog.__init__(self, None, Qt.Window)
        mw.setupDialogGC(self)
        self.mw = mw
        self.mw.reviewer.web.eval('clearEditorWindows(); ALLOW_FIELD_EDITS = false;')
        self.form = aqt.forms.editcurrent.Ui_Dialog()
        self.form.setupUi(self)
        self.form.verticalLayout.setContentsMargins(0,0,0,0)
        self.form.buttonBox.setContentsMargins(0,0,10,10)
        self.setWindowTitle("Migaku Editor")
        self.setMinimumHeight(400)
        self.setMinimumWidth(250)
        self.form.buttonBox.button(QDialogButtonBox.Close).setShortcut(
            QKeySequence("Ctrl+Return")
        )
        self.editor = aqt.editor.Editor(self.mw, self.form.fieldsArea, self)
        self.editor.card = self.mw.reviewer.card
        # self.editor.tags.textEdited.connect(self.saveTagsReload)
        self.editor.tags.hotkeyReturn = QShortcut(QKeySequence(QKeySequence(Qt.Key_Return)), self)
        self.editor.tags.hotkeyReturn.activated.connect(self.saveTagsReload)
        self.editor.tags.hotkeyEnter = QShortcut(QKeySequence(QKeySequence(Qt.Key_Enter)), self)
        self.editor.tags.hotkeyEnter.activated.connect(self.saveTagsReload)
        if self.mw.reviewer.state == "answer":
            self.unBlur()
            self.editor.setNote(self.mw.reviewer.card.note(), focusTo=0)
        else:
            self.setFocus()
            self.blur()
            self.editor.setNote(self.mw.reviewer.card.note())
        restoreGeom(self, "editcurrent")
        addHook("reset", self.onReset)
        if self.mw.pm.night_mode():
            1
            self.editor.tags.parent().setStyleSheet('border: none; margin-top: 0px;')
        self.show()


        self.setWindowIcon(QIcon(join(addonPath, 'icons', 'migaku.png')))
        
    def saveTagsReload(self):
        text = self.editor.tags.text()

        tagsTxt = unicodedata.normalize("NFC", text)
        self.editor.note.tags = self.mw.col.tags.canonify(self.mw.col.tags.split(tagsTxt))
        suffix = ''
        if text.endswith(' '):
            suffix = ' '
        self.editor.tags.setText(self.mw.col.tags.join(self.editor.note.tags).strip() + suffix)
        self.reloadCard()

    def reloadCard(self):
        self.editor.note.flush()
        self.mw.col.save()
        browser = aqt.DialogManager._dialogs["Browser"][1]
        if browser:
            browser.model.reset()
        self.refreshReviewer()

    def refreshReviewer(self):
        try:
            self.mw.reviewer.card.load()
            if self.mw.reviewer.state == 'answer':
                self.mw.reviewer.showAnswerWithoutAudio(self.mw.reviewer)
            elif self.mw.reviewer.state == 'question':
                self.mw.reviewer.showQuestionWithoutAudio(self.mw.reviewer)
        except:
            return

    def blur(self):
        if not self.mw.reviewer.state == "answer":
            try:
                self.editor.web.eval('blur(); enableScroll();') 
            except:
                return

    def unBlur(self):
        try:
            self.editor.web.eval('unBlur(); enableScroll();') 
        except:
            return

    def onReset(self):
        # lazy approach for now: throw away edits
        try:
            n = self.editor.note
            n.load()  # reload in case the model changed
            self.editor.setNote(n)
        except:
            return
        

    def reopen(self, mw):
        self.saveAndClose()

    def reject(self):
        self.saveAndClose()

    def saveAndClose(self):
        self.editor.saveTags()

        self.reloadCard()
        self._saveAndClose()
        self.mw.previousMigakuEditorValues = []
        if mw.migakuEditFields.text() == "Disable In-place Editing":
            self.mw.reviewer.web.eval('ALLOW_FIELD_EDITS = true;')

    def _saveAndClose(self):
        remHook("reset", self.onReset)
        saveGeom(self, "editcurrent")
        aqt.dialogs.markClosed("EditCurrent")
        QDialog.reject(self)
        self.editor.web.close()
        self.editor.web.deleteLater()

   

    def closeWithCallback(self, onsuccess):
        self.saveAndClose()



