
import datetime

from googleapiclient.discovery import build
from oauth2client import file, client, tools
from httplib2 import Http


def get_calendar():
    
    store = file.Storage('token.json')
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets(
            'credentials.json', 
            'https://www.googleapis.com/auth/calendar.readonly')
        creds = tools.run_flow(flow, store)
    return build('calendar', 'v3', http=creds.authorize(Http()))


def find_upcoming_zoomerang_events(calendar, days_ahead=7):
    now = datetime.datetime.utcnow()
    time_min = now.isoformat() + "Z"
    time_max = (now + datetime.timedelta(days=days_ahead)).isoformat() + "Z"

    results = calendar.events().list(calendarId="primary", 
                                     timeMin=time_min,
                                     timeMax=time_max, 
                                     maxResults=100,
                                     singleEvents=True,
                                     orderBy="startTime").execute()
    events = results.get("items", [])

    zoomerang_events = []
    for event in events:
        if event.get("location", "").lower().startswith("zoomerang"):
            zoomerang_events.append(event)

    return zoomerang_events


def format_cron_job(zoomerang_event):

    start_datetime = zoomerang_events[0]["start"]["dateTime"]
    start_datetime = ":".join(start_datetime.split(":")[:-1]) \
                   + start_datetime[-2:]
    args = zoomerang_event["location"].split()[1:]
    summary = zoomerang_event.get("summary", "").replace('"', '')

    st = datetime.datetime.strptime(start_datetime, "%Y-%m-%dT%H:%M:%S%z")

    return f"{st.minute} {st.hour} {st.day} {st.month} * "\
           f"python /home/ubuntu/zoomerang/zoomerang.py {args} \"{summary}\" "\
           f">> /home/ubuntu/zoomerang/zoomerang.log 2>&1"



if __name__ == '__main__':

    zoomerang_events = find_upcoming_zoomerang_events(get_calendar())
    cron_prefix = "SHELL=/bin/sh\nPATH=/home/ubuntu/miniconda3/bin:/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin\n"

    cron_jobs = "\n".join([format_cron_job(e) for e in zoomerang_events]) + "\n"

    #/etc/cron.d/zoomerang
    with open("/etc/cron.d/zoomerang", "w") as fp:
        fp.write(cron_prefix + cron_jobs)

