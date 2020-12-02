



class ConnectionSelection{
    constructor(){
        this.sync_container = document.getElementById("sync_list_container")
        this.list = document.getElementById("conn_list");
        this.active = undefined;
    }

    add(uuid, conn){
        let div = document.createElement("div");
        div.id = uuid;
        div.onclick = ()=>{
            if (this.active) this.active.classList.remove("active");
            this.active = div;
            this.active.classList.add("active")
            this.sync_container.innerHTML = ""
            this.sync_container.appendChild(window.syncs.sync_selections[uuid].list_div)
        }

        let i = document.createElement("i");
        if (conn.status === STATUS_CONNECTED) i.className = "far fa-check-circle";
        else if (conn.status === STATUS_DISCONNECTED) i.className = "far fa-times-circle";

        let span = document.createElement("span");
        span.innerHTML = conn.name;

        div.appendChild(i);
        div.appendChild(span);
        this.list.appendChild(div);
    }
}



class SyncSelection{
    constructor(conn){
        this.uuid = conn.uuid
        this.active = {};
        this.sync_list = {}
        this.list_div = document.createElement("div")
        this.list_div.className = "sync_list"

        for (const [local_dir, syncs] of Object.entries(conn.syncs)){
            this.add(local_dir, syncs)
        }
    }


    add(local_dir, syncs){
        let local_div = document.createElement("div");
        local_div.className = "local";
        local_div.innerHTML = add_break_to_path(
            window.data.directories[local_dir].name
        );
        this.sync_list[local_dir] = {"div": local_div};

        let remote_dirs = document.createElement("div");
        remote_dirs.className = "remote_dirs";

        let sync_div = document.createElement("div");
        sync_div.className = "sync"
        sync_div.appendChild(local_div)
        sync_div.appendChild(remote_dirs)


        for (const [remote, sync] of Object.entries(syncs)){
            let i = document.createElement("i")
            i.className = "fas fa-sync-alt"

            let remote_div = document.createElement("div");
            remote_div.className = "remote";
            remote_div.onclick = ()=>{
                if (this.active.local) this.active.local.classList.remove("active");
                if (this.active.remote) this.active.remote.classList.remove("active");
                this.active.local = sync_div;
                this.active.remote = remote_div;
                this.active.local.classList.add("active");
                this.active.remote.classList.add("active");

                window.syncs.properties_display.set(this.uuid, local_dir, remote);
            };

            let span = document.createElement("span");
            span.innerHTML = add_break_to_path(remote);

            remote_div.appendChild(i);
            remote_div.appendChild(span);
            remote_dirs.appendChild(remote_div);
            this.sync_list[local_dir][remote] = remote_div;
        }

        this.list_div.appendChild(sync_div)
    }

    remove(uuid){

    }

    update(uuid){

    }

}





class PropetiesDisplay{
    constructor(){
        this.container = document.getElementById("props_container");
        this.active = {};

        this.sync_btn = document.getElementById("sync_btn");
        this.sync_btn.onclick = ()=>{ eel.sync(this.uuid, local, remote) };
        
        this.sync_info = new SyncInfo();
        document.getElementById("info_selector").onclick = (event)=>{
            this.display_container(event.target, this.sync_info);
        }

        this.local_ignore_info = new LocalIgnoreInfo();
        document.getElementById("loc_ign_selector").onclick = (event)=>{
            this.display_container(event.target, this.local_ignore_info);
        }

        this.sync_ignore_info = new SyncIgnoreInfo();
        document.getElementById("sync_ign_selector").onclick = (event)=>{
            this.display_container(event.target, this.sync_ignore_info);
        }

        this.conflicts_info = new ConflictsInfo();
        document.getElementById("conflicts_selector").onclick = (event)=>{
            this.display_container(event.target, this.conflicts_info);
        }
    }

    display_container(selector, container){
        if (this.active.selector) this.active.selector.classList.remove("active");
        if (this.active.container) this.active.container.classList.remove("active");
        this.active.selector = selector;
        this.active.container = container.div;
        this.active.selector.classList.add("active");
        this.active.container.classList.add("active");
    }

    set(uuid, local, remote){
        if (!this.active.selector && !this.active.container) {}
        this.display_container(document.getElementById("info_selector"), this.sync_info)
        this.sync_info.set(uuid, local, remote);
        this.local_ignore_info.set(uuid, local, remote);
        this.sync_ignore_info.set(uuid, local, remote);
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

        this.local_ignores = document.getElementById("local_ign");
        this.synced_ignores = document.getElementById("synced_ign");
    }

    set(uuid, local, remote){
        let sync = window.data.connections[uuid].syncs[local][remote];
        
        this.local_name_span.innerHTML = window.data.directories[local].name;
        this.local_path_span.innerHTML = local;
        this.remote_name_span.innerHTML = window.data.connections[uuid].directories[remote];
        this.remote_path_span.innerHTML = remote;
    }
}


class IgnoreInfo extends Container{
    constructor(id, ign_type){
        super(id);
        this.ign_type = ign_type;
        this.ign_patterns = {};
    }

    set(uuid, local, remote){
        let sync = window.data.connections[uuid].syncs[local][remote];
        this.div.innerHTML = "";
        
        for (const ign_pattern of sync[this.ign_type]){
            let span = document.createElement("span");
            span.innerHTML = ign_pattern;
            this.div.appendChild(span);
        }
    }
}

class LocalIgnoreInfo extends IgnoreInfo{
    constructor(){
        super("loc_ign_container", "local_ignore");
    }
}

class SyncIgnoreInfo extends IgnoreInfo{
    constructor(){
        super("sync_ign_container", "synced_ignore");
    }
}



class ConflictsInfo extends Container{
    constructor(){
        super("conflicts_container");
    }   

    set(uuid, local, remote){

    }
}







(async function(){
    "use strict";

    window.syncs = {};
    window.syncs.conn_selection = new ConnectionSelection();
    window.syncs.list = document.getElementById("sync_list");
    window.syncs.sync_selections = {};
    window.syncs.properties_display = new PropetiesDisplay();

    for (const [uuid, conn] of Object.entries(window.data.connections)){
        window.syncs.conn_selection.add(uuid, conn);
        window.syncs.sync_selections[uuid] = new SyncSelection(conn);
    }

})();