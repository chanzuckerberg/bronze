from bronze.libs.google.docs import spreadsheet as ss
from bronze.libs import alarm as bronze_alarm
import pendulum


def get_slack_mapping(name):
    try:
        slack_id = slack_user_mapping[name].tag
    except KeyError:
        slack_id = None
    return slack_id


# Create and initialize the alarm from the YAML file
oncall_reminder = bronze_alarm.Alarm(alarm='alarm.yml')

# Load the spreadsheet
spreadsheet_url = oncall_reminder.sheet_target
spreadsheet = ss.SpreadSheetReader(oncall_reminder.creds_target, spreadsheet_url)

# Construct the name -> SlackID mapping
slack_user_mapping = bronze_alarm.get_slack_mapping(
    spreadsheet=spreadsheet, remove_header=True
)

# Get the date of "today", which is the date of the script invocation time
invocation_date = pendulum.today(tz="America/Los_Angeles")
print(f"The current invocation date is {invocation_date}")

# Look for tomorrow
period_start_datetime = invocation_date.add(hours=10)
period_end_datetime = period_start_datetime.subtract(seconds=1)

invocation_date_str = invocation_date.format("MMM D, YYYY")

# Figure out which target date in the rotation the invocation day matches
print(f"Looking for exact matches of {invocation_date_str} in the rotation sheet...")
target_dates_df = spreadsheet.sheetToDataFrame(
    sheet_name='Rotation', sheet_range='A1:C1000', has_header=True
)
target = target_dates_df.loc[target_dates_df['Start Date'] == invocation_date_str]

# Extract and validate the date and coordinator for composing the messages
date = bronze_alarm.load_cell_from_row(column_name='Start Date', row=target)
primary = bronze_alarm.load_cell_from_row(column_name='Primary', row=target)
secondary = bronze_alarm.load_cell_from_row(column_name='Secondary', row=target)

primary_slack_id = get_slack_mapping(primary)
secondary_slack_id = get_slack_mapping(secondary)

# Compose the message while respecting the "skip" flags
if not primary and not secondary:
    msg = "There's nobody scheduled for on-call tomorrow! Please update the <rotation spreadsheet|https://docs.google.com/spreadsheets/d/13PC0kkNcXMC4_7UJRgjQ6cEXxl5D58mxJD20mAMGImo/edit#gid=1508723546>"
else:
    msg = oncall_reminder.message
    msg = msg.format(
        **{
            "primary": primary_slack_id,
            "secondary": secondary_slack_id,
            "start_datetime": period_start_datetime.to_iso8601_string(),
            "end_datetime": period_end_datetime.to_iso8601_string()
        }
    )

# Send out the message
oncall_reminder.send_msg(msg=msg)
