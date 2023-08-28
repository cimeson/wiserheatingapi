from dotenv import load_dotenv
from prometheus_client import start_http_server, Enum, Gauge, Summary
from wiserHeatingAPI import wiserHub
import datetime
import os
import time

load_dotenv()

if "WISER_HUBHOST" not in os.environ:
    raise EnvironmentError("Failed because envvar WISER_HUBHOST is not set.")
if "WISER_HUBSECRET" not in os.environ:
    raise EnvironmentError("Failed because envvar WISER_HUBSECRET is not set.")

debugEnabled = os.environ.get("WISER_DEBUG") == '1'
wiserhost = os.environ.get("WISER_HUBHOST")
wiserkey = os.environ.get("WISER_HUBSECRET")
delay = int(os.environ.get("WISER_DELAY", 60))

REQUEST_TIME = Summary('request_processing_seconds', 'Time spent processing request')

global_metrics = {
    'heating': Enum('wiser_heating_output_state', 'Heating Output State', states = ['Off', 'On'], labelnames = ['hubHost', 'hubName']),
    'hotwater': Enum('wiser_hotwater_output_state', 'Hot Water Output State', states = ['Off', 'On'], labelnames = ['hubHost', 'hubName']),
}

room_metrics = {
    'humidity': Gauge('wiser_room_humidity_percent', 'Room Humidity Percent', labelnames = ['hubHost', 'hubName', 'roomId', 'roomName']),
    'outputstate': Enum('wiser_room_output_state', 'Room Output State', states = ['Off', 'On'], labelnames = ['hubHost', 'hubName', 'roomId', 'roomName']),
    'setpoint': Gauge('wiser_room_setpoint_celsius', 'Room Set Point Celsius', labelnames = ['hubHost', 'hubName', 'roomId', 'roomName']),
    'temprature': Gauge('wiser_room_temperature_celsius', 'Room Temperature Celsius', labelnames = ['hubHost', 'hubName', 'roomId', 'roomName'])
}

@REQUEST_TIME.time()
def process_request():
    """Query the metrics from the Wiser hub."""

    wh = wiserHub.wiserHub(wiserhost, wiserkey)
    hubName = wh.getWiserHubName()
    systemInfo = wh.getSystem()
    heatingRelayStatus = wh.getHeatingRelayStatus()
    hotwaterRelayState = wh.getHotwaterRelayStatus()
    global_metrics['heating'].labels(hubHost = wiserhost, hubName = hubName).state(heatingRelayStatus)
    global_metrics['hotwater'].labels(hubHost = wiserhost, hubName = hubName).state(hotwaterRelayState)

    if debugEnabled:
        print('---')
        print("Hub: HubHost = {}, HubName = {}, SystemTime = {}".format(wiserhost, hubName, datetime.datetime.fromtimestamp(systemInfo['UnixTime'])))
        print("State: Heating = {}, HotWater = {}".format(heatingRelayStatus, hotwaterRelayState))

    for room in wh.getRooms():
        roomId = room.get("id")
        roomName = room.get("Name").strip()
        roomLabels = {'hubHost': wiserhost, 'hubName': hubName, 'roomId': roomId, 'roomName': roomName}

        roomStatId = room.get("RoomStatId")
        roomstat = wh.getRoomStatData(roomStatId) if roomStatId is not None else None

        # room heating control output
        roomOutputState = room.get("ControlOutputState")
        room_metrics['outputstate'].labels(wiserhost, hubName, roomId, roomName).state(roomOutputState)

        # room heating temprature set point
        roomSetPoint = room.get("CurrentSetPoint") / 10
        room_metrics['setpoint'].labels(wiserhost, hubName, roomId, roomName).set(roomSetPoint)

        # room temprature calculated
        roomTemprature = room.get("CalculatedTemperature") / 10
        room_metrics['temprature'].labels(wiserhost, hubName, roomId, roomName).set(roomTemprature)

        # humidity only available where a RoomStat is installed
        if roomstat is not None:
            roomHumidity = roomstat.get("MeasuredHumidity")
            room_metrics['humidity'].labels(wiserhost, hubName, roomId, roomName).set(roomHumidity)

        if debugEnabled:
            print("Room: Id = {}, Name = {}, CalculatedTemperature = {}, CurrentSetPoint = {}, RoomOutputState = {}, Humidity = {}".format(
                roomId,
                roomName,
                room.get("CalculatedTemperature") / 10,
                room.get("CurrentSetPoint") / 10,
                roomOutputState,
                roomHumidity if roomstat is not None else "No RoomStat"
            ))

if __name__ == '__main__':
    start_http_server(8000)
    while True:
        process_request()
        time.sleep(delay)
