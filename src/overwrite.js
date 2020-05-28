
function combineFunctions(action, action2){
    return function(){
        action.apply(null, arguments);
        console.log("setup")
        action2();
    }
}

setTimeout(addImageResizingEvents, 250);
miaSetFormat = setFormat
setFormat = combineFunctions(miaSetFormat, addImageResizingEvents)
miaSetFields = setFields;
setFields  = combineFunctions(miaSetFields, addImageResizingEvents)