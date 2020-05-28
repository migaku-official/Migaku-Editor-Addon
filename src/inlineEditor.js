//globals

let ALLOW_FIELD_EDITS =%s;
let SHOW_EMPTY_FIELDS = %s;
let typingTimer;                
let doneTypingInterval = 250;  
let contentChangeInterval = false;
let previousValue = false;
let gennedValue = false;
let editorFieldCounter = false;
let inlineEditor = true;
let loadingNewCard = false;

//Include imageResizing.js
%s


//Functions
function addCSS(){
    let style = document.getElementsByTagName('style')[0];
    style.innerHTML = style.innerHTML + '.imageResizeWrapper:hover{cursor:pointer;}.miaEditorInput img{cursor:pointer; max-height:none; max-width:none; width: auto; height: auto;} .emptyEditable{border: 1px solid pink !important; display: inline-block; width: 100px;}';
}

    
function _updateQA(html, fadeTime, onupdate, onshown) { 
    // if a request to update q/a comes in before the previous content
    // has been loaded, wait a while and try again
    loadingNewCard = true;
    if (_updatingQA) {
        setTimeout(function () { _updateQA(html, fadeTime, onupdate, onshown) }, 50);
        return;
    }

    _updatingQA = true;

    onUpdateHook = [onupdate];
    onShownHook = [onshown];

    // fade out current text
    let qa = $("#qa");
    qa.fadeTo(fadeTime, 0, function() {
        // update text
        try {
            qa.html(html);
        } catch(err) {
            qa.text("Invalid HTML on card: "+err);
        }
        _runHook(onUpdateHook);

        // don't allow drags of images, which cause them to be deleted
        $("img").attr("draggable", false);

        // render mathjax
        MathJax.Hub.Queue(["Typeset", MathJax.Hub]);

        // and reveal when processing is done
        MathJax.Hub.Queue(function () {
            qa.fadeTo(fadeTime, 1, function () {
                _runHook(onShownHook);
                _updatingQA = false;
                clearEditorWindows();
                makeEmptyFieldsSelectable();
                loadGeneratedField()
                loadingNewCard = false;
                //pycmd('miacopy' + document.documentElement.innerHTML);
            });
        });
    });
    
}


function loadGeneratedField(){
    if(gennedValue){
        let previouslySelected = document.getElementsByClassName('editableField')[editorFieldCounter];
        mieditField(previouslySelected, previouslySelected.dataset.field);
    }
    gennedValue = false;
}

function clearIntervalWhenLoading(){
        clearInterval(contentChangeInterval);
        previousValue = false;
        return false
    

}

function checkContentChange(el, field){  
    contentChangeInterval = setInterval(function(){
        clearTimeout(typingTimer);
        if(loadingNewCard){
            clearIntervalWhenLoading();
        }else{
            if(el.innerHTML !== previousValue){
                previousValue = el.innerHTML;   
                typingTime = setTimeout(function(){
                    finalizeSelectedFieldEdit(el, field)
                }, doneTypingInterval)
            }
        }
    }
    ,50)
}

function finalizeSelectedFieldEdit(el, field){
    pycmd('finalizeEdit◱' + JSON.stringify([el.innerHTML]) + '◱' + field )
}


function hideElementAndChildren(element){
    element.style.visibility = 'hidden';
    let children = element.childNodes;
    for (let i=0; i< children.length; i++) {
      let child = children[i];
      if (child.nodeType == 1) {
        hideElementAndChildren(child);
      }
    }
}

function mieditField(element, field) {
    if(!ALLOW_FIELD_EDITS ||element.dataset.field == "FrontSide")return;
    setEditorFieldCounter(element);
    let styles = window.getComputedStyle(element);
    let color = styles.getPropertyValue('color');
    let size =  styles.getPropertyValue('font-size');
    let fontFamily = styles.getPropertyValue('font-family');
    let bodyStyles = window.getComputedStyle(document.body);
    let background = bodyStyles.getPropertyValue('background-color');
    let bodyWidth = document.body.offsetWidth;
    let rect = element.getBoundingClientRect();
    let top = rect.top;
    let left = rect.left;
    let width = rect.width;
    let height = rect.height;
    let input = document.createElement("div");
    hideElementAndChildren(element);
    input.style.position = 'absolute';
    input.style.top = (document.documentElement.scrollTop + top) + 'px';
    input.classList.add('miaEditorInput');
    //input.style.border = ('57AAFC')
    input.style.left = left + 'px';
    input.style.color = color;
    if(field == 'Tags')input.style.minWidth = '200px';
    input.style.fontFamily = fontFamily;
    input.style.backgroundColor = background;
    input.style.fontSize = size;
    input.dataset.field = field;
    input.setAttribute('contentEditable', true);
    input.style.zIndex = '10000';
    input.style.width =  'auto';
    // input.style.maxWidth = (bodyWidth -  left) +'px';
    input.style.minWidth = width +'px';
    input.style.minHeight = height + 'px';
    input.style.border = 'none';
    document.body.appendChild(input);
    if(field == 'Tags'){
        input.addEventListener('keydown', function(e) {
        if (e.keyCode === 13) {
                finalizeTagsEdit(input, field);
                e.preventDefault()
            }
        });
    }
    pycmd('getFieldForEdit:' + field);
}

function finalizeTagsEdit(el, field){
    pycmd('finalizeTagsEdit◱' + JSON.stringify([el.innerHTML]) + '◱' + field )
    clearEditorWindows();

}

document.documentElement.addEventListener('mousedown', function(el){
    el = el.target;
    let editWindows = document.getElementsByClassName('miaEditorInput');
    if(editWindows.length == 0)return;
    if(!el.classList.contains('miaEditorInput')){
        while(true){
            el = el.parentElement;
            if(!el)break;
            if(el.classList.contains('miaEditorInput')){
                return
            }
        }
        const editWindow = editWindows[0]
        pycmd('finalizeEdit◱' + JSON.stringify([editWindow.innerHTML]) + '◱' + editWindow.dataset.field )
        gennedValue = false;
        pycmd('miReload');
    }
}, true); 

function clearEditorWindows(){

    let editWindows = document.getElementsByClassName('miaEditorInput');
    if(editWindows.length > 0) {
        for (var i = editWindows.length - 1; i > -1 ; i--) {
            editWindows[i].parentNode.removeChild(editWindows[i]);
        }
        previousValue = false;
        clearInterval(contentChangeInterval);
        
        
        
    }
}

function makeEmptyFieldsSelectable(){
    if(!SHOW_EMPTY_FIELDS)return;
    let fields = document.getElementsByClassName('editableField');
    for(var i = 0; i < fields.length; i++){
        let field = fields[i];
        let fieldWithoutHtml = field.innerHTML.replace(/<((?!img)[^>])+?>/g, '');
        if(fieldWithoutHtml == ''){
           
            field.innerHTML = '<span class="emptyEditable">&nbsp;</span>';
        }
    }
}

function selectElementContents(el) {
    let range = document.createRange();
    range.selectNodeContents(el);
    let sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(range);
}
    
function setFieldValue(value, field){
    let editWindow = document.getElementsByClassName('miaEditorInput')[0];
    previousValue = JSON.parse(value)[0];
    editWindow.innerHTML = previousValue;
    editWindow.focus();
    addImageResizingEventsToElement(editWindow)
    checkContentChange(editWindow, field);

}


function setEditorFieldCounter(el){
   let reviewerFields = document.getElementsByClassName('editableField');
   for (var i = 0; i < reviewerFields.length; i++) {
       if(reviewerFields[i] == el)editorFieldCounter = i;
   }
}

function editGoButton(el, field){
    let text = fetchIndividualEdit(el);
    gennedValue = true;
    pycmd('editGoButton◱' + JSON.stringify([text]) + '◱' + field );
}

function editBunButton(el, field){
    gennedValue = true;
    pycmd('editBunButton◱' + JSON.stringify([el.innerHTML]) + '◱' + field );
}

function cleanGennedText(el, field){
    previousValue = removeBracketsEdit(el.innerHTML);
    el.innerHTML = previousValue;
    el.focus();
    finalizeSelectedFieldEdit(el, el.dataset.field);
}

document.body.addEventListener('keydown', function(e) {
    let editWindow = document.getElementsByClassName('miaEditorInput')[0];
    if(editWindow && document.activeElement == editWindow){
        let field = editWindow.dataset.field;
        if (e.keyCode === 113) {
            editBunButton(editWindow, field);
        }else if(e.keyCode === 114){
            editGoButton(editWindow, field);
        }else if(e.keyCode === 115){
            cleanGennedText(editWindow, field);
        }else if(e.keyCode === 86 && e.ctrlKey && e.shiftKey){
            pycmd('miaPaste');
            e.preventDefault();
        }else if(e.keyCode === 86 && e.ctrlKey){
            pycmd('miaStyledPaste');
            e.preventDefault();
        }
    }
    
}, false)

function cleanUpSpaces(text){
      return text.replace(/ /g, '');
}
function removeBracketsEdit(text) {
  if (text === "") return '';
  let pattern2 = /(\[sound:[^\]]+?\])|(?:\[\d*\])|(?:\[[\w ]+?\])/g;
  if(!/\[[^\[]*?\]/.test(text))return text;

  let pattern = /<[^<]*?>/g;
  let matches = false;
  if (pattern.test(text)){
    matches = text.match(pattern);
    for (x in matches){
        text = text.replace(matches[x], '---NEWLINE___');
    }   
  }
  
  let matches2 = false;
  if (pattern2.test(text)){
    matches2 = text.match(pattern2)
    for (x in matches2){
        text = text.replace(matches2[x], '---SOUNDREF___');
    }   
  }

  text = cleanUpSpaces(text);
  if(matches){
    for (x in matches){
      text = text.replace( '---NEWLINE___', matches[x]);
    } 

  }

  text = text.replace(/\[[^\[]*?\]/g, "");
  if(matches2){
    for (x in matches2){
      text = text.replace( '---SOUNDREF___', matches2[x]);
    } 

  }
  return text;
}


function wrapSelectionEdit(sel) {
    let range, html, wrapper;
    if (sel) {
        let wrapper = document.createElement("p");
        wrapper.classList.add('selection-wrapper')
        sel = window.getSelection();
        if(sel.toString().length < 2) return [sel.anchorNode, sel.anchorOffset, false,false];
        if (sel.getRangeAt && sel.rangeCount) {
            range = sel.getRangeAt(0);
            return [range.startContainer,range.startOffset, range.endContainer, range.endOffset];
        }
    }
}

function fetchIndividualEdit(cur) {
  const sel = window.getSelection();
  let ogHTML = cur.innerHTML;
  let startCont, startOff, endCont, endOff;
  [startCont, startOff,endCont, endOff] = wrapSelectionEdit(sel);
  if(endCont){
    let offset = 0;
    if(startCont.isSameNode(endCont)) offset = 7;
    startCont.textContent = startCont.textContent.substring(0,startOff) + '--IND--' + startCont.textContent.substring(startOff);
    endCont.textContent = endCont.textContent.substring(0,endOff + offset) + '--IND--' + endCont.textContent.substring(endOff + offset);
  }else{
    startCont.textContent = startCont.textContent.substring(0,startOff) + '--IND--' + startCont.textContent.substring(startOff);
  }
  const newHTML = cur.innerHTML;
  cur.innerHTML = ogHTML;  
  return newHTML;
}


function miPasteHTML(html, internal, extendedMode) {
    if(!extendedMode){
        html = html.replace(/<((?!img)[^>])+?>/g, '')
    }
    document.execCommand("inserthtml", false, html);
    let editWindow = document.getElementsByClassName('miaEditorInput')[0];
    let field = editWindow.dataset.field;
    finalizeSelectedFieldEdit(editWindow, field);
    addImageResizingEventsToElement(editWindow);

}

//Calls
addCSS();
