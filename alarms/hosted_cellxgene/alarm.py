from bronze.libs.google.docs import spreadsheet as ss
from bronze.libs import alarm as bronze_alarm
import pendulum


def oncall_period(start_date):
    return start_date.add(hours=10), start_date.add(days=7, hours=10).subtract(seconds=1)


def get_rotation(df, date):
    def get_slack_mapping(name):
        try:
            slack_id = slack_user_mapping[name].tag
        except KeyError:
            slack_id = None
        return slack_id

    rotation = df.loc[df['Start Date'] == date.format("MMM D, YYYY")]

    # Extract and validate the date and coordinator for composing the messages
    primary = bronze_alarm.load_cell_from_row(column_name='Primary', row=rotation)
    secondary = bronze_alarm.load_cell_from_row(column_name='Secondary', row=rotation)
    primary_slack_id = get_slack_mapping(primary)
    secondary_slack_id = get_slack_mapping(secondary)
    return primary_slack_id, secondary_slack_id


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
current_rotation_date = pendulum.today(tz="America/Los_Angeles")
next_rotation_date = current_rotation_date.add(days=7)
print(f"The current rotation date is {current_rotation_date}")
print(f"The next rotation date is {next_rotation_date}")


# Look for tomorrow
current_start_datetime, current_end_datetime = oncall_period(current_rotation_date)
next_start_datetime, next_end_datetime = oncall_period(next_rotation_date)

# Figure out which target date in the rotation the invocation day matches
target_dates_df = spreadsheet.sheetToDataFrame(
    sheet_name='Rotation', sheet_range='A1:C1000', has_header=True
)


current_primary_slack_id, current_secondary_slack_id = get_rotation(target_dates_df, current_rotation_date)
next_primary_slack_id, next_secondary_slack_id = get_rotation(target_dates_df, next_rotation_date)


# Compose the message while respecting the "skip" flags
if any(ele is None for ele in [current_primary_slack_id, current_secondary_slack_id, next_primary_slack_id, next_secondary_slack_id]):
    msg = "There are people missing in the on-call rotation spreadsheet! Please update the <rotation spreadsheet|https://docs.google.com/spreadsheets/d/13PC0kkNcXMC4_7UJRgjQ6cEXxl5D58mxJD20mAMGImo/edit#gid=1508723546>"
else:
    msg = oncall_reminder.message
    msg = msg.format(
        **{
            "current_primary": current_primary_slack_id,
            "current_secondary": current_secondary_slack_id,
            "next_primary": next_primary_slack_id,
            "next_secondary": next_secondary_slack_id,
            "current_start_datetime": current_start_datetime.to_iso8601_string(),
            "current_end_datetime": current_end_datetime.to_iso8601_string(),
            "next_start_datetime": next_start_datetime.to_iso8601_string(),
            "next_end_datetime": next_end_datetime.to_iso8601_string()
        }
    )

# Send out the message
oncall_reminder.send_msg(msg=msg)
