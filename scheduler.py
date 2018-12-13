
import os
import pwd
import grp
import datetime

from googleapiclient.discovery import build
from oauth2client import file, client, tools
from httplib2 import Http


def get_calendar():
    
    dir_path = os.path.dirname(os.path.realpath(__file__))

    store = file.Storage(os.path.join(dir_path, "token.json"))
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets(
            os.path.join(dir_path, "credentials.json"),
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


def format_cron_job(zoomerang_event, user=None):

    if user is None:
        user = pwd.getpwuid(os.getuid())[0]

    dir_path = os.path.dirname(os.path.realpath(__file__))

    start_datetime = zoomerang_events[0]["start"]["dateTime"]
    start_datetime = ":".join(start_datetime.split(":")[:-1]) \
                   + start_datetime[-2:]
    args = " ".join(zoomerang_event["location"].split()[1:])
    summary = zoomerang_event.get("summary", "").replace('"', '')

    st = datetime.datetime.strptime(start_datetime, "%Y-%m-%dT%H:%M:%S%z")

    return f"{st.minute} {st.hour} {st.day} {st.month} * {user} "\
           f"python {dir_path}/zoomerang.py {args} \"{summary}\" "\
           f">> {dir_path}/zoomerang.log 2>&1"


def format_cron_jobs(zoomerang_events, environment_variables=("SHELL", "PATH")):

    cron_prefix = "\n".join([f"{ev.upper()}={os.environ.get(ev)}" \
                             for ev in environment_variables])

    cron_jobs = [format_cron_job(ev) for ev in zoomerang_events]

    return cron_prefix + "\n\n" + "\n".join(cron_jobs) + "\n\n"


if __name__ == '__main__':

    zoomerang_events = find_upcoming_zoomerang_events(get_calendar())

    content = format_cron_jobs(zoomerang_events)

    #/etc/cron.d/zoomerang
    cron_path = "/etc/cron.d/zoomerang"
    with open(cron_path, "w") as fp:
        fp.write(content)

    # Ensure correct permissions, etc.
    os.chmod(cron_path, 600)
    os.chown(cron_path, pwd.getpwnam("root").pw_uid, grp.getgrnam("root").gr_gid)

    # Ensure cron jobs will run.
    os.system(f"touch {os.path.dirname(cron_path)}")
    os.system("sudo service cron restart")

