const STATUS_DISCONNECTED = 0;
const STATUS_AVAILABLE = 1;
const STATUS_CONNECTED = 2;
const STATUS_PENDING = 3;
const STATUS_FAILED = 4;

const connection_info_grid = document.querySelector(".connection_info_grid")



// HELPER FUNCTIONS

function update_status_span(span, status){
    span.innerHTML = "";
    let icon = document.createElement("i");
    span.appendChild(icon);
    switch(status){
        case STATUS_DISCONNECTED:
            icon.className = "far fa-times-circle";
            span.innerHTML += "Offline";
            break;
        case STATUS_AVAILABLE:
            icon.className = "fas fa-signal"
            span.innerHTML += "Online"
            break;
        case STATUS_CONNECTED:
            icon.className = "far fa-check-circle"
            span.innerHTML += "Connected"
            break;
        case STATUS_PENDING:
            icon.className = "fas fa-spinner" 
            span.innerHTML += "Connecting.."
            break;
        case STATUS_FAILED:
            icon.className = "fas fa-times";
            span.innerHTML += "Connection Failed";
            break;
    }
}




// CLASSES

const add_window = new (class{
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
            this.name_input.value)()
        await new_connection(uuid, conn_selection)
        overlay_off()
    }
})()



const delete_window = new (class {
    constructor(){
        this.window = document.getElementById("delete_window")
        this.connection_name = document.getElementById("del_window_name")
        this.delete_btn = document.getElementById("delete_btn")
        document.getElementById("cancel_btn").onclick = overlay_off
    }

    display(uuid, name){
        overlay_on()
        this.window.style.display = "grid"
        this.connection_name.innerHTML = name
        this.delete_btn.onclick = function(){
            connections[uuid].remove_row(conn_selection)
            delete connections[uuid]
            overlay_off();
            connection_info_grid.style.display = "none"
        }
    }
})()




const info_display = new (class {
    constructor(){
        this.name_field = document.getElementById("name_field")
        this.status_span = document.querySelector("#status_field span")
        this.uuid_field = document.getElementById("uuid")
        this.hostname_field = document.getElementById("hostname")
        this.port_field = document.getElementById("port")
        this.auto_connect_field = document.getElementById("auto_connect")
        this.directories_list = document.querySelector("#directories_field .list")
        this.syncs_list = document.querySelector("#syncs_field .list")
        this.active=""
    }

    async display(uuid){
        if (this.active === uuid) return
        if (this.active !== "" && connections[this.active] !== undefined) connections[this.active].set_active(false)
        connections[uuid].set_active(true)
        this.active=uuid

        connection_info_grid.style.display = "grid"
        let info = await eel.get_uuid_info(uuid)()
        let status = await eel.get_uuid_status(uuid)()

        this.name_field.innerHTML = info["name"]
        update_status_span(this.status_span, status)
        
        this.uuid_field.innerHTML = uuid
        this.hostname_field.innerHTML = info["hostname"]
        this.port_field.innerHTML = info["port"]
        this.auto_connect_field.innerHTML = info["auto_connect"] // set str in webGUI.py

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
})()




class Connection{
    constructor(uuid){
        this.uuid = uuid
        this.active = false

        this.row = document.createElement("div")
        this.row.id = uuid
        this.row.className = "tb_row"
        this.row.addEventListener("click", ()=> info_display.display(this.uuid))

        this.content = document.createElement("div")
        this.content.className = "tb_content"

        this.name_col = document.createElement("span")
        this.content.appendChild(this.name_col)

        this.status_col = document.createElement("span")
        this.status_col.className = "tb_status"
        this.content.appendChild(this.status_col)

        this.nt_btn = document.createElement("button") // nt_btn = network button : button for connecting/disconnecting
        this.nt_btn.addEventListener("click", async (event)=>{
            event.stopPropagation()
            await info_display.display(this.uuid)
            if (this.status === STATUS_DISCONNECTED){
                this.update_status_span(STATUS_PENDING)
                await eel.connect(this.uuid)
                // if (!await eel.connect(this.uuid)()) this.update_status_span(STATUS_FAILED)
            }else if (this.status === STATUS_CONNECTED){
                await eel.disconnect(this.uuid)()
            }
        })
        this.content.appendChild(this.nt_btn)

        this.delete_btn = document.createElement("button")
        this.delete_btn.className = "far fa-trash-alt delete_btn tb_btn"
        this.delete_btn.title = "Delete"
        this.content.appendChild(this.delete_btn)
        this.delete_btn.onclick = ()=> delete_window.display(this.uuid)

        this.row.appendChild(this.content)
        this.status = STATUS_DISCONNECTED
    }

    add_row(selection){
        selection.table.appendChild(this.row)
    }
    
    remove_row(selection){
        selection.table.removeChild(this.row)
    }

    set_active(active){
        if (active) this.row.classList.add('active')
        else this.row.classList.remove('active')
    }

    async update_name(){
        this.name_col.innerHTML = await eel.get_uuid_name(this.uuid)()
    }

    async update_status(status){
        this.status = status
        this.update_status_span(status)
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

    update_status_span(status){
        update_status_span(this.status_col, status)
        if (this.uuid === info_display.active) update_status_span(info_display.status_span, status)
    }
}
async function new_connection(uuid){
    connections[uuid] = new Connection(uuid)
    await connections[uuid].update_name()
    await connections[uuid].update_status(await eel.get_uuid_status(uuid)())
    connections[uuid].add_row(conn_selection)
}
const connections = {};




class Selection{
    constructor(id){
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
}
const conn_selection = new Selection("connections_selection");
const req_selection = new Selection("requests_selection");





// MAIN
 
(async function(){
    "use strict";
    const uuids = await eel.get_uuids()();

    for (const uuid of uuids) await new_connection(uuid)

    document.getElementById("new_connection").onclick = ()=> add_window.display()

})();




// EXPOSED FUNTIONS
eel.expose(update_status)
function update_status(uuid, status){
    console.log(status)
    connections[uuid].update_status(status)
}

eel.expose(update_uuid)
function update_uuid(old_uuid, new_uuid){
    if (old_uuid === new_uuid) return // otherwise connection will be deleted 
    console.log(new_uuid)
    connections[new_uuid] = connections[old_uuid]
    connections[new_uuid].uuid = new_uuid
    delete connections[old_uuid]
}


// Note: this python error message means some error happend in an exposed javascript function
// Traceback (most recent call last):
//   File "src\\gevent\\greenlet.py", line 854, in gevent._gevent_cgreenlet.Greenlet.run
//   File "d:\dev\File Syncer GUI\env\lib\site-packages\eel\__init__.py", line 303, in _process_message
//     _call_return_values[call_id] = message['value']
// KeyError: 'value'











