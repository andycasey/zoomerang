zoomerang
=========

Because my sleep is important and Australia's time zone *sucks*.

Scheduler
---------

The Scheduler looks through my Google Calendar for upcoming Zoom meetings that I want Zoomerang to record,
and schedules a `cron` job to record the meeting. It's a good idea to run the Scheduler at 23:59 on Sundays.
The following `cron` job will do that for you:

``59 23 * * 6 python scheduler.py``


Zoomerang
---------

The Zoomerang script does the following:

1. Calls in and records a specified Zoom meeting.

2. Downloads the audio MP3 of that Zoom meeting.

3. Updates the `meetings.yaml` file with information about the recorded meeting.

4. Updates the `meetings.xml` file, which is a RSS Podcast feed that my phone checks daily for updates.
