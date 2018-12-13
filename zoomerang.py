
"""
Make an audio recording of a Zoom meeting.
"""

# Additional steps:
# 0. Get meeting information from Calendar?
# 1. Put the recording to a new podcast RSS feed?
# 2. Notify upon failure?

import os
import requests
import yaml
from twilio.rest import Client

# Load configuration file.
dir_path = os.path.dirname(os.path.realpath(__file__))
with open(os.path.join(dir_path, "zoomerang.yaml")) as fp:
    config = yaml.load(fp)

def record_zoom_meeting(meeting_id, meeting_duration=3600, full_output=False):
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

    recording = call.recordings.list()[0]
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
        summary = sys.argv[2:]

    # Prepare the output path.
    recordings_dir_path = os.path.join(dir_path, "recordings")
    os.makedirs(recordings_dir_path, exist_ok=True)

    now = datetime.datetime.now().isoformat()
    output_prefix = os.path.join(recordings_dir_path, f"{meeting_id}-{now}")
    

    # Get the URL of the recording for the given meeting.
    url, call, recording = record_zoom_meeting(meeting_id, full_output=True)

    # Download the recording.
    r = requests.get(url)
    if not r.ok:
        r.raise_for_status()

    with open(f"{output_prefix}.mp3", "wb") as fp:
        fp.write(r.content)

    meta = dict(meeting_id=meeting_id, 
                summary=summary,
                start_datetime=now,
                audio_path=f"{output_prefix}.mp3")

    with open(f"{output_path}.yaml", "w") as fp:
        fp.write(yaml.dumps(meta))

    # Update the RSS feed.
    # TODO

    print("Done")

