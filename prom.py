from dotenv import load_dotenv
from prometheus_client import start_http_server, Enum, Gauge, Summary
from wiserHeatingAPI import wiserHub
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

REQUEST_TIME = Summary('request_processing_seconds', 'Time spent processing request')

global_metrics = {
    'hotwater': Enum('wiser_hotwater_output_state', 'Hot Water Output State', states = ['Off', 'On'], labelnames = ['hubHost', 'hubName'])
}
rooms = {}

@REQUEST_TIME.time()
def process_request(wh):
    """Query the metrics from the Wiser hub."""

    hotwaterOutputState = wh.getHotwaterRelayStatus()
    global_metrics['hotwater'].labels(hubHost = wiserhost, hubName = hubName).state(hotwaterOutputState)

    if debugEnabled:
        print('---')
        print("Hub HubHost = {}, HubName = {}".format(wiserhost, hubName))
        print("HotWater State = {}".format(hotwaterOutputState))

    for room in wh.getRooms():
        roomId = room.get("id")
        roomName = room.get("Name").strip()

        if not roomId in rooms:
            rooms[roomId] = {
                'temprature': Gauge('wiser_room_temperature_celsius', 'Room Temperature Celsius', labelnames = ['hubHost', 'hubName', 'roomId', 'roomName']),
                'setpoint': Gauge('wiser_room_setpoint_celsius', 'Room Set Point Celsius', labelnames = ['hubHost', 'hubName', 'roomId', 'roomName']),
                'outputstate': Enum('wiser_room_output_state', 'Room Output State', states = ['Off', 'On'], labelnames = ['hubHost', 'hubName', 'roomId', 'roomName'])
            }

        roomTemprature = room.get("CalculatedTemperature") / 10
        rooms[roomId]['temprature'].labels(hubHost = wiserhost, hubName = hubName, roomId = roomId, roomName = roomName).set(roomTemprature)

        roomSetPoint = room.get("CurrentSetPoint") / 10
        rooms[roomId]['setpoint'].labels(hubHost = wiserhost, hubName = hubName, roomId = roomId, roomName = roomName).set(roomSetPoint)

        roomOutputState = room.get("ControlOutputState")
        rooms[roomId]['outputstate'].labels(hubHost = wiserhost, hubName = hubName, roomId = roomId, roomName = roomName).state(roomOutputState)

        if debugEnabled:
            print("Room Id = {}, Name = {}, CalculatedTemperature = {}, CurrentSetPoint = {}, RoomOutputState = {}".format(
                roomId,
                roomName,
                room.get("CalculatedTemperature") / 10,
                room.get("CurrentSetPoint") / 10,
                roomOutputState
            ))

if __name__ == '__main__':
    wh = wiserHub.wiserHub(wiserhost, wiserkey)
    hubName = wh.getWiserHubName()

    start_http_server(8000)
    while True:
        process_request(wh)
        time.sleep(60)
