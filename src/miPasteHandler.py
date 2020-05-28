# -*- coding: utf-8 -*-
# 
from bs4 import BeautifulSoup
import warnings
from anki.utils import isWin, namedtmp, stripHTMLMedia, \
    checksum
import base64
from .miutils import miInfo, miAsk
from aqt.qt import *
from aqt import mw
import urllib.request, urllib.parse, urllib.error
import anki
from aqt.utils import shortcut, showInfo, showWarning, getFile, \
    openHelp, tooltip, qtMenuShortcutWorkaround
import re
import json
import html
import requests
from anki.sync import AnkiRequestsClient

pics = ("jpg", "jpeg", "png", "tif", "tiff", "gif", "svg", "webp")
audio =  ("wav", "mp3", "ogg", "flac", "mp4", "swf", "mov", "mpeg", "mkv", "m4a", "3gp", "spx", "oga", "webm")

class PasteHandler():

    removeTags = ["script", "iframe", "object", "style"]

    def onPaste(self):
        self._onPaste(QClipboard.Clipboard)

    def _onPaste(self, mode):
        extended = not (mw.app.queryKeyboardModifiers() & Qt.ShiftModifier)
        if mw.pm.profile.get("pasteInvert", False):
            extended = not extended
        mime = mw.app.clipboard().mimeData(mode=mode)
        html, internal = self._processMime(mime)
        if not html:
            return
        self.doPaste(html, internal, extended)

    def onPaste(self):
        self._onPaste(QClipboard.Clipboard)

    def onMiddleClickPaste(self):
        self._onPaste(QClipboard.Selection)

    def _processMime(self, mime):

        # try various content types in turn
        html, internal = self._processHtml(mime)
        if html:
            return html, internal

        # favour url if it's a local link
        if mime.hasUrls() and mime.urls()[0].toString().startswith("file://"):
            types = (self._processUrls, self._processImage, self._processText)
        else:
            types = (self._processImage, self._processUrls, self._processText)

        for fn in types:
            html = fn(mime)
            if html:
                return html, False
        return "", False

    def doPaste(self, html, internal, extended=False):
        html = self._pastePreFilter(html, internal)
        if extended:
            extended = "true"
        else:
            extended = "false"

        # miInfo(html)
        # return   
        mw.reviewer.web.eval("miPasteHTML(%s, %s, %s);" % (
            json.dumps(html), json.dumps(internal), extended))

    def _pastePreFilter(self, html, internal):
        with warnings.catch_warnings() as w:
            warnings.simplefilter('ignore', UserWarning)
            doc = BeautifulSoup(html, "html.parser")

        if not internal:
            for tag in self.removeTags:
                for node in doc(tag):
                    node.decompose()

            # convert p tags to divs
            for node in doc("p"):
                node.name = "div"

        for tag in doc("img"):
            try:
                src = tag['src']
            except KeyError:
                # for some bizarre reason, mnemosyne removes src elements
                # from missing media
                continue

            # in internal pastes, rewrite mediasrv references to relative
            if internal:
                m = re.match(r"http://127.0.0.1:\d+/(.*)$", src)
                if m:
                    tag['src'] = m.group(1)
            else:
                # in external pastes, download remote media
                if self.isURL(src):
                    fname = self._retrieveURL(src)
                    if fname:
                        tag['src'] = fname
                elif src.startswith("data:image/"):
                    # and convert inlined data
                    tag['src'] = self.inlinedImageToFilename(src)

        html = str(doc)
        return html

    def _retrieveURL(self, url):
        "Download file into media folder and return local filename or None."
        # urllib doesn't understand percent-escaped utf8, but requires things like
        # '#' to be escaped.
        url = urllib.parse.unquote(url)
        if url.lower().startswith("file://"):
            url = url.replace("%", "%25")
            url = url.replace("#", "%23")
            local = True
        else:
            local = False
        # fetch it into a temporary folder
        mw.progress.start(
            immediate=not local, parent=mw)
        ct = None
        try:
            if local:
                req = urllib.request.Request(url, None, {
                    'User-Agent': 'Mozilla/5.0 (compatible; Anki)'})
                filecontents = urllib.request.urlopen(req).read()
            else:
                reqs = AnkiRequestsClient()
                reqs.timeout = 30
                r = reqs.get(url)
                if r.status_code != 200:
                    showWarning(_("Unexpected response code: %s") % r.status_code)
                    return
                filecontents = r.content
                ct = r.headers.get("content-type")
        except urllib.error.URLError as e:
            showWarning(_("An error occurred while opening %s") % e)
            return
        except requests.exceptions.RequestException as e:
            showWarning(_("An error occurred while opening %s") % e)
            return
        finally:
            mw.progress.finish()
        # strip off any query string
        url = re.sub(r"\?.*?$", "", url)
        path = urllib.parse.unquote(url)
        return mw.col.media.writeData(path, filecontents, typeHint=ct)

    def inlinedImageToFilename(self, txt):
        prefix = "data:image/"
        suffix = ";base64,"
        for ext in ("jpg", "jpeg", "png", "gif"):
            fullPrefix = prefix + ext + suffix
            if txt.startswith(fullPrefix):
                b64data = txt[len(fullPrefix):].strip()
                data = base64.b64decode(b64data, validate=True)
                if ext == "jpeg":
                    ext = "jpg"
                return self._addPastedImage(data, "."+ext)

    def _addPastedImage(self, data, ext):
        # hash and write
        csum = checksum(data)
        fname = "{}-{}{}".format("paste", csum, ext)
        return self._addMediaFromData(fname, data)


    def _addMediaFromData(self, fname, data):
        return mw.col.media.writeData(fname, data)

    def _processHtml(self, mime):
        if not mime.hasHtml():
            return None, False
        html = mime.html()

        # no filtering required for internal pastes
        if html.startswith("<!--anki-->"):
            return html[11:], True

        return html, False

    def _processImage(self, mime):
        if not mime.hasImage():
            return
        im = QImage(mime.imageData())
        uname = namedtmp("paste")
        if mw.pm.profile.get("pastePNG", False):
            ext = ".png"
            im.save(uname+ext, None, 50)
        else:
            ext = ".jpg"
            im.save(uname+ext, None, 80)

        # invalid image?
        path = uname+ext
        if not os.path.exists(path):
            return

        data = open(path, "rb").read()
        fname = self._addPastedImage(data, ext)
        if fname:
            return self.fnameToLink(fname)

    def fnameToLink(self, fname):
        ext = fname.split(".")[-1].lower()
        if ext in pics:
            name = urllib.parse.quote(fname.encode("utf8"))
            return '<img src="%s">' % name
        else:
            anki.sound.clearAudioQueue()
            anki.sound.play(fname)
            return '[sound:%s]' % fname


    def _processUrls(self, mime):
        if not mime.hasUrls():
            return

        url = mime.urls()[0].toString()
        # chrome likes to give us the URL twice with a \n
        url = url.splitlines()[0]
        return self.urlToLink(url)


    def urlToLink(self, url):
        fname = self.urlToFile(url)
        if not fname:
            return None
        return self.fnameToLink(fname)

    def urlToFile(self, url):
        l = url.lower()
        for suffix in pics+audio:
            if l.endswith("." + suffix):
                return self._retrieveURL(url)
        # not a supported type
        return

    def _processText(self, mime):
        if not mime.hasText():
            return

        txt = mime.text()

        # inlined data in base64?
        if txt.startswith("data:image/"):
            return self.inlinedImageToLink(txt)

        # if the user is pasting an image or sound link, convert it to local
        if self.isURL(txt):
            url = txt.split("\r\n")[0]
            link = self.urlToLink(url)
            if link:
                return link

            # not media; add it as a normal link if pasting with shift
            link = '<a href="{}">{}</a>'.format(
                url, html.escape(txt)
            )
            return link

        # normal text; convert it to HTML
        txt = html.escape(txt)
        txt = txt.replace("\n", "<br>")\
            .replace("\t", " "*4)

        # if there's more than one consecutive space,
        # use non-breaking spaces for the second one on
        def repl(match):
            return " " + match.group(1).replace(" ", "&nbsp;")
        txt = re.sub(" ( +)", repl, txt)

        return txt

    def inlinedImageToLink(self, src):
        fname = self.inlinedImageToFilename(src)
        if fname:
            return self.fnameToLink(fname)

        return ""

    def inlinedImageToFilename(self, txt):
        prefix = "data:image/"
        suffix = ";base64,"
        for ext in ("jpg", "jpeg", "png", "gif"):
            fullPrefix = prefix + ext + suffix
            if txt.startswith(fullPrefix):
                b64data = txt[len(fullPrefix):].strip()
                data = base64.b64decode(b64data, validate=True)
                if ext == "jpeg":
                    ext = "jpg"
                return self._addPastedImage(data, "."+ext)

        return ""

    def isURL(self, s):
        s = s.lower()
        return (s.startswith("http://")
            or s.startswith("https://")
            or s.startswith("ftp://")
            or s.startswith("file://"))