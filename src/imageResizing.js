//Globals

let imageResizeInterval = false;
let maintainAspect = true;
let mouseX = false;
let mouseY = false;


//Functions


function addImageResizingEvents(){
    let element = document.getElementById('fields');
    let images= element.getElementsByTagName('img');
    for (const image of images) {
        image.setAttribute('title', 'Click+Drag:\n(Left⇔Right)\nResize with aspect ratio.\n\t\nCtrl+Click+Drag:\nResize freely.\n\t\nShift+Click:\nRestore original size.');
        addMinHeightData(image);
        image.addEventListener('mousedown', handleClickEvents, true); 
        
    }
}

function addImageResizingEventsToElement(element){
    let images= element.getElementsByTagName('img');
    for (const image of images) {
        image.setAttribute('title', 'Click+Drag:\n(Left⇔Right)\nResize with aspect ratio.\n\t\nCtrl+Click+Drag:\nResize freely.\n\t\nShift+Click:\nRestore original size.');
        image.removeEventListener("click", handleClickEvents);
        addMinHeightData(image);
        image.addEventListener('mousedown', handleClickEvents, true); 
        
    }
}

function ensureMinHeight(){
    let element = document.getElementById('fields');
    let images= element.getElementsByTagName('img');
    for (const image of images) {
        addMinHeightData(image);
    }
}

function addMinHeightData(image){
    let rect = image.getBoundingClientRect();
    let width = rect.width;
    let height = rect.height;
    let aspect = height/width;
    let dataMinHeight = (aspect * 40);
    if(!dataMinHeight) dataMinHeight = 40;
    image.dataset.minHeight = dataMinHeight;
    image.dataset.aspect = aspect
}

function restoreImageSize(image){
    image.style.height = 'auto';
    image.style.width = 'auto';
    addMinHeightData(image)

}

function clearResizeImageInterval(){
    clearInterval(imageResizeInterval)
    imageResizeInterval = false;

}

function dontMaintainAspectInit(image){
    maintainAspect = false;
    resizeImage(image, 'red');

}

function maintainAspectInit(image){
    maintainAspect = true;
    resizeImage(image, 'navy');

}

function executeResizing(image){
    let recordedAspect = image.dataset.aspect;
    console.log(recordedAspect)
    if(isNaN(recordedAspect)){
        ensureMinHeight();
    }
    let rect = image.getBoundingClientRect();
    let width = rect.width;
    let height = rect.height;
    let left = rect.left;
    let top = rect.top;
    let aspect = height/width;
    let newWidth = mouseX - left;
    let newHeight = mouseY - top;
    if(maintainAspect){
        let potentialHeight =  (newWidth * aspect);
        let body = document.body;
        body.scrollTop = body.scrollHeight;
        body.scrollLeft = body.scrollWidth;
        image.style.minWidth = '40px';
        image.style.minHeight = image.dataset.minHeight + 'px';
        image.style.height = potentialHeight +'px';
        image.style.width = newWidth +'px';

    }else{
        image.style.width = newWidth +'px';
        image.style.height=  newHeight +'px';
        image.style.minHeight = '40px';
        image.style.minWidth = '40px';
        
    }
}

function resizeImage(image){
    if(!imageResizeInterval){
        imageResizeInterval = setInterval(function(){
        executeResizing(image);
    }, 100)
    }
    
}

function updateMousePosition(event){
    if(imageResizeInterval){
        mouseX = event.clientX;
        mouseY = event.clientY;
    }
}


function handleClickEvents(ev) {
    let image = ev.target;
    if(ev.ctrlKey){
        dontMaintainAspectInit(image);
    }else if(ev.shiftKey){
        restoreImageSize(image);
        
    }else{
        maintainAspectInit(image);
    }
    if(!inlineEditor){
    	currentField = image.closest(".field");
    }
    ev.preventDefault();
}


//Listeners
document.documentElement.addEventListener('mousemove', updateMousePosition, true); 

document.documentElement.addEventListener('mouseup',function(ev){
    clearResizeImageInterval();
    if(!inlineEditor){
    	clearChangeTimer();
    	saveField("key");
    }   
} , true); 


