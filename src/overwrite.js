
function combineFunctions(action, action2){
    return function(){
        action.apply(null, arguments);
        console.log("setup")
        action2();
    }
}

setTimeout(addImageResizingEvents, 250);
migakuSetFormat = setFormat
setFormat = combineFunctions(migakuSetFormat, addImageResizingEvents)
migakuSetFields = setFields;
setFields  = combineFunctions(migakuSetFields, addImageResizingEvents)