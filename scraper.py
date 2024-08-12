from typing import List

import requests
from bs4 import BeautifulSoup
from influxdb import InfluxDBClient

import schemas


def scrap_downstream(html_down: str) -> List[schemas.ChannelDataDown]:
    soup_down = BeautifulSoup(html_down, "lxml")
    downchannels_data = list()

    tbody = soup_down.find("tbody")
    rows = tbody.find_all("tr")
    for row in rows:
        tds = row.find_all("td")
        receiver_id = tds[0].text
        channel_id = tds[1].text

        lock = tds[2]
        lock_raw = lock.find("script").text
        lock_raw = lock_raw.lstrip('i18n("').rstrip('")')
        if lock_raw == "TAG_UPC_T38":
            lock_raw = "Locked"
        if lock_raw == "TAG_UPC_T39":
            lock_raw = "Unlocked"

        frequency = tds[3].text

        modulation = tds[4]
        modulation_raw = modulation.find("script").text
        modulation_raw = modulation_raw.lstrip('i18n("').rstrip('")')
        if modulation_raw == "TAG_UPC_T37":
            modulation_raw = "N/A"

        rate = tds[5]
        symbol_raw = rate.find("script").text
        symbol_raw = symbol_raw.lstrip('i18n("').rstrip('")')

        snr = tds[6].text

        power = tds[7].text

        downchannels_data.append(
            schemas.ChannelDataDown(
                receiver_id=receiver_id,
                channel_id=channel_id,
                lock_status=lock_raw,
                frequency=frequency,
                modulation=modulation_raw,
                symbol_rate=symbol_raw,
                snr=snr,
                power=power,
            )
        )
    # print(downchannels_data)
    return downchannels_data


def scrap_upstream(html_up: str) -> List[schemas.ChannelDataUp]:
    soup_up = BeautifulSoup(html_up, "lxml")
    upchannels_data = list()

    tbody = soup_up.find("tbody")
    rows = tbody.find_all("tr")
    for row in rows:
        tds = row.find_all("td")
        transmitter_id = tds[0].text
        channel_id = tds[1].text

        lock = tds[2]
        lock_raw = lock.find("script").text
        lock_raw = lock_raw.lstrip('i18n("').rstrip('")')
        if lock_raw == "TAG_UPC_T38":
            lock_raw = "Locked"
        if lock_raw == "TAG_UPC_T39":
            lock_raw = "Unlocked"

        frequency = tds[3].text

        modulation = tds[4]
        modulation_raw = modulation.find("script").text
        modulation_raw = modulation_raw.lstrip('i18n("').rstrip('")')

        symbol_rate = tds[5].text

        channel_type = tds[6]
        channel_type_raw = channel_type.find("script").text
        channel_type_raw = channel_type_raw.lstrip('i18n("').rstrip('")')

        power = tds[7].text

        upchannels_data.append(
            schemas.ChannelDataUp(
                transmitter_id=transmitter_id,
                channel_id=channel_id,
                lock_status=lock_raw,
                frequency=frequency,
                modulation=modulation_raw,
                symbol_rate=symbol_rate,
                channel_type=channel_type_raw,
                power=power,
            )
        )
    # print(upchannels_data)
    return upchannels_data


def check_if_on_loginpage(url_check: str) -> bool:
    loginpage_str_to_compare = '<h2><script>i18n("LOGIN_AREA_LABEL2=")</script></h2>'
    url_check_response = requests.get(url_check, timeout=10)
    loginpage = BeautifulSoup(url_check_response.text, "lxml")
    check_loginpage = loginpage.find("h2")
    if str(check_loginpage) == loginpage_str_to_compare:
        return True
    else:
        return False


def login_into() -> None:
    print("Trying to login...")
    url_login = "http://192.168.42.1/goform/login"
    s = requests.get("http://192.168.42.1/login.asp")
    st = s.text
    stx = BeautifulSoup(st, "lxml")
    csrf = str(stx.find("input"))
    csrf = csrf.lstrip('<input name="CSRFValueL" type="hidden" value=').rstrip('"/>')
    print(f"CSRFValue={csrf}")
    login_payload = {
        "CSRFValue": f"{csrf}",
        "loginUsername": "admin",
        "loginPassword": "admin",
        "logoffUser": "0",
    }
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "Origin": "http://192.168.42.1",
        "Connection": "keep-alive",
        "Referer": "http://192.168.42.1/",
        "Upgrade-Insecure-Requests": "1",
        "DNT": "1",
        "Sec-GPC": "1",
    }
    logged_url = requests.post(url_login, data=login_payload, headers=headers)
    try:
        logged_url.raise_for_status
    except requests.exceptions.RequestException as err:
        print("Whoops! Some error occurred during login", err)

    print(f"Logged in successfully with status: {logged_url.status_code}")


def request_downstream() -> str:
    url_downstream = "http://192.168.42.1/status/connection-downstream.asp"
    print("Requesting data from downstream.asp...")
    if check_if_on_loginpage(url_downstream) is True:
        print("Not logged in")
        login_into()
    try:
        response_down = requests.get(url_downstream, timeout=10)
        response_down.raise_for_status
    except requests.exceptions.ConnectionError as errc:
        print("Connection error:", errc)
    except requests.exceptions.Timeout as errt:
        print("Connection timeout:", errt)
    except requests.exceptions.RequestException as err:
        print("Whooops something else:", err)
    return response_down.text


def request_upstream() -> str:
    url_upstream = "http://192.168.42.1/status/connection-upstream.asp"
    print("Requesting data from upstream.asp...")
    if check_if_on_loginpage(url_upstream) is True:
        print("Not logged in")
        login_into()
    try:
        response_up = requests.get(url_upstream, timeout=10)
        response_up.raise_for_status
    except requests.exceptions.ConnectionError as errc:
        print("Connection error:", errc)
    except requests.exceptions.Timeout as errt:
        print("Connection timeout:", errt)
    except requests.exceptions.RequestException as err:
        print("Whooops something else:", err)
    return response_up.text


def influx_write(
    ups: List[schemas.ChannelDataUp], downs: List[schemas.ChannelDataDown]
):
    points = list()
    for ch in ups:
        points.append(
            dict(
                measurement="channelDataUp",
                tags={
                    "transmitter_id": ch.transmitter_id,
                    "channel_id": ch.channel_id,
                    "lock_status": ch.lock_status,
                    "frequency": ch.frequency,
                    "modulation": ch.modulation,
                    "channel_type": ch.channel_type,
                },
                fields={
                    "symbol_rate": ch.symbol_rate,
                    "power": ch.power,
                },
            )
        )
    for ch in downs:
        points.append(
            dict(
                measurement="channelDataDown",
                tags={
                    "receiver_id": ch.receiver_id,
                    "channel_id": ch.channel_id,
                    "lock_status": ch.lock_status,
                    "frequency": ch.frequency,
                    "modulation": ch.modulation,
                },
                fields={
                    "symbol_rate": ch.symbol_rate,
                    "snr": ch.snr,
                    "power": ch.power,
                },
            )
        )

    client = InfluxDBClient(host="localhost", port=8086)
    client.write_points(points=points, database="electric")
    client.close()


if __name__ == "__main__":
    resp_up = request_upstream()
    up = scrap_upstream(resp_up)
    resp_down = request_downstream()
    down = scrap_downstream(resp_down)
    influx_write(ups=up, downs=down)
