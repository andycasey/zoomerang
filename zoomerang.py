
"""
Make an audio recording of a Zoom meeting.
"""

import datetime
import os
import requests
import yaml
from glob import glob
from time import sleep
from urllib import parse

import dateutil.parser
from twilio.rest import Client
from podgen import Podcast, Episode, Media

def record_meeting(twilio_account_sid, twilio_auth_token, twilio_phone_number,
                   meeting_id, summary=None, conference_phone_number=None, 
                   duration=3600, full_output=False):
    """
    Make an audio recording of a meeting (e.g., a Zoom meeting), and return a 
    URL where the recording can be directly accessed.

    :param meeting_id:
        The meeting ID.

    :param duration: [optional]
        The expected meeting duration (in seconds). This defaults to one hour.

    :param conference_phone_number: [optional]
        The conference call number. If `None` is provided then the meeting is
        assumed to be a Zoom meeting.

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
      <Pause length="{duration}"/>
      <Hangup/>
    </Response>
    """.strip()

    call_url = requests.Request("GET", "http://twimlets.com/echo",
                                params=dict(Twiml=TwiML)).prepare().url

    # Call in and record.
    client = Client(twilio_account_sid, twilio_auth_token)
    call = client.calls.create(to=conference_phone_number,
                               from_=twilio_phone_number,
                               send_digits=f"{meeting_id}#",
                               record=True,
                               url=call_url)

    # Now we wait. Give an extra 60 seconds for connection, processing, etc.
    sleep(duration + 60)

    while True:
        recordings = call.recordings.list()
        if len(recordings) < 1:
            sleep(10)
        else:
            recording = recordings[0]
            break

    url = "https://api.twilio.com{0}.mp3".format(recording.uri[:-5])

    # Twilio MP3s have a rate of 32 kilobits per second.
    estimated_file_size = int((int(recording.duration) * 32) / 8 * 1000)

    metadata = dict(summary=summary,
                    meeting_id=meeting_id,
                    conference_phone_number=conference_phone_number,
                    url=url,
                    duration=int(recording.duration),
                    start_datetime=recording.start_time.isoformat(),
                    created_datetime=recording.date_created.isoformat(),
                    price=float(recording.price),
                    price_unit=recording.price_unit,
                    estimated_file_size=estimated_file_size)

    if full_output:
        return (metadata, call, recording)

    return metadata



if __name__ == "__main__":

    import argparse

    # Load config.
    dir_path = os.path.dirname(os.path.realpath(__file__))
    with open(os.path.join(dir_path, "zoomerang.yaml")) as fp:
        config = yaml.load(fp)

    parser = argparse.ArgumentParser(description="Record a scheduled meeting")
    parser.add_argument("meeting_id", type=int)
    parser.add_argument("summary", type=str,
                        help="a description of the meeting purpose")
    parser.add_argument("--phone-number", nargs=1, type=str, 
                        default=config["zoom_phone_number"],
                        help="the call number to use (defaults to Zoom)")
    parser.add_argument("--duration", type=int, default=60,
                        help="the expected meeting duration (in minutes)")

    args = parser.parse_args()


    # Prepare the output path.
    recordings_dir_path = config["recordings_local_path"]
    os.makedirs(recordings_dir_path, exist_ok=True)

    now = datetime.datetime.now().isoformat()
    output_prefix = os.path.join(recordings_dir_path, f"{now}-{args.meeting_id}")

    if args.meeting_id > 0:
        print(f"Recording meeting ID {args.meeting_id} (tel: {args.phone_number} "\
              f"for up to {args.duration} minutes)")

        # Get the URL of the recording for the given meeting.
        meeting = record_meeting(config["twilio_account_sid"], 
                                 config["twilio_auth_token"],
                                 config["twilio_phone_number"],
                                 args.meeting_id,
                                 conference_phone_number=args.phone_number,
                                 duration=60 * args.duration,
                                 summary=args.summary)

        print(f"Call complete. Response: {meeting}")

        # Save the meeting details.
        with open(f"{output_prefix}.yaml", "w") as fp:
            fp.write(yaml.dump(meeting))

    # Update podcast.
    podcast = Podcast(name="Zoomerang",
                      description="Telecons you missed while you were sleeping.",
                      website=config["zoomerang_remote_addr"],
                      explicit=False)

    meeting_paths = glob(f"{recordings_dir_path}*.yaml")
    for meeting_path in meeting_paths:
        with open(meeting_path, "r") as fp:
            meeting = yaml.load(fp)

        podcast.add_episode(Episode(
            title=meeting["summary"],
            media=Media(meeting["url"], 
                        size=meeting["estimated_file_size"],
                        type="audio/mpeg",
                        duration=datetime.timedelta(seconds=meeting["duration"])),
            publication_date=dateutil.parser.parse(meeting["created_datetime"])))

    with open(config["zoomerang_podcast_path"], "w") as fp:
        fp.write(f"{podcast}")

    print("Updated podcast.")

