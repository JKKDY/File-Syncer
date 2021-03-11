


// "3c8fd4fd-1981-11eb-a7f5-70bc105d2bbd": {
//     "auto_connect": -1,
//     "directories": {
//         "D:\\dev\\File Syncer GUI\\test_folder": "test folder"
//     },
//     "hostname": "Surface",
//     "name": "This PC",
//     "port": 40000,
//     "syncs": {
//         "D:\\dev\\File Syncer GUI\\test_folder1": {
//             "D:\\dev\\File Syncer GUI\\test_folder": {
//                 "auto_sync": 0,
//                 "bidirectional": true,
//                 "local_ignore": [],
//                 "synced_ignore": []
//             }
//         }
//     }
// },



// ##################
//   HELPER FUNCTIONS
// ##################
function update_status_span(span, status){
    span.innerHTML = "";
    let icon = document.createElement("i");
    span.appendChild(icon);
    icon.className = connection_status_icon(status);
    span.innerHTML += connection_status_str(status);
}







// ##################
//      CLASSES
// ##################

class NewConnectionWindow{
    constructor(){
        this.window = document.getElementById("add_window")
        this.hostname_input = document.getElementById("add_hostname")
        this.port_input = document.getElementById("add_port")
        this.name_input = document.getElementById("add_name") 
        document.getElementById("add_connection_btn").onclick = ()=>this.add_connection()
    }

    display(){
        overlay_on();
        this.hostname_input.value = ""
        this.port_input.value = ""
        this.name_input.value = ""
        this.window.style.display="grid";
    }

    async add_connection(){
        let uuid = await eel.add_connection(
            this.hostname_input.value, 
            parseInt(this.port_input.value), 
            this.name_input.value
        )()
        overlay_off()
    }
}



class DeleteConnWindow {
    constructor(){
        this.window = document.getElementById("delete_window")
        this.connection_name = document.getElementById("del_window_name")
        this.delete_btn = document.getElementById("delete_btn")
        document.getElementById("cancel_btn").onclick = overlay_off
    }

    display(uuid, name){
        overlay_on();
        this.window.style.display = "grid";
        this.connection_name.innerHTML = name;
        this.delete_btn.onclick = function(){
            window.connections.info_display.clear();
            window.connections.selection.remove(uuid);
            overlay_off();
        }
    }
}




class ConnectionInfoDisplay{
    constructor(){
        this.grid = document.querySelector(".connection_info_grid")
        this.name_field = document.getElementById("name_field")
        this.status_span = document.querySelector("#status_field span")
        this.uuid_field = document.getElementById("uuid")
        this.hostname_field = document.getElementById("hostname")
        this.port_field = document.getElementById("port")
        this.auto_connect_field = document.getElementById("auto_connect")
        this.directories_list = document.querySelector("#directories_field .list")
        this.syncs_list = document.querySelector("#syncs_field .list")
        this.active=undefined;
    }

    clear(){
        this.active = undefined;
        this.grid.style.display = "none"
    }

    async display(row){
        // set row as active
        if (this.active) {
            if (this.active.uuid === row.uuid) return
            this.active.set_active(false)
        }
        this.active = row
        this.active.set_active(true)

        this.grid.style.display = "grid"
        let info = window.data.connections[row.uuid]
        let status = await eel.get_uuid_status(row.uuid)()

        this.name_field.innerHTML = info["name"]
        update_status_span(this.status_span, status)
        
        this.uuid_field.innerHTML = row.uuid
        this.hostname_field.innerHTML = info["hostname"]
        this.port_field.innerHTML = info["port"]
        if (info["auto_connect"] === true) this.auto_connect_field.innerHTML = "Yes"
        else this.auto_connect_field.innerHTML = "No"

        this.directories_list.innerHTML = ""
        for (const [dir_path, dir_name] of Object.entries(info["directories"])){
            let span = document.createElement("span")
            span.innerHTML = add_break_to_path(dir_name===""? dir_path : dir_path)
            this.directories_list.appendChild(span)
        }

        this.syncs_list.innerHTML = ""
        for (const [local_dir, remote_dirs] of Object.entries(info["syncs"])){
            let sync = document.createElement("div")
            sync.className = "sync"

            let loc_span = document.createElement("span") //loc := local (dir)
            loc_span.className = "local_dir"
            loc_span.innerHTML = add_break_to_path(local_dir)
            sync.appendChild(loc_span)
    
            let sync_icon = document.createElement("i")
            sync_icon.className = "fas fa-sync-alt"
    
            for (const [remote_dir, _] of Object.entries(remote_dirs)){
                let rem_span = document.createElement("span")
                rem_span.className = "remote_dir"
                rem_span.appendChild(sync_icon)
                rem_span.innerHTML += add_break_to_path(remote_dir);
                sync.appendChild(rem_span);
            };
            this.syncs_list.appendChild(sync)
        }
    }
}



class ConnectionRow{
    constructor(uuid){
        this.uuid = uuid;
        this.active = false;
        this.display = window.connections.info_display;

        this.row = document.createElement("div")
        // this.row.id = uuid
        this.row.className = "tb_row"
        this.row.addEventListener("click", ()=> window.connections.info_display.display(this))

        this.content = document.createElement("div")
        this.content.className = "tb_content"

        this.name_col = document.createElement("span")
        this.name_col.innerHTML = window.data.connections[uuid].name

        this.status_col = document.createElement("span")
        this.status_col.className = "tb_status"

        // nt_btn = network button : button for connecting/disconnecting
        this.nt_btn = document.createElement("button") 
        this.nt_btn.addEventListener("click", async (event)=>{
            event.stopPropagation()
            await window.connections.info_display.display(this)
            if (this.status === STATUS_DISCONNECTED){
                this.update_status(STATUS_PENDING)
                await eel.connect(this.uuid)
            }else if (this.status === STATUS_CONNECTED){
                await eel.disconnect(this.uuid)()
            }
        })

        this.delete_btn = document.createElement("button")
        this.delete_btn.className = "far fa-trash-alt delete_btn tb_btn"
        this.delete_btn.title = "Delete"
        this.delete_btn.onclick = ()=> window.connections.delete_conn_window.display(this.uuid)

        this.content.appendChild(this.name_col)
        this.content.appendChild(this.status_col)
        this.content.appendChild(this.delete_btn)
        this.content.appendChild(this.nt_btn)

        this.row.appendChild(this.content)
        this.update_status(window.data.connections[uuid].status)
    }

    update_status(status){
        this.status = status

        //update status in info display if active
        if (this.display.active && this.display.active.uuid === this.uuid){
            update_status_span(window.connections.info_display.status_span, status)
        }

        // update status logo/string
        update_status_span(this.status_col, status)

        // update nt_btn (button for connecting/disconnecting)
        switch(status){
            case STATUS_DISCONNECTED:
                this.nt_btn.className = "fas fa-check nt_btn tb_btn"
                this.nt_btn.title = "Try Connect"
                break;
            case STATUS_AVAILABLE:
                break;
            case STATUS_CONNECTED:
                this.nt_btn.className = "far fa-times-circle nt_btn tb_btn"
                this.nt_btn.title = "Disconnect"
                break;
        } 
    }

    set_active(active){
        if (active) this.row.classList.add('active')
        else this.row.classList.remove('active')
    }
}




class Selection{
    constructor(id){
        this.rows = {}
        this.selection = document.getElementById(id)
        this.table = document.querySelector("#"+id+" .selection_table")
        this.input = document.querySelector("#"+id+" input")
        this.input.onkeyup = ()=>{
            let search_str = this.input.value.toUpperCase();
            let rows = this.table.getElementsByClassName("tb_row");
            
            for (const row of rows){
                let spans = row.getElementsByTagName("span");
                let contains_search = false;
                for (const span of spans){
                    let txtValue = span.innerText || span.textContent;
                    if (txtValue.toUpperCase().indexOf(search_str) > -1){
                        contains_search = true;
                    }
                }
                if (contains_search === false) row.style.display = "none";
                else row.style.display = "" ;
            }
        }
    }

    add(uuid, row){
        this.rows[uuid] = row;
        this.table.appendChild(row.row)
    }

    remove(uuid){
        this.table.removeChild(this.rows[uuid].row)
        delete this.rows[uuid]
    }

    change_uuid(old_uuid, new_uuid){
        this.rows[new_uuid] = this.rows[old_uuid]
        this.rows[new_uuid].uuid = new_uuid
        delete this.rows[old_uuid]
    }
}







// ##################
//      MAIN
// ##################
 
(async function(){
    "use strict";

    window.connections = {};
    window.connections.info_display = new ConnectionInfoDisplay();
    window.connections.selection =  new Selection("connections_selection");
    window.connections.req_selection = new Selection("requests_selection");

    window.connections.new_conn_window = new NewConnectionWindow();
    window.connections.delete_conn_window = new DeleteConnWindow();
    
    for (const [uuid, conn] of Object.entries(window.data.connections)){
        window.connections.selection.add(uuid, new ConnectionRow(uuid))
    }

    document.getElementById("new_connection").onclick = ()=> window.connections.new_conn_window.display()

    window.callbacks.status_change.add((uuid, status)=>{
        window.connections.selection.rows[uuid].update_status(status)
    })
    window.callbacks.uuid_change.add((old_uuid, new_uuid) => {
        window.connections.selection.change_uuid(old_uuid, new_uuid)

        if (window.connections.info_display.active.uuid === new_uuid){
            window.connections.info_display.uuid_field.innerHTML = new_uuid
        }
    })
    window.callbacks.new_connection.add((uuid) => {
        window.connections.selection.add(uuid, new ConnectionRow(uuid))
    })
})();



