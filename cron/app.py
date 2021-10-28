import requests
from time import sleep
sleep(0.05)

CRONJOB_URL = "http://172.23.66.163/api/cronjob"

def run():
    while True:     
        response = requests.get(CRONJOB_URL)
        sleep(10)

if __name__ == "__main__":
    run()