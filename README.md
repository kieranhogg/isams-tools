iSAMS Tools
===========

This software is a group of modules that work with, or provide addition functionality, for iSAMS (http://isams.co.uk). See each module for its documentation.

Register Reminder
-----------------

Sends emails to tutors who have not registered all students.

**Requirements**

* iSAMS
    * either a database user, or a Batch API key set up (see below)
* Docker
* E-mail server

Installation
=============

1. If you don't have access to iSAMS database (cloud install), you will need to use the API. If you wish to use the database directly, set CONNECTION_METHOD to 'MSSQL' in settings.py and skip to step 5
1. `iSAMS > Control Panel > API Services Manager > Manage Batch API Keys > Request Batch API Key`
1. API Key mode must be set to 'Development' (note: this causes data to be pulled directly from the DB, so be wary of executing too frequently)
1. Once you have a new API key, edit the Batch methods to include those in the *iSAMS Batch Method Requirements* section
1. Edit `settings_example.py` and rename it to `settings.py`
1. Build with docker: `docker build -t isams_tools/v1 .`
1. Run with docker: `docker run isams-tools/v1 register_reminder --args 1`
1. Add entries to crontab, as shown below (for Windows you will probably need AT: https://support.microsoft.com/en-us/kb/313565)

**iSAMS API Setup**

In your Batch API methods, you need to enable the following:

* HRManager:CurrentStaff
* PupilManager:CurrentPupils
* RegistrationManager:RegistrationStatuses
* SchoolManager:Forms

**Example Crontab**

```bash
# runs the first reminder at 8am Monday-Friday
0 8 * * 1-5 docker run isams_tools/v1 register_reminder --args 1 >/dev/null 2>&1 

# runs the second reminder at 8:30am Monday-Friday
30 8 * * 1-5 docker run isams_tools/v1 register_reminder --args 2 >/dev/null 2>&1 

# runs the final reminder at 8:45am Monday-Friday
45 8 * * 1-5 docker run isams_tools/v1 register_reminder --args 3 >/dev/null 2>&1
```
