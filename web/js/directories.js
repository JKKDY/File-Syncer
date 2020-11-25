

const dir_list = new (class{
    constructor(){
        this.list = document.getElementById("dir_list")
        this.dir_divs = {}
        this.active = ""
    }

    add_dir(dir_path){
        let div = document.createElement("div")
        let span = document.createElement("span")
        span.innerHTML = directories[dir_path].name
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
            if (this.active !== "") this.dir_divs[this.active ].classList.remove("active")
            this.active = dir_path
            div.className = "active"
            dir_info.display(dir_path)
        })

        edit_btn.addEventListener("click", ()=>{

        })
    }
})()




const dir_info = new (class{
    constructor(){
        this.path_span = document.querySelector("#path span")
        this.dir_view = document.getElementById("directory_view")

        this.name = document.getElementById("name")
        this.ign_patterns = document.getElementById("ignore_patterns")
    }

    display(dir_path){
        let dir = directories[dir_path]
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
})()




class Directory{
    constructor(path, name){
        this.path = path
        this.name = name
        this.graph = {}
        this.root = undefined
        this.collapse_lvl = 0
        this.ign_patterns = []
    }

    async update(){
        this.ign_patterns = await eel.get_ign_patters(this.path)()
        let graph = await eel.get_dir_graph(this.path)() 
        
        if (this.root === undefined){
            this.graph = this.create_folder(graph.name)
            this.root = this.graph.div
            let name_div = this.root.getElementsByClassName("name")[0]
            
            let expand_btn = document.createElement("i")
            expand_btn.classList = "far fa-plus-square"
            expand_btn.id = "collapse_lvl_plus"
            expand_btn.title = "Expand next level"

            let collapse_btn = document.createElement("i")
            collapse_btn.classList = "far fa-minus-square"
            collapse_btn.id = "collapse_lvl_minus"
            collapse_btn.title = "Collapse level"

            name_div.appendChild(expand_btn)
            name_div.appendChild(collapse_btn)
        }

        this.update_folder(graph, this.graph);   
    }

    update_folder(new_folder_graph, old_folder_graph){
        old_folder_graph.name = new_folder_graph.name;
        if (old_folder_graph.files === undefined) old_folder_graph.files = {};
        if (old_folder_graph.folders === undefined) old_folder_graph.folders = {};

        // delete old files
        for (const [file_path, file_div] of Object.entries(old_folder_graph.files)){
            if (!(file_path in new_folder_graph.files)){
                old_folder_graph.content.removeChild(file_div)
                delete old_folder_graph[file_path]
            }
        }

        // add new files
        for (const [file_path, name] of Object.entries(new_folder_graph.files)){
            if (!(file_path in old_folder_graph.files)){
                let file_div = this.create_file(name)
                old_folder_graph.content.appendChild(file_div)
                old_folder_graph.files[file_path] = file_div
            }
        }

        // delete old folders
        for (const [folder_path, folder] of Object.entries(old_folder_graph.folders)){
            if (!(folder_path in new_folder_graph.folders)){
                old_folder_graph.content.removeChild(folder.div)
                delete old_folder_graph.folders[folder_path]
            }
        }

        // add new folders
        for (const [folder_path, subFolder] of Object.entries(new_folder_graph.folders)){
            if (!(folder_path in old_folder_graph.folders)){
                let new_folder = this.create_folder(subFolder.name)
                old_folder_graph.content.appendChild(new_folder.div)
                old_folder_graph.folders[folder_path] = new_folder
            }
            this.update_folder(subFolder, old_folder_graph.folders[folder_path])
        }
    }

    create_file(name){
        let file = document.createElement("div")
        file.innerHTML = name
        file.className = "file"
        return file
    }

    create_folder(folder_name){
        let folder = document.createElement("div")
        folder.className = "folder"

        let collapse_btn = document.createElement("i")
        collapse_btn.className = "far fa-folder-open"

        let collapse = ()=>{
            collapse_btn.className = "far fa-folder"
            content.style.display = "none"
        }

        let expand = ()=>{
            collapse_btn.className = "far fa-folder-open"
            content.style.display = "grid"
        }

        collapse_btn.addEventListener("click", ()=>{
            if (collapse_btn.classList.contains("fa-folder")) expand();
            else collapse();
        })

        let name = document.createElement("div")
        name.innerHTML = folder_name
        name.className = "name"

        let content = document.createElement("div")
        content.className = "content"

        folder.appendChild(collapse_btn)
        folder.appendChild(name)
        folder.appendChild(content)

        return {
            "folders": {},
            "files" : {},
            "div" : folder,
            "content" : content,
            "expand" : expand,
            "collapse" : collapse
        }
        // if (this.folder_contents[depth] === undefined) this.folder_contents[depth]={};
        // this.folder_contents[depth][path] = content
    }
}

async function new_dir(dir_path, name){
    // dir_list.add_dir(dir_name)
    directories[dir_path] = new Directory(dir_path, name)
    await directories[dir_path].update()

    dir_list.add_dir(dir_path)

}

const directories = {};




// MAIN
 
(async function(){
    "use strict";
    const dirs = await eel.get_directories()();

    for (const [path, name] of Object.entries(dirs)) await new_dir(path, name)
})();