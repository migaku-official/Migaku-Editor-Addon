# -*- coding: utf-8 -*-
# 
from os.path import  join, dirname
import re
import aqt
from anki.utils import bodyClass, stripHTML, isWin
from anki.hooks import addHook, wrap, runHook, runFilter
from aqt import mw
from aqt import DialogManager
from .miutils import miInfo, miAsk
from .miaEditor import MIAEditCurrent
import requests 
import urllib.parse
import unicodedata
import json
import time
from aqt.tagedit import TagEdit
from aqt.main import AnkiQt, gui_hooks
from aqt.qt import *
from aqt.reviewer import Reviewer
from . import Pyperclip 
from pathlib import Path
import anki
import anki.backend_pb2 as pb
from anki.rsbackend import TemplateReplacementList, proto_replacement_list_to_native
from typing import Dict, Tuple
import unicodedata
from .miPasteHandler import PasteHandler


miaPasteHander = PasteHandler()

def closeEditor(*args):
    miaEditor = aqt.DialogManager._dialogs["EditCurrent"][1]
    if miaEditor:
        miaEditor.saveAndClose()

def maybeCloseMIAEditor(self, state: str, *args):
    miaEditor = aqt.DialogManager._dialogs["EditCurrent"][1]
    if self.state == 'review' and miaEditor and state != 'review':
        miaEditor.saveAndClose()

def unblurMIAEditor(*args):
    miaEditor = aqt.DialogManager._dialogs["EditCurrent"][1]
    if miaEditor:
        miaEditor.unBlur()

def blurMIAEditor(*args):
    miaEditor = aqt.DialogManager._dialogs["EditCurrent"][1]
    if miaEditor:
        miaEditor.blur()

def saveConfig(value, name):
    newConf= getConfig()
    newConf[name] = value
    mw.addonManager.writeConfig(__name__, newConf)

def toggleFieldEditing():
    
    if mw.miaEditFields.text() == "Enable In-place Editing":
        mw.miaEditFields.setText("Disable In-place Editing")
        miaEditor = aqt.DialogManager._dialogs["EditCurrent"][1]
        if mw.reviewer and not miaEditor:
            mw.reviewer.web.eval('ALLOW_FIELD_EDITS = true;')
        saveConfig(True, 'editFields')
    else:
        mw.miaEditFields.setText("Enable In-place Editing")
        if mw.reviewer:
            mw.reviewer.web.eval('ALLOW_FIELD_EDITS = false;')
        saveConfig(False, 'editFields')

def toggleShowEmpty():
    if mw.miaShowEmpty.text() == "Show Empty Fields":
        mw.miaShowEmpty.setText("Hide Empty Fields")
        if mw.reviewer:
            mw.reviewer.web.eval('SHOW_EMPTY_FIELDS = true;')
        saveConfig(True, 'showEmptyFields')
    else:
        mw.miaShowEmpty.setText("Show Empty Fields")
        if mw.reviewer:
            mw.reviewer.web.eval('SHOW_EMPTY_FIELDS = false;')
        saveConfig(False, 'showEmptyFields')
    if mw.reviewer.state == 'answer':
        mw.reviewer.showAnswerWithoutAudio(mw.reviewer)
    elif mw.reviewer.state == 'question':
        mw.reviewer.showQuestionWithoutAudio(mw.reviewer)

def getConfig():
    return mw.addonManager.getConfig(__name__)

def setupGuiMenu():
    addMenu = False
    if not hasattr(mw, 'MIAMainMenu'):
        mw.MIAMainMenu = QMenu('MIA',  mw)
        addMenu = True
    if not hasattr(mw, 'MIAMenuSettings'):
        mw.MIAMenuSettings = []
    config = getConfig()
    text = "Disable In-place Editing"
    if not config['editFields']:
        text = "Enable In-place Editing" 
    text2 = 'Hide Empty Fields'
    if not config['showEmptyFields']:
        text2 = 'Show Empty Fields'
    mw.miaShowEmpty = QAction(text2, mw)
    mw.miaShowEmpty.triggered.connect(toggleShowEmpty)
    mw.MIAMenuSettings.insert(0, mw.miaShowEmpty)

    mw.miaEditFields = QAction(text, mw)
    mw.miaEditFields.triggered.connect(toggleFieldEditing)
    mw.MIAMenuSettings.insert(0, mw.miaEditFields)
    
    mw.MIAMainMenu.clear()
    for act in mw.MIAMenuSettings:
        mw.MIAMainMenu.addAction(act)
    if hasattr(mw, 'MIAMenuActions'):
        mw.MIAMainMenu.addSeparator()
        for act in mw.MIAMenuActions:
            mw.MIAMainMenu.addAction(act)

    if addMenu:
        mw.form.menubar.insertMenu(mw.form.menuHelp.menuAction(), mw.MIAMainMenu)

setupGuiMenu()

def getImageResizingJS():
    imageResizingJS = join(dirname(__file__), "imageResizing.js")
    with open(imageResizingJS, "r", encoding="utf-8") as imageResizingJSFile:
        return imageResizingJSFile.read() 

def getEditEventJS():
    inlineEditor = join(dirname(__file__), "inlineEditor.js")
    with open(inlineEditor, "r", encoding="utf-8") as inlineEditorFile:
        return inlineEditorFile.read() 

def addEventsToFields(self):
    editFields = 'true'
    if mw.miaEditFields.text() == "Enable In-place Editing":
        editFields = 'false'
    showEmpty = 'true'
    if mw.miaShowEmpty.text() == "Show Empty Fields":
        showEmpty = 'false'
    editEventJS = getEditEventJS() 
    self.web.eval(editEventJS%(editFields, showEmpty, getImageResizingJS()))
    clearAndDisableIfPersitentEditor(self)

def clearAndDisableIfPersitentEditor(reviewer):
    miaEditor = aqt.DialogManager._dialogs["EditCurrent"][1]
    if miaEditor:
        reviewer.web.eval('clearEditorWindows(); ALLOW_FIELD_EDITS = false;')    


def getHTMLFieldNote(self, cmd):
    split = cmd.split('◱')
    html = json.loads(split[1])[0]
    field = split[2]
    note = self.card.note()
    html = stripImageTitles(html)
    return html, field, note

def mylinkhandler(self, cmd):
    if cmd.startswith('bodyClick'):
       miaEditor = aqt.DialogManager._dialogs["EditCurrent"][1]
       if miaEditor:
            miaEditor.blur()
       return
    elif cmd.startswith('miaStyledPaste'):
       miaPasteHander.onPaste()
    elif cmd.startswith('miaPaste'):
       miaPasteHander.onPaste()
    elif cmd.startswith('getFieldForEdit:'):
        field = cmd.split(':')[1]
        if field == 'Tags':
            self.web.eval('setFieldValue(\'["' + self.mw.col.tags.join(self.card.note().tags).strip().replace("\\", "\\\\").replace("'", "\\'") + '"]\', \''+ field + '\');')
        else:
            self.web.eval('setFieldValue(\'[' + json.dumps(self.card.note()[field], ensure_ascii=False).replace("\\", "\\\\").replace("'", "\\'") + ']\', \''+ field + '\');')
        self.web.setFocus()
    elif cmd.startswith('finalizeTagsEdit◱'):
        html, field, note = getHTMLFieldNote(self, cmd)
        tagsTxt = unicodedata.normalize("NFC", stripHTML(html))
        note.tags = self.mw.col.tags.canonify(self.mw.col.tags.split(tagsTxt))
        note.flush()
        self.card.load()
        reloadReviewer(self)
        refreshBrowser()
    elif cmd.startswith('finalizeEdit◱'):
        html, field, note = getHTMLFieldNote(self, cmd)
        if field == 'Tags':
            return
        else:
            note[field] = html
        note.flush()
        self.card.load()
        refreshBrowser()
    elif cmd.startswith('miReload'):
        reloadReviewer(self)
    elif  cmd.startswith('editGenChin◱'):
        html, field, note = getHTMLFieldNote(self, cmd)
        if field == 'Tags':
            return
        else:
            if hasattr(mw, 'MIAChinese') and mw.MIAChinese:
                genned = mw.MIAChinese.fetchParsed(html, field, note)
                note[field] = genned
                updateReviewerContents(self, note)
    elif  cmd.startswith('editGoButton◱'):
        html, field, note = getHTMLFieldNote(self, cmd)
        if field == 'Tags':
            return
        else:
            if hasattr(mw, 'Exporter') and mw.Exporter:
                genned = mw.Exporter.fetchIndividualExport(html, note)
                note[field] = genned
                updateReviewerContents(self, note)
    elif  cmd.startswith('editBunButton◱'):
        html, field, note = getHTMLFieldNote(self, cmd)
        if field == 'Tags':
            return
        else:
            if hasattr(mw, 'Exporter') and mw.Exporter:
                genned = mw.Exporter.fetchParsedField(html, note)
                note[field] = genned
                updateReviewerContents(self, note)
    else:
        ogRevLinkHandler(self, cmd)
  

def updateReviewerContents(reviewer, note):
    note.flush()
    reviewer.card.load()
    reloadReviewer(reviewer)
    refreshBrowser()

def refreshBrowser():
    browser = aqt.DialogManager._dialogs["Browser"][1]
    if browser:
        browser.model.reset()             

def stripImageTitles(html): 
    return html.replace('title="Click+Drag:\n(Left⇔Right)\nResize with aspect ratio.\n\t\nCtrl+Click+Drag:\nResize freely.\n\t\nShift+Click:\nRestore original size."', '')

def reloadReviewer(reviewer):
    if reviewer.state == "answer":
        reviewer.showAnswerWithoutAudio(reviewer)
    else:
        reviewer.showQuestionWithoutAudio(reviewer)
         
def getFieldOrdinal(self, note, field):
        fields = note._model["flds"]
        for f in fields:
            if field == f['name']:
                return f['ord']
        else:
            return False

def getCleanedFieldName(fn):
    if ':' in fn:
        splitResult = fn.split(':')
        return splitResult[len(splitResult) - 1]
    return fn

def getEditableFields(text):
    pattern = r'(<div.*?display-type=\".+?\" class=\"wrapped-.{3,4}nese\">{{([^#^\/]+?)}}<\/div>)|({{([^#^\/]+?)}})'
    linksScriptsPattern = r'<a[^>]+?href=[^>]+?>|\<script\>[\s\S]+<\/script>'
    linksScripts = re.findall(linksScriptsPattern, text)
    text = re.sub(linksScriptsPattern, '◱link◱', text)
    matches = re.findall(pattern, text)
    alreadyReplaced = []
    for m in matches:
        raw, fieldname, raw2, fieldname2 = m
        if raw:
            toReplace = raw
            fn = fieldname
        else:
            toReplace = raw2
            fn = fieldname2
        if toReplace not in alreadyReplaced:
            fn = getCleanedFieldName(fn)
            text = text.replace(toReplace, '<div style="display:inline-block;" class="editableField" data-field="' + fn + '" ondblclick="mieditField(this, \'' + fn + '\')">' + toReplace + "</div>")
            alreadyReplaced.append(toReplace)
    for link in linksScripts:
        text = text.replace('◱link◱', link, 1)
    return text

def mirender_card(
        self, qfmt: str, afmt: str, fields: Dict[str, str], card_ord: int
    ) -> Tuple[TemplateReplacementList, TemplateReplacementList]:
        afmt = getEditableFields(afmt)
        qfmt = getEditableFields(qfmt)
        out = self._run_command(
            pb.BackendInput(
                render_card=pb.RenderCardIn(
                    question_template=qfmt,
                    answer_template=afmt,
                    fields=fields,
                    card_ordinal=card_ord,
                )
            )
        ).render_card

        qnodes = proto_replacement_list_to_native(out.question_nodes)  # type: ignore
        anodes = proto_replacement_list_to_native(out.answer_nodes)  # type: ignore

        return (qnodes, anodes)

anki.rsbackend.RustBackend.render_card = mirender_card

Reviewer._linkHandler = wrap(Reviewer._linkHandler, blurMIAEditor)
Reviewer._showQuestion = wrap(Reviewer._showQuestion, blurMIAEditor)
Reviewer._showAnswer = wrap(Reviewer._showAnswer, unblurMIAEditor)
Reviewer._initWeb = wrap(Reviewer._initWeb, addEventsToFields)
ogRevLinkHandler = Reviewer._linkHandler
Reviewer._linkHandler =  mylinkhandler



def gt(obj):
    return type(obj).__name__

def announceParent(self, event = False):
    if hasattr(mw, 'miaDictionary'):
        if mw.miaDictionary and mw.miaDictionary.isVisible():
            parent = self.parentWidget().parentWidget().parentWidget()
            pName = gt(parent)
            if gt(parent) not in ['AddCards', 'EditCurrent']:
                parent =  aqt.DialogManager._dialogs["Browser"][1]
                pName = 'Browser'
                if not parent:
                    return
            mw.miaDictionary.dict.setCurrentEditor(parent.editor, 'Edit')

def addClickToTags(self):
    self.tags.clicked.connect(lambda: announceParent(self))

TagEdit.focusInEvent = wrap(TagEdit.focusInEvent, announceParent)



def checkCurrentEditor(self):
    if hasattr(mw, 'miaDictionary'):
        if mw.miaDictionary and mw.miaDictionary.isVisible():
            mw.miaDictionary.dict.checkEditorClose(self.editor)

def addEditActivated(self, event = False):
    if hasattr(mw, 'miaDictionary'):
        if mw.miaDictionary and mw.miaDictionary.isVisible():
            mw.miaDictionary.dict.setCurrentEditor(self.editor, 'Edit')


MIAEditCurrent._saveAndClose = wrap(MIAEditCurrent._saveAndClose, checkCurrentEditor)
MIAEditCurrent.mousePressEvent = addEditActivated

def showAnswerWithoutAudio(self):
        if self.mw.state != "review":
            # showing resetRequired screen; ignore space
            return
        self.state = "answer"
        c = self.card
        a = c.a()
        a = self._mungeQA(a)
        a = runFilter("prepareQA", a, c, "reviewAnswer")
        # render and update bottom
        self.web.eval("_showAnswer(%s);" % json.dumps(a))
        self._showEaseButtons()

def showQuestionWithoutAudio(self):
        self._reps += 1
        self.state = "question"
        self.typedAnswer = None
        c = self.card
        # grab the question and play audio
        if c.isEmpty():
            q = _(
                """\
The front of this card is empty. Please run Tools>Empty Cards."""
            )
        else:
            q = c.q()
        # render & update bottom
        q = self._mungeQA(q)
        q = runFilter("prepareQA", q, c, "reviewQuestion")

        bodyclass = bodyClass(self.mw.col, c)

        self.web.eval("_showQuestion(%s,'%s');" % (json.dumps(q), bodyclass))
        self._drawFlag()
        self._drawMark()
        self._showAnswerButton()
        # if we have a type answer field, focus main web
        if self.typeCorrect:
            self.mw.web.setFocus()


aqt.editcurrent.EditCurrent = MIAEditCurrent

mw.reviewer.showAnswerWithoutAudio = showAnswerWithoutAudio 
mw.reviewer.showQuestionWithoutAudio = showQuestionWithoutAudio 

def macFixBridgeCmd(self, cmd):
    try:
        ogAnkiWebviewBridge(self, cmd)
    except:
        return


if not isWin:
    ogAnkiWebviewBridge = aqt.webview.AnkiWebView._onBridgeCmd
    aqt.webview.AnkiWebView._onBridgeCmd = macFixBridgeCmd

def miaBridgeCmd(self, cmd):
        if not self.note or not runHook:
            # shutdown
            return
        # focus lost or key/button pressed?
        if cmd.startswith("blur") or cmd.startswith("key"):
            (type, ord, nid, txt) = cmd.split(":", 3)
            ord = int(ord)
            try:
                nid = int(nid)
            except ValueError:
                nid = 0
            if nid != self.note.id:
                print("ignored late blur")
                return
            txt = urllib.parse.unquote(txt)
            txt = unicodedata.normalize("NFC", txt)
            txt = self.mungeHTML(txt)
            # misbehaving apps may include a null byte in the text
            txt = txt.replace("\x00", "")
            # reverse the url quoting we added to get images to display
            txt = self.mw.col.media.escapeImages(txt, unescape=True)
            self.note.fields[ord] = txt
            # refreshEditor(self)
            # self.web.eval('pycmd("MIAEditor◲" + currentFieldOrdinal() + "◲" + currentField.innerHTML)')
            self.saveTags()

            if type == "blur":
                self.currentField = None
                # run any filters
                if runFilter(
                    "editFocusLost", False, self.note, ord):
                    # something updated the note; update it after a subsequent focus
                    # event has had time to fire
                    self.mw.progress.timer(100, self.loadNoteKeepingFocus, False)
                else:
                    self.checkValid()
            else:
                runHook("editTimer", self.note)
                self.checkValid()
            refreshEditor(self)
        # focused into field?
        elif cmd.startswith("focus"):
            (type, num) = cmd.split(":", 1)
            self.currentField = int(num)
            runHook("editFocusGained", self.note, self.currentField)
        elif cmd in self._links:
            self._links[cmd](self)
        else:
            print("uncaught cmd", cmd)   
        
        

def isOtherMIACMD(cmd):
    return cmd.startswith('textToJReading') or cmd.startswith('individualJExport') or cmd.startswith('textToCReading')



def handleBrowserUpdate(self, cmd):
    (type, ord, nid, txt) = cmd.split(":", 3)
    ord = int(ord)
    try:
        nid = int(nid)
    except ValueError:
        nid = 0
    if nid != self.note.id:
        print("ignored late blur")
        return
    txt = unicodedata.normalize("NFC", txt)
    txt = self.mungeHTML(txt)
    # misbehaving apps may include a null byte in the text
    txt = txt.replace("\x00", "")
    # reverse the url quoting we added to get images to display
    txt = self.mw.col.media.escapeImages(txt, unescape=True)
    self.note.fields[ord] = txt
    if not self.addMode:
        self.note.flush()
        self.mw.requireReset()
    if type == "blur":
        self.currentField = None
        # run any filters
        if gui_hooks.editor_did_unfocus_field(False, self.note, ord):
            # something updated the note; update it after a subsequent focus
            # event has had time to fire
            self.mw.progress.timer(100, self.loadNoteKeepingFocus, False)
        else:
            self.checkValid()
    else:
        gui_hooks.editor_did_fire_typing_timer(self.note)
        self.checkValid()

    
def refreshEditor(editor):
    editor.note.flush()
    editor.mw.col.save()
    editor.mw.reviewer.card.load()
    if editor.mw.reviewer.state == 'answer':
        editor.mw.reviewer.showAnswerWithoutAudio(editor.mw.reviewer)
    elif editor.mw.reviewer.state == 'question':
        editor.mw.reviewer.showQuestionWithoutAudio(editor.mw.reviewer)
    browser = aqt.DialogManager._dialogs["Browser"][1]
    if browser:
        browser.model.reset()
  

def reloadEditor(editor, nid):
    if nid == editor.note.id:
        editor.setNote(mw.col.getNote(nid))


def bridgeReroute(self, cmd):
    className = type(self.parentWindow).__name__
    if className == 'MIAEditCurrent' and not isOtherMIACMD(cmd):
        if cmd == "bodyClick":
            self.parentWindow.unBlur()
            if hasattr(mw, 'miaDictionary'):
                if mw.miaDictionary and mw.miaDictionary.isVisible() and self.note:
                    mw.miaDictionary.dict.setCurrentEditor(self, 'Edit')
            return
        elif cmd.startswith("focus"):
            self.parentWindow.unBlur()
            if hasattr(mw, 'miaDictionary'):
                if mw.miaDictionary and mw.miaDictionary.isVisible() and self.note:
                    mw.miaDictionary.dict.setCurrentEditor(self, 'Edit')
        miaBridgeCmd(self, cmd)
    else:
        miaEditor = aqt.DialogManager._dialogs["EditCurrent"][1]
        if miaEditor and miaEditor.editor and className == 'Browser' and cmd.startswith("blur") or cmd.startswith("key"):
            handleBrowserUpdate(self, cmd)
            try:
                reloadEditor(miaEditor.editor, self.note.id)
            except:
                return
        else: 
            ogReroute(self, cmd)

ogReroute = aqt.editor.Editor.onBridgeCmd 
aqt.editor.Editor.onBridgeCmd = bridgeReroute

def refreshEditorCard(self):
    miaEditor = aqt.DialogManager._dialogs["EditCurrent"][1]
    if miaEditor:
        try:
            c = self.card
            if c:
                n = c.note()
                miaEditor.editor.setNote(n)
            else:
                closeEditor()
        except:
            return

aqt.reviewer.Reviewer.nextCard = wrap(aqt.reviewer.Reviewer.nextCard, refreshEditorCard)

def changeEditorDestination():
    aqt.dialogs._dialogs['EditCurrent'] = [MIAEditCurrent, None]


changeEditorDestination()


from aqt.reviewer import Reviewer

bodyClick = '''document.addEventListener("click", function (ev) {
        console.log("BODY")
        pycmd("bodyClick")
    }, false);'''

def addBodyClick(self):
    self.web.eval(bodyClick)


aqt.editor.Editor.setupWeb = wrap(aqt.editor.Editor.setupWeb, addBodyClick)
Reviewer.show = wrap(Reviewer.show, addBodyClick)