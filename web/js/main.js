
// ####################
//        OVERLAY
// ####################
function overlay_on(){
    document.getElementById("overlay").style.display = ""
}
function overlay_off(){
    console.log("sdjkkkkkkkfnsdkfsdf")
    for (const pop_up of document.getElementsByClassName("pop_up_window"))
        pop_up.style.display="none";
    document.getElementById("overlay").style.display = "none";

}



// ####################
//        UTILS
// ####################
function add_break_to_path(path){
    return path.replaceAll('\\', '\\<wbr>')
}

const sleep = ms => new Promise(res => setTimeout(res, ms));





// ####################
//        NAVBAR
// ####################
class Navbar{
    constructor(){
        location.hash = "#home";
        this.current_page = "#home";
        this.indicator = document.getElementById("indicator")

        this.nav_links = {};
        this.pages = {};
        for (const link of document.querySelectorAll("nav a")){
            let page = link.getAttribute("href")
            this.nav_links[page] = link;
            console.log(page)
            this.pages[page] = document.querySelector(page)
            $( page ).load("/pages/" + page.substring(1) + ".html")
        }

        window.addEventListener("hashchange", ()=>this.load_page())
        window.addEventListener('resize', ()=>{
            this.indicator.style.transition = ""
            this.indicator.style.top = this.nav_links[this.current_page].getBoundingClientRect().top + "px";
            this.indicator.style.transition = "all 0.15s ease 0.15s";
        });
        this.load_page()
    }

    load_page(){
        this.nav_links[this.current_page].classList.remove("active");
        this.pages[this.current_page].classList.remove("active")
        this.current_page = location.hash;
        
        this.indicator.style.top = this.nav_links[this.current_page].getBoundingClientRect().top + "px";
        this.nav_links[this.current_page].classList.add("active");
        this.pages[this.current_page].classList.add("active");
    }
};





// #########################
// CONNECTIONS & DIRECTORIES
// #########################
class Connection{
    constructor(uuid, info, status){
        this.uuid = uuid;
        this.name = info.name;
        this.status = status
        this.directories = info.directories;
        this.hostname = info.hostname;
        this.port = info.port;
        this.syncs = info.syncs;
        this.auto_connect = info.auto_connect;
    }
}


class Directory{
    constructor(path, info, graph){
        this.path = path;
        this.name = info.name;
        this.ign_patterns = info.ignore; 
        this.graph = new Folder(graph.name);
        this.graph.update(graph)
        this.root = this.graph.div
    }

    async update_graph(){
        let graph = await eel.get_dir_graph(this.path)(); 
        this.graph.update(graph)
    }
}


class Folder{
    constructor(name){
        this.name = name;
        this.folders = {};
        this.files = {}

        this.div = document.createElement("div");
        this.div.className = "folder";

        this.collapse_btn = document.createElement("i");
        this.collapse_btn.className = "far fa-folder-open";
        this.collapse_btn.addEventListener("click", ()=>{
            if (this.collapse_btn.classList.contains("fa-folder")) this.expand();
            else this.collapse();
        });

        this.name_div = document.createElement("div");
        this.name_div.innerHTML = name;
        this.name_div.className = "name";

        this.content_div = document.createElement("div");
        this.content_div.className = "content";

        this.div.appendChild(this.collapse_btn);
        this.div.appendChild(this.name_div);
        this.div.appendChild(this.content_div);
    }

    collapse() {
        this.collapse_btn.className = "far fa-folder";
        this.content_div.style.display = "none";
    }

    expand() {
        this.collapse_btn.className = "far fa-folder-open";
        this.content_div.style.display = "grid";
    }


    update(graph){
        this.name = graph.name;
        
        // delete old files
        for (const [file_path, file_div] of Object.entries(this.files)){
            if (!(file_path in graph.files)){
                this.content_div.removeChild(file_div)
                delete this.files[file_path]
            }
        }

        // add new files
        for (const [file_path, name] of Object.entries(graph.files)){
            if (!(file_path in this.files)){
                let file_div = document.createElement("div")
                file_div.innerHTML = name
                file_div.className = "file"
                this.content_div.appendChild(file_div)
                this.files[file_path] = file_div
            }
        }

        // delete old folders
        for (const [folder_path, folder] of Object.entries(this.folders)){
            if (!(folder_path in graph.folders)){
                this.content_div.removeChild(folder.div)
                delete this.folders[folder_path]
            }
        }

        // add new folders 
        for (const [folder_path, folder] of Object.entries(graph.folders)){
            if (!(folder_path in this.folders)){
                this.folders[folder_path] = new Folder(folder.name)
                this.content_div.appendChild(this.folders[folder_path].div)
            }
            this.folders[folder_path].update(graph.folders[folder_path])
        }
    }
}





// ####################
//        MAIN
// ####################

(async function(){
    "use strict";   
    document.getElementById("overlay").onclick = ()=>overlay_off() ;
    overlay_off();

    // first load resources, then navbar & pages! 
    window.data = {};
    window.data.connections = {};
    window.data.directories = {};

    for (const uuid of await eel.get_uuids()()) {
        let info = await eel.get_uuid_info(uuid)();
        let status = await eel.get_uuid_status(uuid)();
        window.data.connections[uuid] = new Connection(uuid, info, status);
    };

    for (const path of await eel.get_directories()()){
        let info = await eel.get_dir_info(path)();
        let graph = await eel.get_dir_graph(path)();
        window.data.directories[path] = new Directory(path, info, graph);
    };


    window.navbar = new Navbar(); 
})();


