# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
import subprocess, requests, json
from pprint import pp

def go():
    base_headers = {
        "accept": "application/json",
        "content-type": "application/json",
    }
    base_url = "http://127.0.0.1:31415/api/v1"
    openapi_def_path = f"{base_url}/openapi.json"
    # my_base_topic = f"wlan-pi/{eth0_mac}"
    global_base_topic = "wlan-pi/all"


    # Get openapi def

    response = requests.get(
                f"{openapi_def_path}",
                params={},
                headers=base_headers,
            )

    print(response.text)

    # response = requests.get(
    #             f"{openapi_def_path}",
    #             params={},
    #             headers=base_headers,
    #         )
    #
    # print(response.text)


if __name__ == '__main__':
    go()