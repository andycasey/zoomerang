zoomerang
=========

Zoomerang looks through your Google Calendar for upcoming telecons that you
want to record. Then it posts the recording to a private podcast that your 
device is subscribed to. 

Why? Because sleep is important and Australia's time zone *sucks*.


Part I: The Scheduler
---------------------

The Scheduler (`scheduler.py`) looks through my Google Calendar for upcoming 
meetings that I want to record (by setting 'Zoomerang `<MEETING_ID>`' as the 
location), then schedules a `cron` job to record that meeting.

It's a good idea to run the Scheduler each half hour to catch last minute
meeting invitations. There's a script in `scripts/zoomerangscheduler` that
will do that:

````
cp scripts/zoomerangscheduler /etc/cron.d/
chmod 600 /etc/cron.d/zoomerangscheduler
chown root:root /etc/cron.d/zoomerangscheduler
touch /etc/cron.d/
sudo service cron restart
````


Part II: Zoomerang
------------------

Zoomerang (`zoomerang.py`) actually does the work. It will record a specified 
meeting (e.g., a Zoom or regular teleconference call), and then post the 
recording to a private Podcast that my phone checks daily for updates.


Recording options
-----------------

Your meeting doesn't have to be run through Zoom. It could be a regular telecon
with some meeting ID number. To specify a non-Zoom meeting, you can give the
conference phone number in your Calendar location:

- Zoomerang `<MEETING_ID>` --phone-number `[PHONE_NUMBER]`

Any international number is allowed as long as you specify it in a sensible 
format. You can also specify how long you expect the meeting to run (in minutes):

- Zoomerang `<MEETING_ID>` --duration 30

The default is 60 minutes. 