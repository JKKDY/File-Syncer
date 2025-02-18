# File Syncer

A program for syncing files and folders peer to peer between devies. Features a headless backend and a web based front end. 

# Features

- Peer-To-Peer syncing: Every device acts as a server and client.
- File Tracking using file system metadata and constant-time file hashes. Directory are represented as tree graphs.
- Directory Delta detection are based on graph merging.
- Conflict detection between directory graphs
- Fast UI with low overhead based on single page web applications and [eel](https://github.com/python-eel/Eel)
- Comprehensive logging of file tracking, syncing and network traffic


# Example images
An example image of the syncing page. The left side holds all the known devices, the top right side all the configured syncs and bottom right side contains information about the sync (e.g. which folders are being synced, are there conflicts to resolve etc)
![image](https://github.com/user-attachments/assets/6ed32478-9eac-497d-b3b7-782cd6ac4ec2)

<br>
Example image showcasing the directory overview. This is intended to showcase information about each file, which ones are being tracked, which ones are ignored, if the file has been modified etc 
![image](https://github.com/user-attachments/assets/1898d6e8-572e-4871-824d-d224d5bc1c55)


# History, Current State, Missing Features
This project was a product of Covid/Lockdown induced boredom and was written long before I started my CS degree. Hence in its current state it is missing a number critical features especially in regards to security:
- No authentication mechanism
- No encryption 
- Directory graphs are sent as pickle objects. An attacker could use this to inject code into the unpickeling process

For this reason this program and in particular the backend shouldnt be used for actually sending any data. The UI was also added as an after thought and was naively written in pure HTML/CSS/Javascript. Hence it is not particularly usable (UX is hard) and also doesnt look very nice. For this reason too it is  missing access to many features the backend provides

Also other QoL and performance features are missing:
- Large folders can (and will) cause signifcant performance overhead since the program cannot break larger folders into multiple smaller onse
- no incremental sync of files: large files will be sent as whole instead of just sending the part that was modified
- no real time sync: syncs are only performed periodically, not when file changes occur
- no automatic detection of other devices (zero-configuration networking)
- UI fetches font-awesome icons, so internet connection is required to display icons
