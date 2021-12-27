


class AddDirectoryWindow{
    constructor(){
        this.window = document.getElementById("add_directory_window")
        this.dir_select_btn = document.getElementById("dir_select_btn")
        this.dir_input = document.getElementById("add_dir_path")
        this.name_input = document.getElementById("add_dir_name")
        this.dir_select_btn.onclick = async () => {
            console.log("jsdfkjsdfn")
            this.dir_input.value = await eel.ask_dir_path()()
            console.log(this.dir_input.value)
        }
        document.getElementById("add_directory_btn").onclick = ()=>{
            let path = this.dir_input.value
            let name = this.name_input.value
            eel.add_directory(path, name, [])
            overlay_off()
        }
    }

    display(){
        overlay_on();
        this.window.style.display="grid";
        this.dir_input.value = ""
        this.name_input.value = ""
    }
}

class DirectorySelection{
    constructor(){
        this.list = document.getElementById("dir_list")
        this.dir_divs = {}
        this.active = ""
    }

    add_dir(dir_path){
        let div = document.createElement("div")
        let span = document.createElement("span")
        
        span.innerHTML = window.data.directories[dir_path].name
        let edit_btn = document.createElement("button")
        let icon = document.createElement("i")
        icon.className = "far fa-edit"

        edit_btn.appendChild(icon)
        div.appendChild(span)
        div.appendChild(edit_btn)
        this.list.appendChild(div)
        this.dir_divs[dir_path] = div

        div.addEventListener("click", ()=>{
            if (this.active === dir_path) return
            if (this.active !== "" &&  this.dir_divs[this.active] !== undefined) this.dir_divs[this.active].classList.remove("active")
            this.active = dir_path
            div.className = "active"
            window.directories.info_display.display(dir_path)
        })

        edit_btn.addEventListener("click", ()=>{

        })
    }
}




class DirectoryInfo{
    constructor(){
        this.path_span = document.querySelector("#path span")
        this.dir_view = document.getElementById("directory_view")

        this.name = document.getElementById("name")
        this.ign_patterns = document.getElementById("ignore_patterns")
    }

    display(dir_path){
        let dir = window.data.directories[dir_path]
        this.path_span.innerHTML = dir_path
        this.name.innerHTML = dir.name

        this.ign_patterns.innerHTML = ""
        for (const pattern of dir.ign_patterns){
            let span = document.createElement("span")
            span.innerHTML = pattern
            this.ign_patterns.appendChild(span) 
        }

        this.dir_view.innerHTML = ""
        this.dir_view.appendChild(dir.root)
    }
};






// MAIN

(async function(){
    "use strict";
    window.directories = {};
    window.directories.info_display = new DirectoryInfo();
    window.directories.selection = new DirectorySelection();
    window.add_dir_window = new AddDirectoryWindow();

    document.getElementById("new_directory").onclick = ()=>window.add_dir_window.display();
   
    for (const [dir_path, dir] of Object.entries(window.data.directories)){
        window.directories.selection.add_dir(dir_path)
    }

    window.callbacks.directory_graph_update.add((directory)=>{
        if (window.directories.selection.active === directory){
            window.directories.info_display.display(directory)
        }
    })

    window.callbacks.new_directory.add((dir_path)=>{
        window.directories.selection.add_dir(dir_path)
    })
})();