import sys
import json
import os
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8")

from curl_cffi import requests


# ============================================================
# CONFIGURATION
# ============================================================

URL = "https://www.redbus.in/rpw/api/searchResults"

DATES = [
    "15-Oct-2026",
    "16-Oct-2026",
    "24-Oct-2026",
    "25-Oct-2026",
]

FROM_CITY = "75494"
TO_CITY = "94698"

START_TIME = "10:00"
END_TIME = "16:00"

STATE_FILE = "state.json"
CONFIG_FILE = "config.json"

# Telegram credentials are read from environment variables.
# Local Windows:
#   set TELEGRAM_BOT_TOKEN=your_bot_token
#   set TELEGRAM_CHAT_ID=your_chat_id
#
# GitHub Actions:
#   store these two values as repository Secrets.
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()


# ============================================================
# HEADERS
# ============================================================

HEADERS = {
    "accept": "application/json, text/plain, */*",
    "content-type": "application/json",
    "origin": "https://www.redbus.in",
    "referer": "https://www.redbus.in/",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/142.0.0.0 Safari/537.36"
    ),
}


# ============================================================
# SESSION
# ============================================================

session = requests.Session(
    impersonate="chrome"
)


def load_config():
    config = {"dates": DATES, "start": START_TIME, "end": END_TIME, "offset": 0}
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            config.update(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return config


def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def telegram_request(method, **kwargs):
    if not TELEGRAM_BOT_TOKEN:
        return {}
    try:
        response = session.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/{method}",
            timeout=30,
            **kwargs,
        )
        return response.json() if response.status_code == 200 else {}
    except Exception as e:
        print("Telegram error:", repr(e))
        return {}


def send_telegram_message(chat_id, text):
    return telegram_request("sendMessage", data={"chat_id": chat_id, "text": text}).get("ok", False)


def valid_dates(values):
    try:
        dates = [datetime.strptime(value, "%d-%b-%Y").strftime("%d-%b-%Y") for value in values]
        return dates or None
    except ValueError:
        return None


def valid_time(value):
    try:
        return datetime.strptime(value, "%H:%M").strftime("%H:%M")
    except ValueError:
        return None


def process_telegram_commands(config):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return config

    updates = telegram_request(
        "getUpdates",
        params={"offset": config.get("offset", 0) + 1, "timeout": 0},
    ).get("result", [])
    for update in updates:
        config["offset"] = update["update_id"]
        message = update.get("message", {})
        chat_id = str(message.get("chat", {}).get("id", ""))
        if chat_id != TELEGRAM_CHAT_ID:
            continue
        parts = message.get("text", "").strip().split()
        command = parts[0].split("@", 1)[0].lower() if parts else ""
        args = parts[1:]
        reply = None
        if command == "/dates":
            dates = valid_dates(args) if args else config["dates"]
            if args and dates:
                config["dates"] = dates
                reply = "Dates updated: " + ", ".join(dates)
            elif args:
                reply = "Use dates like: /dates 15-Oct-2026 16-Oct-2026"
            else:
                reply = "Dates: " + ", ".join(config["dates"])
        elif command == "/time":
            if len(args) == 2 and valid_time(args[0]) and valid_time(args[1]):
                config["start"], config["end"] = args
                reply = f"Time updated: {args[0]} - {args[1]}"
            else:
                reply = "Use: /time 10:00 16:00"
        elif command == "/set" and len(args) >= 3:
            dates = valid_dates(args[:-2])
            start, end = valid_time(args[-2]), valid_time(args[-1])
            if dates and start and end:
                config.update(dates=dates, start=start, end=end)
                reply = f"Updated: {', '.join(dates)} | {start} - {end}"
            else:
                reply = "Use: /set 15-Oct-2026 16-Oct-2026 10:00 16:00"
        elif command == "/status":
            reply = f"Dates: {', '.join(config['dates'])}\nTime: {config['start']} - {config['end']}"
        elif command == "/help":
            reply = "/dates DATE...\n/time HH:MM HH:MM\n/set DATE... START END\n/status"
        if reply:
            send_telegram_message(chat_id, reply)
    save_config(config)
    return config


# ============================================================
# INITIALIZE REDBUS SESSION
# ============================================================

def initialize_session():

    print("=" * 80)
    print("INITIALIZING REDBUS SESSION")
    print("=" * 80)

    try:

        response = session.get(
            "https://www.redbus.in/",
            headers=HEADERS,
            timeout=30,
        )

        print(
            "Homepage status:",
            response.status_code
        )

        if response.status_code != 200:
            print(
                "Warning: RedBus homepage returned",
                response.status_code
            )

    except Exception as e:

        print(
            "Homepage request failed:",
            repr(e)
        )

    print()


# ============================================================
# TELEGRAM NOTIFICATION
# ============================================================

def send_telegram_notification(available_buses):

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:

        print()
        print("Telegram notification skipped.")
        print(
            "Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID "
            "environment variables."
        )

        return False

    if not available_buses:

        # No currently returned matching buses.
        return False

    lines = [
        "🚌 REDBUS BUS ALERT",
        "",
        f"Route: {FROM_CITY} → {TO_CITY}",
        f"Departure window: {START_TIME} - {END_TIME}",
        "",
    ]

    total_buses = sum(
        len(buses)
        for buses in available_buses.values()
    )

    lines.append(
        f"Currently available matching buses: {total_buses}"
    )
    lines.append("")

    for journey_date, buses in available_buses.items():

        if not buses:
            continue

        lines.append(f"📅 {journey_date}")

        for bus in buses.values():

            service_name = (
                bus.get("serviceName")
                or bus.get("travelsName")
                or "Unknown service"
            )

            departure = bus.get(
                "departureTime",
                "Unknown"
            )

            arrival = bus.get(
                "arrivalTime",
                "Unknown"
            )

            fare_list = bus.get(
                "fareList",
                []
            )

            if fare_list:
                fare = ", ".join(
                    f"₹{x}" for x in fare_list
                )
            else:
                fare = "N/A"

            available = bus.get(
                "availableSeats",
                "N/A"
            )

            total = bus.get(
                "totalSeats",
                "N/A"
            )

            lines.extend([
                f"🚌 {service_name}",
                f"🕐 {departure} → {arrival}",
                f"💺 Seats: {available}/{total}",
                f"💰 Fare: {fare}",
                "",
            ])

    message = "\n".join(lines)

    telegram_url = (
        "https://api.telegram.org/bot"
        f"{TELEGRAM_BOT_TOKEN}/sendMessage"
    )

    try:

        response = session.post(telegram_url, data={"chat_id": TELEGRAM_CHAT_ID, "text": message}, timeout=30)

        if response.status_code == 200:

            result = response.json()

            if result.get("ok"):

                print()
                print("Telegram notification sent successfully.")

                return True

        print()
        print(
            "Telegram notification failed:",
            response.status_code,
            response.text[:500]
        )

    except Exception as e:

        print()
        print(
            "Telegram notification error:",
            repr(e)
        )

    return False


# ============================================================
# LOAD PREVIOUS STATE
# ============================================================

def load_state():

    if not os.path.exists(STATE_FILE):

        return {}

    try:

        with open(
            STATE_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except Exception as e:

        print(
            "Could not load state:",
            e
        )

        return {}


# ============================================================
# SAVE STATE
# ============================================================

def save_state(state):

    temp_file = STATE_FILE + ".tmp"

    with open(
        temp_file,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            state,
            f,
            indent=2,
            ensure_ascii=False
        )

    os.replace(
        temp_file,
        STATE_FILE
    )


# ============================================================
# GET REDBUS DATA
# ============================================================

def get_buses(doj):

    print("=" * 80)
    print("DATE:", doj)
    print("=" * 80)

    params = {
        "fromCity": FROM_CITY,
        "toCity": TO_CITY,
        "DOJ": doj,
        "limit": "10",
        "offset": "0",
        "meta": "true",
        "groupId": "0",
        "sectionId": "0",
        "sort": "0",
        "sortOrder": "0",
        "from": "initialLoad",
        "getUuid": "true",
        "bT": "1",
        "clearLMBFilter": "undefined",
        "isFilterApplied": "false",
    }

    try:

        response = session.post(
            URL,
            params=params,
            headers=HEADERS,
            timeout=60,
        )

    except Exception as e:

        print(
            "REQUEST ERROR:",
            repr(e)
        )

        return None, None

    print(
        "STATUS:",
        response.status_code
    )

    if response.status_code != 200:

        print(
            "HTTP ERROR:",
            response.text[:300]
        )

        return None, None

    try:

        result = response.json()

    except Exception as e:

        print(
            "JSON ERROR:",
            e
        )

        return None, None

    success = result.get(
        "success",
        False
    )

    print(
        "SUCCESS:",
        success
    )

    if not success:

        return None, None

    data = result.get(
        "data",
        {}
    )

    metadata = data.get(
        "metaData",
        {}
    )

    total_count = metadata.get(
        "totalCount",
        0
    )

    print(
        "TOTAL COUNT:",
        total_count
    )

    inventories = data.get(
        "inventories",
        []
    )

    print(
        "INVENTORIES:",
        len(inventories)
    )

    # --------------------------------------------------------
    # IMPORTANT
    # --------------------------------------------------------
    #
    # RedBus sometimes returns:
    #
    # totalCount > 0
    # inventories = []
    #
    # Therefore we return both values.
    #

    return inventories, total_count


# ============================================================
# TIME FILTER
# ============================================================

def is_time_in_range(departure_time):

    if not departure_time:

        return False

    try:

        # Example:
        #
        # 2026-10-24 13:45:00
        #
        time_part = departure_time[11:16]

        return (
            START_TIME
            <= time_part
            <= END_TIME
        )

    except Exception:

        return False


# ============================================================
# CREATE UNIQUE BUS KEY
# ============================================================

def get_bus_key(bus):

    service_id = bus.get(
        "serviceId"
    )

    route_id = bus.get(
        "routeId"
    )

    departure = bus.get(
        "departureTime"
    )

    return (
        f"{service_id}|"
        f"{route_id}|"
        f"{departure}"
    )


# ============================================================
# NORMALIZE BUS
# ============================================================

def normalize_bus(bus, journey_date):

    return {

        "journeyDate": journey_date,

        "travelsName": bus.get(
            "travelsName"
        ),

        "serviceName": bus.get(
            "serviceName"
        ),

        "serviceId": bus.get(
            "serviceId"
        ),

        "routeId": bus.get(
            "routeId"
        ),

        "operatorId": bus.get(
            "operatorId"
        ),

        "busType": bus.get(
            "busType"
        ),

        "departureTime": bus.get(
            "departureTime"
        ),

        "arrivalTime": bus.get(
            "arrivalTime"
        ),

        "journeyDurationMin": bus.get(
            "journeyDurationMin"
        ),

        "fareList": bus.get(
            "fareList"
        ),

        "availableSeats": bus.get(
            "availableSeats"
        ),

        "totalSeats": bus.get(
            "totalSeats"
        ),

        "availableWindowSeats": bus.get(
            "availableWindowSeats"
        ),

        "availableAisleSeats": bus.get(
            "availableAisleSeats"
        ),

        "standardBpName": bus.get(
            "standardBpName"
        ),

        "standardDpName": bus.get(
            "standardDpName"
        ),

        "busTypeId": bus.get(
            "busTypeId"
        ),

        "isRtc": bus.get(
            "isRtc"
        ),

        "isNonAc": bus.get(
            "isNonAc"
        ),

        "isSeater": bus.get(
            "isSeater"
        ),

        "isMticketEnabled": bus.get(
            "isMticketEnabled"
        ),
    }


# ============================================================
# FILTER BUSES
# ============================================================

def filter_matching_buses(
    inventories,
    journey_date
):

    matching = {}

    for bus in inventories:

        departure = bus.get(
            "departureTime"
        )

        if not is_time_in_range(
            departure
        ):

            continue

        normalized = normalize_bus(
            bus,
            journey_date
        )

        key = get_bus_key(
            bus
        )

        matching[key] = normalized

    return matching


# ============================================================
# COMPARE BUS
# ============================================================

def compare_bus(
    old_bus,
    new_bus
):

    changes = []

    old_seats = old_bus.get(
        "availableSeats"
    )

    new_seats = new_bus.get(
        "availableSeats"
    )

    if old_seats != new_seats:

        changes.append(
            f"Available seats: "
            f"{old_seats} -> {new_seats}"
        )

    old_fare = old_bus.get(
        "fareList"
    )

    new_fare = new_bus.get(
        "fareList"
    )

    if old_fare != new_fare:

        changes.append(
            f"Fare: "
            f"{old_fare} -> {new_fare}"
        )

    return changes


# ============================================================
# PRINT NEW BUS ALERT
# ============================================================

def print_new_bus_alert(bus):

    print()
    print("!" * 80)
    print("🚌 NEW BUS AVAILABLE")
    print("!" * 80)

    print(
        "Journey Date:",
        bus.get("journeyDate")
    )

    print(
        "Departure:",
        bus.get("departureTime")
    )

    print(
        "Arrival:",
        bus.get("arrivalTime")
    )

    print(
        "Bus:",
        bus.get("travelsName")
    )

    print(
        "Service:",
        bus.get("serviceName")
    )

    print(
        "Service ID:",
        bus.get("serviceId")
    )

    print(
        "Route ID:",
        bus.get("routeId")
    )

    print(
        "Bus Type:",
        bus.get("busType")
    )

    print(
        "Fare:",
        bus.get("fareList")
    )

    print(
        "Available Seats:",
        bus.get("availableSeats")
    )

    print(
        "Total Seats:",
        bus.get("totalSeats")
    )

    print(
        "Boarding:",
        bus.get("standardBpName")
    )

    print(
        "Dropping:",
        bus.get("standardDpName")
    )

    print("!" * 80)
    print()


# ============================================================
# PRINT CHANGE ALERT
# ============================================================

def print_change_alert(
    bus,
    changes
):

    print()
    print("!" * 80)
    print("🔔 BUS INFORMATION CHANGED")
    print("!" * 80)

    print(
        "Journey Date:",
        bus.get("journeyDate")
    )

    print(
        "Departure:",
        bus.get("departureTime")
    )

    print(
        "Bus:",
        bus.get("travelsName")
    )

    print(
        "Service ID:",
        bus.get("serviceId")
    )

    for change in changes:

        print(
            "CHANGE:",
            change
        )

    print("!" * 80)
    print()


# ============================================================
# CHECK ONE DATE
# ============================================================

def check_date(
    journey_date,
    previous_state
):

    inventories, total_count = get_buses(
        journey_date
    )

    # --------------------------------------------------------
    # API request failed
    # --------------------------------------------------------

    if inventories is None:

        print(
            "API request failed for",
            journey_date
        )

        return (
            previous_state,
            False,
            {}
        )

    # --------------------------------------------------------
    # Important:
    #
    # inventories=[] does NOT mean no buses.
    #
    # If total_count > 0, RedBus has results but did not
    # provide inventory objects in this response.
    # --------------------------------------------------------

    if (
        len(inventories) == 0
        and total_count > 0
    ):

        print()
        print(
            "RedBus reports",
            total_count,
            "results, but no inventory "
            "details were returned."
        )

        print(
            "Keeping previous state unchanged."
        )

        return (
            previous_state,
            False,
            {}
        )

    # --------------------------------------------------------
    # Filter 10:00 - 16:00
    # --------------------------------------------------------

    current_buses = filter_matching_buses(
        inventories,
        journey_date
    )

    print(
        "MATCHING BUSES (10:00-16:00):",
        len(current_buses)
    )

    # --------------------------------------------------------
    # Previous buses for this date
    # --------------------------------------------------------

    old_buses = previous_state.get(
        journey_date,
        {}
    )

    # --------------------------------------------------------
    # New buses
    # --------------------------------------------------------

    for key, bus in current_buses.items():

        if key not in old_buses:

            print_new_bus_alert(
                bus
            )

        else:

            changes = compare_bus(
                old_buses[key],
                bus
            )

            if changes:

                print_change_alert(
                    bus,
                    changes
                )

    # --------------------------------------------------------
    # Buses that disappeared
    # --------------------------------------------------------

    for key, old_bus in old_buses.items():

        if key not in current_buses:

            print()
            print(
                "BUS NO LONGER RETURNED:"
            )

            print(
                old_bus.get(
                    "journeyDate"
                ),
                "|",
                old_bus.get(
                    "departureTime"
                ),
                "|",
                old_bus.get(
                    "travelsName"
                )
            )

    # --------------------------------------------------------
    # Update state
    # --------------------------------------------------------

    previous_state[journey_date] = (
        current_buses
    )

    return (
        previous_state,
        True,
        current_buses
    )


# ============================================================
# MAIN
# ============================================================

def main():

    global DATES, START_TIME, END_TIME

    print()
    print("=" * 80)
    print("REDBUS MONITOR")
    print("=" * 80)

    config = process_telegram_commands(load_config())
    DATES = config["dates"]
    START_TIME, END_TIME = config["start"], config["end"]
    print("Journey dates:", ", ".join(DATES))
    print("Departure window:", START_TIME, "to", END_TIME)

    print()

    initialize_session()

    previous_state = load_state()

    successful_dates = 0

    # Buses confirmed by the current API run.
    # Only these are sent to Telegram.
    available_buses = {}

    for journey_date in DATES:

        try:

            (
                previous_state,
                successful,
                current_buses
            ) = check_date(
                journey_date,
                previous_state
            )

            if successful:

                successful_dates += 1

                if current_buses:

                    available_buses[journey_date] = (
                        current_buses
                    )

        except Exception as e:

            print()
            print(
                "ERROR processing",
                journey_date
            )

            print(
                repr(e)
            )

    # --------------------------------------------------------
    # Telegram notification
    # --------------------------------------------------------

    if available_buses:

        send_telegram_notification(
            available_buses
        )

    else:

        print()
        print(
            "No matching buses currently available."
        )

    # --------------------------------------------------------
    # Save state
    # --------------------------------------------------------

    save_state(
        previous_state
    )

    print()
    print("=" * 80)
    print("MONITOR FINISHED")
    print("=" * 80)

    print(
        "Successful dates:",
        successful_dates,
        "/",
        len(DATES)
    )

    print(
        "State saved to:",
        STATE_FILE
    )

    print(
        "Checked departure window:",
        START_TIME,
        "-",
        END_TIME
    )

    print(
        "Telegram configured:",
        bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)
    )

    print("=" * 80)


if __name__ == "__main__":

    main()