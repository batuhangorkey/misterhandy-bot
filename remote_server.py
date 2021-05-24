import socket
import subprocess
import threading

PORT = 20002
APP = "python3 bot.py"
BUFFER = 128
active_process = ""


def main():
    global active_process
    s = socket.socket()
    print("Socket successfully created...")

    s.bind(('', PORT))
    print("Socket binded to {}".format(PORT))

    s.listen(5)
    print("Socket is listening...")

    while True:
        c, addr = s.accept()
        print("Got connection from {}".format(addr))
        rec = c.recv(BUFFER).decode()
        print("received {}".format(rec))

        if "start" in rec:
            if active_process == "":
                start_process = threading.Thread(target=start)
                start_process.start()

            else:
                print("The application is already running...")

        elif "stop" in rec:
            stop()
        elif "status" in rec:
            c.send(status().encode())

        c.close()


def start():
    global active_process
    bash_command = APP
    f = open("/home/cnblgnserver/Desktop/cloud_project/htdocs/falloutbot_logger.txt", "w+")
    process = subprocess.Popen(bash_command.split(), stdout=f, stderr=f)
    active_process = process
    output, error = process.communicate()


def stop():
    global active_process
    if isinstance(active_process, subprocess.Popen):
        active_process.terminate()
        print("The application has been stoped")
        active_process = ""


def status():
    global active_process
    if active_process == "":
        return "App is not working\n"
    else:
        return "App is working\n"


main()
