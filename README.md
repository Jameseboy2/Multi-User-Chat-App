# Multi User Chat App

Allows you to chat and play pong with friends

The latest version I created was the lan_chat_pong.py file, but you can see the other files I had made before I came to this final file.
The lan_chat.py file just has the chat feature in the GUI, and the client.py and server.py are a pair I had originally created to see how
networking actually works. To run them, you have to have at least one client.py file running and then another server.py (or two) to connect
to it.

## Instructions for Build and Use

Steps to build and/or run the software:

1. Download and open the .exe file
2. (optional) Download any of the .py files to see how it works
3. (optional) Run the .py files in your code editor
4. (optional) If you want to run two instences on one device:
   - Download lan_chat_pong.py
   - Open two seperate terminals
   - Run 'py lan_chat_pong.py' on each terminal

Instructions for using the software:

1. Choose whether to create or join a room
2. Choose a username
3. If you created a room, choose a room name
4. If you want to join a room via LAN, look for a previously created room, click it, and select "join room"
5. If you want to join a room via WAN, insert the necessary IP address of a previously created room (you will need to have port forwarding enabled)

## Development Environment

To recreate the development environment, you need the following software and/or libraries with the specified versions:

* socket
* tkinter
* json
* time
* threading
* Your choice of code editor that can run python

## Useful Websites to Learn More

I found these websites useful in developing this software:

* socketserver — A framework for network servers ([Link](https://docs.python.org/3.13/library/socketserver.html))
* socket — Low-level networking interface ([Link](https://docs.python.org/3.13/library/socket.html))
* Socket Programming in Python (Guide) ([Link](https://realpython.com/python-sockets/)) <--- This one is increadibly helpful for getting started

## Future Work

The following items I plan to fix, improve, and/or add to this project in the future:

* [ ] Improve WAN service by implementing ngrok to bypass port forwarding issues
* [ ] Improve pong
* [ ] Improve the UI
