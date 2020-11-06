
(async function(){
    "use strict";   
    // document.getElementById("overlay").onclick = overlay_off() 
    overlay_off();
})();


function overlay_on(){
    document.getElementById("overlay").style.display = ""
}

function overlay_off(){
    for (const pop_up of document.getElementsByClassName("pop_up_window"))
        pop_up.style.display="none";
    document.getElementById("overlay").style.display = "none";
}


function add_break_to_path(path){
    return path.replaceAll('\\', '\\<wbr>')
}


const sleep = ms => new Promise(res => setTimeout(res, ms));
