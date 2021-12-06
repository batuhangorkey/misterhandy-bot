import socket
import subprocess
import threading

PORT = 20002
BUFFER = 128
APP = "python3 bot.py"
LOG_PATH = "/home/cnblgnserver/Desktop/cloud_project/htdocs/falloutbot_logger.txt"


class RemoteServer:
    active_process = None
    log_file = None

    @classmethod
    def run(cls):
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
                if cls.active_process.poll():
                    print("The application is already running...")
                else:
                    start_process = threading.Thread(target=cls.start)
                    start_process.start()
            elif "stop" in rec:
                cls.stop()
            elif "status" in rec:
                c.send(cls.status().encode())
            c.close()

    @classmethod
    def start(cls):
        bash_command = APP
        cls.log_file = open(LOG_PATH, "w+")
        cls.active_process = subprocess.Popen(bash_command.split(), stdout=cls.log_file, stderr=cls.log_file)

    @classmethod
    def stop(cls):
        if cls.active_process.poll():
            cls.active_process.terminate()
            cls.log_file.close()
            print("The application has been stoped")

    @classmethod
    def status(cls):
        if cls.active_process.poll():
            return "App is working\n"
        else:
            return "App is not working\n"


RemoteServer.run()
