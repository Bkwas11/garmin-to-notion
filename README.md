[![Sync Garmin to Notion](https://github.com/chloevoyer/garmin-to-notion/actions/workflows/sync_garmin_to_notion.yml/badge.svg?branch=main)](https://github.com/chloevoyer/garmin-to-notion/actions/workflows/sync_garmin_to_notion.yml)
# Garmin to Notion Integration :watch:

This project connects your Garmin activities and personal records to your Notion database, allowing you to keep track of your performance metrics in one place.

> [!IMPORTANT]
> **Existing users:** Garmin tightened their authentication in March 2025, breaking the previous email/password login flow. You will need to sync your fork with the latest changes and migrate to the new token-based authentication. See [README_AUTH_SETUP.md](README_AUTH_SETUP.md) for instructions. Your `GARMIN_EMAIL` and `GARMIN_PASSWORD` secrets can be removed once done.

## Features :sparkles:  
  🔄  Automatically sync Garmin activities to Notion in real-time  
  📊  Track detailed activity metrics, with distances in miles and running pace in min/mi
  🎯  Extract and track personal records (fastest 1K, longest ride)  
  👣  Optional daily steps tracker
  😴  Optional sleep data tracker  
  📅  Optional monthly training calendar with planned mileage, Garmin workouts, completion, and weekly totals
  🏋️  Optional strength log with completed exercises, sets, reps, weight, and volume
  🤖  Zero-touch automation once configured  
  📱  Compatible with all Garmin activities and devices  
  🔧  Easy setup with clear instructions and minimal coding required  

## Prerequisites :hammer_and_wrench:  
- A Notion account with API access.
- A Garmin Connect account to pull activity data.
- If you wish to sync your Peloton workouts with Garmin, see [peloton-to-garmin](https://github.com/philosowaffle/peloton-to-garmin)
## Getting Started :dart:
A detailed step-by-step guide is provided on my Notion template [here](https://chloevoyer.notion.site/Set-up-Guide-17915ce7058880559a3ac9f8a0720046).
For more advanced users, follow these steps to set up the integration:
### 1. Fork this GitHub Repository
### 2. Duplicate my [Notion Template](https://www.notion.so/templates/fitness-tracker-738)
* Save your Activities and Personal Records database ID (you will need it for step 4)
  * Optional: Daily Steps database ID
  * Look at the URL: notion.so/username/[string-of-characters]
  * The database ID is everything after your “username/“ and before the “?v”
### 3. Create Notion Token
* Go to [Notion Integrations](https://www.notion.so/profile/integrations).
* [Create](https://developers.notion.com/docs/create-a-notion-integration) a new integration and copy the integration token.
* [Share](https://www.notion.so/help/add-and-manage-connections-with-the-api#enterprise-connection-settings) the integration with the target database in Notion.

### 4. Generate a Garmin Authentication Token
* Follow the instructions in [README_AUTH_SETUP.md](README_AUTH_SETUP.md) to generate and configure your `GARMIN_AUTH_TOKEN`.

### 5. Set Environment Secrets
* Environment secrets to define:
  * GARMIN_AUTH_TOKEN (see step 4)
  * NOTION_TOKEN
  * NOTION_DB_ID
  * NOTION_PR_DB_ID
  * NOTION_STEPS_DB_ID (optional)
  * NOTION_SLEEP_DB_ID (optional)
  * NOTION_CALENDAR_DB_ID (optional; see Training Calendar below)
  * NOTION_STRENGTH_DB_ID (optional; see Strength Log below)
### 6. Run Scripts (if not using automatic workflow)
* Run [garmin-activities.py](https://github.com/chloevoyer/garmin-to-notion/blob/main/garmin-activities.py) to sync your Garmin activities to Notion.  
`python garmin-activities.py`
* Run [person-records.py](https://github.com/chloevoyer/garmin-to-notion/blob/main/personal-records.py) to extract activity records (e.g., fastest run, longest ride).  
`python personal-records.py` 

## Training Calendar

The Training Calendar on the main Notion dashboard creates one row for every day of the current month. You can enter **Miles Planned** directly in Notion. Each sync then:

- imports workouts assigned to dates on your Garmin Connect calendar;
- labels planned and completed running distance as **Miles Planned** and **Miles Run**;
- places an automatic ☐/☑ directly beside each planned workout;
- adds a checkmark and strikethrough when the full day's plan is complete; and
- repeats the planned and actual weekly mileage totals on every day in that week.
- shows a red sleep status below 7 hours, yellow for 7–7.99 hours, and green for 8 or more hours; and
- adds a compact mileage, run-goal, strength, and sleep summary to the final visible day of each week.

Create a separate Notion database and add these properties with the exact names and types shown:

| Property | Notion type |
| --- | --- |
| Day | Title |
| Date | Date |
| Miles Planned | Number |
| Miles Run | Number |
| Workout Planned | Text with automatic ☐/☑ |
| Completed Activities | Text |
| Complete | Checkbox |
| Week | Text |
| Weekly Planned Miles | Number |
| Weekly Actual Miles | Number |
| Sleep Hours | Number |
| Sleep Status | Select: 🟢 8+ hours, 🟡 7+ hours, 🔴 Under 7 hours |
| Weekly Run Goals Met | Number |
| Weekly Run Goals Planned | Number |
| Weekly Strength Completed | Number |
| Weekly Strength Planned | Number |
| Weekly Avg Sleep | Number |
| Weekly Sleep Goals Met | Number |
| Weekly Summary | Text |

Then share the database with your Notion integration, save its data-source ID as the GitHub Actions secret `NOTION_CALENDAR_DB_ID`, and add a Notion **Calendar view** using the `Date` property to the main dashboard. Show `Miles Planned`, `Miles Run`, `Workout Planned`, `Sleep Hours`, `Sleep Status`, and `Weekly Summary` on calendar cards.

The first run fills the current month. After you edit Miles Planned, the next daily run refreshes completion and weekly totals. Activity distances, daily-step distances, longest-run records, longest-ride records, and pace are written in miles. To convert older activity values already stored in Notion, manually run the workflow once with `GARMIN_ACTIVITIES_FETCH_LIMIT` set high enough to include those activities (up to 1000).

## Strength Log

The optional Strength Log imports each completed, non-rest set from Garmin strength activities. It records the workout and exercise names, date, set number and type, reps, weight in pounds, per-set volume, and duration. A stable set key prevents duplicate rows and lets later Garmin corrections update the existing Notion row.

Create a separate Notion database with these properties: `Set` (Title), `Date` (Date), `Workout` (Text), `Exercise` (Text), `Set Number` (Number), `Set Type` (Select with Active, Warmup, Drop Set, Failure, and Other), `Reps` (Number), `Weight (lb)` (Number), `Volume (lb)` (Number), `Duration (sec)` (Number), `Activity ID` (Text), and `Set Key` (Text). Share it with the Notion integration and save its data-source ID as `NOTION_STRENGTH_DB_ID`.

The sync checks the most recent Garmin activities. Set `GARMIN_STRENGTH_FETCH_LIMIT` higher for the first run if you want to import older strength sessions; when omitted, it uses `GARMIN_ACTIVITIES_FETCH_LIMIT`.
## Example Configuration :pencil:  
You can customize the scripts to fit your needs by modifying environment variables and Notion database settings.  

Here is a screenshot of what my Notion dashboard looks like:  
![garmin-to-notion-template](https://github.com/user-attachments/assets/b37077cc-fe87-466f-9424-8ba9e4efa909)


My Notion template is available for free and can be duplicated to your Notion [here](https://www.notion.so/templates/fitness-tracker-738)

## Acknowledgements :raised_hands:  
- Reference dictionary and examples can be found in [cyberjunky/python-garminconnect](https://github.com/cyberjunky/python-garminconnect.git).
- This project was inspired by [n-kratz/garmin-notion](https://github.com/n-kratz/garmin-notion.git).
## Contributing :handshake:   
Contributions are welcome! If you find a bug or want to add a feature, feel free to open an issue or submit a pull request. Financial contributions are also greatly appreciated :blush:    

<a href="https://www.buymeacoffee.com/cvoyer" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/default-orange.png" alt="Buy Me A Coffee" height="41" width="174"></a>   

## :copyright: License  
This project is licensed under the MIT License. See the LICENSE file for more details.
