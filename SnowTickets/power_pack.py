import os
import threading
import time

# import pprint
import requests
import urllib3
import yaml
from aos.client import AosClient
from signal import signal, SIGINT

class PowerPackBase:
    def __init__(self, worker_callback, checker_callback, setup_file="setup.yaml"):
        self.setup = {}
        self.setup_file = setup_file
        self.aos_client = None
        self.exit = threading.Event()
        self.go = threading.Event()
        self._worker = threading.Thread
        self._pause_checker = threading.Thread
        self._worker_callback = worker_callback
        self._checker_callback = checker_callback
        self.exit.clear()
        self.go.set()
        self.load_setup()
        self.get_apstra_client()
        signal(SIGINT, self.break_handler)

    # This will be the main loop that will be run.
    def worker_loop(self):
        while not self.exit.is_set():
            self.go.wait()
            self._worker_callback()
            time.sleep(self.setup['wait_time_seconds'])
        print("Exiting Worker Loop.")

    # This will be used to check if we need to pause the main loop
    def pause_check_loop(self):
        while not self.exit.is_set():
            # Check condition and decide if we are going to clear.
            if self._checker_callback():
                print("Pause Set, Pausing")
                self.go.clear()
            else:
                self.go.set()
            time.sleep(self.setup['wait_time_seconds'])
        print("Exiting Pause Check Loop.")

    def start(self, blocking=True):
        self._worker = threading.Thread(target=self.worker_loop)
        self._pause_checker = threading.Thread(target=self.pause_check_loop)
        self._worker.start()
        self._pause_checker.start()
        if blocking:
            self._worker.join()

    # Load the yaml file with the config
    def load_setup(self):
        with open(self.setup_file, "r") as s:
            self.setup = yaml.safe_load(s)

    # Set up the apstra client
    def get_apstra_client(self):
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        aos_ip = os.environ.get('APSTRA_URL').split("https://")[1]
        aos_port = os.environ.get('APSTRA_PORT')
        aos_user = os.environ.get('APSTRA_USER')
        aos_pw = os.environ.get('APSTRA_PASS')
        session = requests.Session()
        session.verify = True
        self.aos_client = AosClient(protocol="https", host=aos_ip, port=int(aos_port), session=session)
        self.aos_client.auth.login(aos_user, aos_pw)

    def pause(self):
        self.go.clear()

    def unpause(self):
        self.go.set()

    def stop(self):
        self.exit.set()

    def break_handler(self, signal_received, frame):
        self.stop()
