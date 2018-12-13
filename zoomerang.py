
"""
Make an audio recording of a Zoom meeting.
"""

import datetime
import os
import requests
import yaml
from time import sleep
from twilio.rest import Client

# Load configuration file.
dir_path = os.path.dirname(os.path.realpath(__file__))
with open(os.path.join(dir_path, "zoomerang.yaml")) as fp:
    config = yaml.load(fp)

def record_zoom_meeting(meeting_id, meeting_duration=120, full_output=False):
    """
    Make an audio recording of a Zoom meeting, and return a URL where the
    recording can be directly accessed.

    :param meeting_id:
        The Zoom meeting ID.

    :param meeting_duration: [optional]
        The expected meeting duration (in seconds). This defaults to one hour.

    :param full_output: [optional]
        If `True`, return the URL of the recording, and the call instance, and
        the recording instance. If `False` then just return the URL of the
        recording.

    :returns:
        The URL of the audio recording of the meeting.
    """

    # Construct a URL with our TwiML instructions.
    TwiML = f"""
    <?xml version="1.0" encoding="UTF-8"?>
    <Response>
      <Pause length="{meeting_duration}"/>
      <Hangup/>
    </Response>
    """.strip()

    call_url = requests.Request("GET", "http://twimlets.com/echo",
                                params=dict(Twiml=TwiML)).prepare().url

    # Call in and record.
    client = Client(config["twilio_account_sid"], config["twilio_auth_token"])
    call = client.calls.create(to=config["zoom_phone_number"],
                               from_=config["twilio_phone_number"],
                               send_digits=f"{meeting_id}#",
                               record=True,
                               url=call_url)

    # Now we wait. Give an extra 60 seconds for connection, processing, etc.
    sleep(meeting_duration + 60)

    while True:
        recordings = call.recordings.list()
        if len(recordings) < 1:
            sleep(10)
        else:
            recording = recordings[0]
            break

    url = "https://api.twilio.com{0}.mp3".format(recording.uri[:-5])

    if full_output:
        return (url, call, recording)

    return url



if __name__ == "__main__":

    import sys

    if len(sys.argv) < 2:
        exit()

    meeting_id = sys.argv[1]
    if len(sys.argv) == 2:
        summary = f"Meeting {meeting_id}"
    else:
        summary = sys.argv[2]

    # Prepare the output path.
    recordings_dir_path = "/var/www/html/recordings/"
    os.makedirs(recordings_dir_path, exist_ok=True)

    now = datetime.datetime.now().isoformat()
    output_prefix = os.path.join(recordings_dir_path, f"{meeting_id}-{now}")


    # Get the URL of the recording for the given meeting.
    print(f"Recording Zoom meeting {meeting_id}")
    url, call, recording = record_zoom_meeting(meeting_id, full_output=True)

    print(f"Retrieving audio from {url}")

    # Download the recording.
    while True:
        r = requests.get(url)
        if not r.ok:
            print("Request failed. Waiting and trying again.")
            sleep(10)

        break

    with open(f"{output_prefix}.mp3", "wb") as fp:
        fp.write(r.content)

    meta = dict(meeting_id=meeting_id,
                summary=summary,
                start_datetime=now,
                audio_path=f"{output_prefix}.mp3")

    with open(f"{output_prefix}.yaml", "w") as fp:
        fp.write(yaml.dump(meta))

    # Update the RSS feed.
    # TODO

    print("Complete")

