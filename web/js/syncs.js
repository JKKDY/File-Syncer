


// ######################
//  CONNECTION SELECTION
// ######################
// list of connections, located on the left side
class ConnectionSelection{
    constructor(){
        this.sync_container = document.getElementById("sync_list_container")
        this.list = document.getElementById("conn_list");
        this.active = undefined;
        this.connections = {};
    }

    add(uuid, conn){ // conn: auto_connect, directories,hostname, name, port, status, sycns, uuid
        let connection = {};
        connection.uuid = uuid
        connection.div = document.createElement("div");
        // connection.div.id = uuid;
        connection.div.onclick = ()=>{
            if (this.active) this.active.classList.remove("active");
            this.active = connection.div;
            this.active.classList.add("active");
            this.sync_container.innerHTML = "";
            this.sync_container.appendChild(window.syncs.sync_selections[connection.uuid].list_div);
        }

        connection.i = document.createElement("i");
        connection.change_status = (status)=>{ connection.i.className = connection_status_icon(status) };
        connection.change_status(conn.status);

        connection.span = document.createElement("span");
        connection.span.innerHTML = conn.name;

        connection.div.appendChild(connection.i);
        connection.div.appendChild(connection.span);
        this.list.appendChild(connection.div);
        this.connections[uuid] = connection;
    }

    change_uuid(old_uuid, new_uuid){
        this.connections[old_uuid].uuid = new_uuid
        this.connections[new_uuid] = this.connections[old_uuid]
        delete this.connections[old_uuid]
    }
}




// ######################
//      SYNC SELECTION
// ######################
// displays syncs for selected connection, located on the right side at the top
class SyncSelection{
    constructor(conn){
        this.uuid = conn.uuid
        this.active = {};
        this.sync_list = {}
        this.list_div = document.createElement("div")
        this.list_div.className = "sync_list"

        for (const [local, syncs] of Object.entries(conn.syncs)){
            this.add_local(local)
            for (const [remote, sync_info] of Object.entries(syncs)){ 
                this.add_remote(local, remote)
            }
        }
    }

    add_local(local_dir){
        // left column in selection
        let local_div = document.createElement("div");
        local_div.className = "local";
        local_div.innerHTML = add_break_to_path(window.data.directories[local_dir].name);

        // right column in selection
        let remote_dirs = document.createElement("div");
        remote_dirs.className = "remote_dirs";

        // parent div containg left and right column
        let sync_div = document.createElement("div");
        sync_div.className = "sync"
        sync_div.appendChild(local_div)
        sync_div.appendChild(remote_dirs)
        sync_div.onclick = ()=>{
            if (this.active.local != this.sync_list[local_dir].sync_div) remote_dirs.children[0].on_click()
        }

        this.list_div.appendChild(sync_div)
        this.sync_list[local_dir] = {"local_div": local_div, "sync_div": sync_div, "remote_div":remote_dirs};
    }

    add_remote(local_dir, remote_dir){
        let i = document.createElement("i") // sync icon
        let icon = document.createElement("i")
        icon.className = "fas fa-sync-alt"
        i.appendChild(icon)

        let remote_div = document.createElement("div");
        remote_div.className = "remote";
        remote_div.on_click = ()=>{ // onclick set this sync as active (=visually highlighted)
            if (this.active.local) this.active.local.classList.remove("active");
            if (this.active.remote) this.active.remote.classList.remove("active");
            this.active.local = this.sync_list[local_dir].sync_div;
            this.active.remote = remote_div;
            this.active.local.classList.add("active");
            this.active.remote.classList.add("active");

            window.syncs.properties_display.set(this.uuid, local_dir, remote_dir);
        };
        remote_div.addEventListener("click", (event)=>{
            event.stopPropagation()
            remote_div.on_click()
        })

        remote_div.set_icon_spin = (spin)=>{
            if (spin==true) icon.className = "fas fa-sync-alt fa-spin"
            else icon.className = "fas fa-sync-alt"
        }

        let span = document.createElement("span");
        span.innerHTML = get_remote_name(remote_dir)
        remote_div.appendChild(i);
        remote_div.appendChild(span);
        this.sync_list[local_dir].remote_div.appendChild(remote_div)
        this.sync_list[local_dir][remote_dir] = remote_div;
    }
    
    remove(uuid){ // remove sync

    }

    update(uuid){

    }

    is_active(local_dir, remote_dir){
        return (this.active.local === this.sync_list[local_dir].sync_div && this.active.remote === this.sync_list[local_dir][remote_dir])
    }

}
function get_remote_name(remote){
    try{
        if (window.data.connections[uuid].directories[remote] === undefined) return remote.split("\\")[-1]
        else return window.data.connections[uuid].directories[remote]
    } catch{
        return  remote.split("\\").at(-1)
    }
}




// ######################
//   PROPERTIES DISPLAY
// ######################
// sync properties of selected sync, located at bottom RHS
class PropertiesDisplay{
    constructor(){
        this.container = document.getElementById("props_container");
        this.active = {};
        this.local = undefined;
        this.remote = undefined;
        this.uuid = undefined

        this.sync_btn = document.getElementById("sync_btn");
        this.sync_btn.onclick = ()=>{ 
            if (this.uuid && window.data.connections[this.uuid].status === STATUS_CONNECTED){
                eel.sync(this.uuid, this.local, this.remote) 
            }
        };
        
        this.sync_info = new SyncInfo();
        document.getElementById("info_selector").onclick = (event)=>{
            this.display_container(event.target, this.sync_info);
        }

        this.ignore_info = new IgnoreInfo();
        document.getElementById("ign_selector").onclick = (event)=>{
            this.display_container(event.target, this.ignore_info);
        }

        this.conflicts_info = new ConflictsInfo();
        document.getElementById("conflicts_selector").onclick = (event)=>{
            this.display_container(event.target, this.conflicts_info);
        }
    }

    display_container(selector, container){
        if (this.active.selector) this.active.selector.classList.remove("active");
        if (this.active.container) this.active.container.classList.remove("active");
        if (this.is_set){
            this.active.selector = selector;
            this.active.container = container.div;
            this.active.selector.classList.add("active");
            this.active.container.classList.add("active");
        }
    }

    set(uuid, local, remote){
        this.is_set = true;
        this.remote = remote;
        this.local = local;
        this.uuid = uuid;
        if (!this.active.selector && !this.active.container) {
            this.display_container(document.getElementById("info_selector"), this.sync_info)
        }
        this.sync_info.set(uuid, local, remote);
        this.ignore_info.set(uuid, local, remote);
        this.conflicts_info.set(uuid, local, remote);
    }
} 

class Container{
    constructor(id){this.div = document.getElementById(id)}
    set(uuid, local, remote){}
}
class SyncInfo extends Container{
    constructor(){
        super("info_container");

        this.local_name_span = document.getElementById("loc_name");
        this.local_path_span = document.getElementById("loc_path");
        this.remote_name_span = document.getElementById("rem_name");
        this.remote_path_span = document.getElementById("rem_path");

        this.bi_sync_span = document.getElementById("bi_sync");
        this.auto_sync_span = document.getElementById("auto_sync");

        this.conflict_policy_span = document.getElementById("conflict_policy")
        this.resolve_policy_span = document.getElementById ("resolve_policy")

        this.local_ignores = document.getElementById("local_ign");
        this.synced_ignores = document.getElementById("synced_ign");
    }

    set(uuid, local, remote){
        let sync = window.data.connections[uuid].syncs[local][remote];
        
        this.local_name_span.innerHTML = window.data.directories[local].name;
        this.local_path_span.innerHTML = local;
        this.remote_name_span.innerHTML = get_remote_name(remote);
        this.remote_path_span.innerHTML = remote;
        this.bi_sync_span.innerHTML =  sync.bidirectional

        switch(sync.conflict_policy){
            case 1:
                this.conflict_policy_span.innerHTML  = "Wait for resolve"
                break
            case 2:
                this.conflict_policy_span.innerHTML  = "Record conflict and proceed"
                break
            case 3:
                this.conflict_policy_span.innerHTML  = "Use default resolve policy"
                break
        }

        switch(sync.default_resolve_policy){
            case 1:
                this.resolve_policy_span.innerHTML = "Keep local file/folder"
                break
            case 2:
                this.resolve_policy_span.innerHTML = "Replace local file/folder"
                break
            case 3:
                this.resolve_policy_span.innerHTML = "Keep newest version"
                break
            case 4:
                this.resolve_policy_span.innerHTML = "Create copy of file/folder"
                break
        }

        if (sync.auto_sync === 0) this.auto_sync_span.innerHTML = "No"
        else if (sync.auto_sync === -1) this.auto_sync_span.innerHTML = "Yes"
        else {
            let str = "Yes, every "

            let d = Math.floor(sync.auto_sync/60/60/24)
            let h = Math.floor(sync.auto_sync/60/60) - d*24
            let m = Math.floor(sync.auto_sync/60) - h*60 - d*24*60
            let s = sync.auto_sync - m*60 -h*60*60 - d*60*60*24

            if (d!= 0) str += d + "d "
            if (h!= 0) str += h + "h "
            if (m!= 0) str += m + "m "
            if (s!= 0) str += s + "s "

            this.auto_sync_span.innerHTML = str
        }
    }
}

class IgnoreInfo extends Container{
    constructor(){
        super("ign_container");
        this.ign_patterns = {};
    }

    set(uuid, local, remote){
        let sync = window.data.connections[uuid].syncs[local][remote];
        this.div.innerHTML = "";
        
        // temporary fix
        for (const ign_pattern of sync["local_ignore"]){
            let span = document.createElement("span");
            span.innerHTML = ign_pattern;
            this.div.appendChild(span);
        }

        for (const ign_pattern of sync["synced_ignore"]){
            let span = document.createElement("span");
            span.innerHTML = ign_pattern;
            this.div.appendChild(span);
        }

        if (this.div.innerHTML===""){
            this.div.innerHTML = "None"
        }
    }
}

class ConflictsInfo extends Container{
    constructor(){
        super("conflicts_container");
    }   

    set(uuid, local, remote){
        for (const [k, conflict] of Object.entries(window.data.connections[uuid].conflicts[local][remote])){
            const [path, is_dir]  = k.split(",")
            this.create_conflict(path, is_dir, conflict)
        }
    }

    create_conflict(path, is_dir, conflict){
        let conflict_div = document.createElement("div")
        conflict_div.className = "conflict"

        let icon = document.createElement("i")
        icon.className = "fas fa-chevron-down" + " chevron"
        conflict_div.appendChild(icon)

        let type_icon = document.createElement("i")
        if (is_dir === false) type_icon.className = "far fa-folder type_indicator"
        else type_icon.className = "far fa-file type_indicator"

        if (conflict.resolve_policy !== false){
            type_icon.className += " resolved"
            icon.className  += " resolved"
        }

        let path_span = document.createElement("span")
        path_span.className = "path"
        path_span.appendChild(type_icon)
        path_span.innerHTML += " " + path
        conflict_div.appendChild(path_span)

        console.log(conflict)    
        console.log(conflict.local_modif_time)
        console.log(conflict.remote_modif_time)
        
        function create_pair(key_html, value_html){
            let key = document.createElement("span")
            key.className = "key"
            key.innerHTML = key_html
            conflict_div.appendChild(key)

            let value = document.createElement("span")
            value.className = "value"
            value.innerHTML = value_html
            conflict_div.appendChild(value)
        }

        create_pair("Conflict type:", conflict.conflict_type)
        create_pair("Last local modifaction time:", conflict.local_modif_time)
        create_pair("Last remote modifaction time:", conflict.remote_modif_time)
        create_pair("Resolve policy:", conflict.resolve_policy)

        this.div.appendChild(conflict_div)
    }
}







(async function(){
    "use strict";

    window.syncs = {};
    window.syncs.conn_selection = new ConnectionSelection();
    window.syncs.list = document.getElementById("sync_list");
    window.syncs.sync_selections = {};
    window.syncs.properties_display = new PropertiesDisplay();

    for (const [uuid, conn] of Object.entries(window.data.connections)){
        window.syncs.conn_selection.add(uuid, conn);
        window.syncs.sync_selections[uuid] = new SyncSelection(conn);
    }

    // callbacks
    window.callbacks.status_change.add((uuid, status)=>{
        window.syncs.conn_selection.connections[uuid].change_status(status)
    })

    window.callbacks.uuid_change.add((old_uuid, new_uuid) => {
        window.syncs.conn_selection.change_uuid(old_uuid, new_uuid)

        window.syncs.sync_selections[new_uuid] = window.syncs.sync_selections[old_uuid]
        window.syncs.sync_selections[new_uuid].uuid = new_uuid
        delete window.syncs.sync_selections[old_uuid]  

        let display = window.syncs.properties_display 
        if (display.uuid === old_uuid){
            display.set(new_uuid, display.remote, display.local)
        }
    })

    window.callbacks.new_connection.add((uuid) => {
        window.syncs.conn_selection.add(uuid, window.data.connections[uuid]);
        window.syncs.sync_selections[uuid] = new SyncSelection(window.data.connections[uuid]);
    })

    window.callbacks.new_sync.add((uuid, local, remote, info) => {
        if (window.syncs.sync_selections[uuid].sync_list[local] === undefined) window.syncs.sync_selections[uuid].add_local(local)
        window.syncs.sync_selections[uuid].add_remote(local, remote, info)
    })

    window.callbacks.update_sync_state.add((uuid, local_dir, remote_dir, state) => {
        if (window.syncs.sync_selections[uuid].sync_list[local_dir] != undefined && window.syncs.sync_selections[uuid].sync_list[local_dir][remote_dir] != undefined)
            window.syncs.sync_selections[uuid].sync_list[local_dir][remote_dir].set_icon_spin(state)
    })

    window.callbacks.new_conflict.add((uuid, local, remote, path, is_dir, conflict) => {
        if (window.syncs.sync_selections[uuid].is_active(local, remote)){
            window.syncs.properties_display.conflicts_info.create_conflict(path, is_dir, conflict)
        }
    })

    window.callbacks.delete_conflict.add((uuid, local, remote, path, is_dir) => {

    })
})();

