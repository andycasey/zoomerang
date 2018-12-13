
"""
Make an audio recording of a Zoom meeting.
"""

import datetime
import os
import requests
import yaml
from glob import glob
from time import sleep
from twilio.rest import Client

# Load configuration file.
dir_path = os.path.dirname(os.path.realpath(__file__))
with open(os.path.join(dir_path, "zoomerang.yaml")) as fp:
    config = yaml.load(fp)

def record_meeting(meeting_id, duration=3600, phone_number=None,
                   full_output=False):
    """
    Make an audio recording of a meeting (e.g., a Zoom meeting), and return a 
    URL where the recording can be directly accessed.

    :param meeting_id:
        The meeting ID.

    :param duration: [optional]
        The expected meeting duration (in seconds). This defaults to one hour.

    :param phone_number: [optional]
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

    if phone_number is None:
        phone_number = config["zoom_phone_number"]

    call_url = requests.Request("GET", "http://twimlets.com/echo",
                                params=dict(Twiml=TwiML)).prepare().url

    # Call in and record.
    client = Client(config["twilio_account_sid"], config["twilio_auth_token"])
    call = client.calls.create(to=phone_number,
                               from_=config["twilio_phone_number"],
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

    if full_output:
        return (url, call, recording)

    return url



if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser(description="Record a scheduled meeting")
    parser.add_argument("meeting_id", type=int)
    parser.add_argument("summary", type=str,
                        help="a description of the meeting purpose")
    parser.add_argument("--phone-number", nargs=1, type=str, default=None,
                        help="the call number to use (defaults to Zoom)")
    parser.add_argument("--duration", type=int, default=60,
                        help="the expected meeting duration (in minutes)")

    args = parser.parse_args()

    
    # Prepare the output path.
    recordings_dir_path = "/var/www/html/recordings/"
    os.makedirs(recordings_dir_path, exist_ok=True)

    now = datetime.datetime.now().isoformat()
    output_prefix = os.path.join(recordings_dir_path, f"{now}-{args.meeting_id}")

    # Get the URL of the recording for the given meeting.
    print(f"Recording meeting ID {args.meeting_id} (tel: {args.phone_number} "\
          f"for up to {args.duration} minutes")

    url, call, recording = record_meeting(args.meeting_id,
                                          duration=60*args.duration,
                                          phone_number=args.phone_number,
                                          full_output=True)

    print(f"Call complete. Retrieving audio from {url}")

    # Download the recording.
    while True:
        r = requests.get(url)
        if not r.ok:
            print("Request failed. Waiting and trying again.")
            sleep(10)

        break

    with open(f"{output_prefix}.mp3", "wb") as fp:
        fp.write(r.content)

    meta = dict(meeting_id=args.meeting_id,
                summary=args.summary,
                start_datetime=now,
                duration=args.duration,
                phone_number=args.phone_number,
                audio_path=f"{output_prefix}.mp3")

    with open(f"{output_prefix}.yaml", "w") as fp:
        fp.write(yaml.dump(meta))

    # Update the RSS feed.
    # TODO
    print(meta)

    zoomerang_url = config["zoomerang_url"]


    rss_content = f"""
<rss xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" xmlns:atom="http://www.w3.org/2005/Atom" xmlns:media="http://search.yahoo.com/mrss/" version="2.0">
<channel>
<atom:link href="http://www.abc.net.au/radio/programs/the-signal/feed/9443166/podcast.xml" rel="self" type="application/xml"/>
<title>Zoomerang</title>
<itunes:subtitle>Sleep is important. So is work.</itunes:subtitle>
<description>
<![CDATA[
Your sleep is important, and Australia's time zone sucks. Zoomerang records the scheduled telecons that you slept through.
]]>
</description>
<link>{zoomerang_url}</link>
<copyright></copyright>
<language>en</language>
<image>
<title>Zoomerang</title>
<url>http://www.abc.net.au/cm/rimage/9446470-1x1-thumbnail.jpg?v=4</url>
<link>{zoomerang_url}</link>
</image>
<itunes:image href="http://www.abc.net.au/cm/rimage/9446470-1x1-large.jpg?v=4"/>
<itunes:author>Andy Casey</itunes:author>
<itunes:owner>
<itunes:name>Andy Casey</itunes:name>
<itunes:email>andrew.casey@monash.edu</itunes:email>
</itunes:owner>
<itunes:summary>
Your sleep is important, and Australia's time zone sucks. Zoomerang records the scheduled telecons that you slept through.
</itunes:summary>
<itunes:category text="News"/>
<itunes:explicit>no</itunes:explicit>
<lastBuildDate>{now}</lastBuildDate>"""
    
    rss_item_template = """
<item>
<title>{title}</title>
<itunes:subtitle>
{subtitle}
</itunes:subtitle>
<description>
<![CDATA[
{description}
]]>
</description>
<link>
{link}
</link>
<enclosure url="{audio_url}" type="audio/mp3" length="{audio_file_size}"/>
<pubDate>{publication_date}</pubDate>
<guid isPermaLink="true">
{link}
</guid>
<itunes:duration>{duration}</itunes:duration>
<itunes:keywords></itunes:keywords>
<media:content url="{audio_url}" type="audio/mp3" fileSize="{audio_file_size}" medium="audio" expression="full" duration="{duration}"/>
<media:group>
<media:description>
{media_description}
</media:description>
</media:group>
</item>"""

    metadata_paths = glob(f"{recordings_dir_path}*.yaml")

    for metadata_path in metadata_paths:
        with open(metadata_path, "r") as fp:
            meta = yaml.load(fp)

        basename = os.path.basename(meta["audio_path"])
        rss_content += rss_item_template.format(title=meta["summary"],
                                                subtitle="",
                                                description="",
                                                publication_date=meta["start_datetime"],
                                                link=f"{zoomerang_url}",
                                                audio_url=f"{zoomerang_url}/recordings/{basename}",
                                                audio_file_size=os.path.getsize(meta["audio_path"]),
                                                duration="{0}:{1}".format(meta.get("duration", 0)/60, meta.get("duration", 0) % 60),
                                                media_description="")

    rss_content += "</channel></rss>"

    with open("/var/www/html/podcast.xml", "w") as fp:
        fp.write(rss_content.strip())

    print("Updated podcast")

