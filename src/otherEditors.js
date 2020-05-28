//Globals
let inlineEditor = false;

//Functions
function addCSS(){
        let style = document.getElementsByTagName('style')[0];
        style.innerHTML = style.innerHTML + '#fields img{ cursor:pointer; max-height:none; max-width:none; width: auto; height: auto;}#fields table td div{overflow: auto;}}';
    }
    addCSS();

function saveField(type) {
    clearChangeTimer();
    if (!currentField) {
        // no field has been focused yet
        return;
    }
    // type is either 'blur' or 'key'
    // let html = currentField.innerHTML.replace(/title="Click\+Drag:\n\(Left⇔Right\)\nResize with aspect ratio\.\n\t\nCtrl\+Click\+Drag:\nResize freely.\n\t\nShift\+Click:\nRestore original size\./g, '')
    let html = currentField.innerHTML;
    pycmd(
        type +
            ":" +
            currentFieldOrdinal() +
            ":" +
            currentNoteId +
            ":" +
            html
    );
}






//Include imageResizing.js
%s

//Include Overwrites
%s