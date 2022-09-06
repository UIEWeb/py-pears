import os
import pandas as pd
import py_pears.utils as utils

# remove after creating wrapper for failure email
import smtplib

# Calculate the path to the root directory of this package
ROOT_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), '..'))

EXPORT_DIR = ROOT_DIR + '/pears_exports/'

# Download required PEARS exports from S3
utils.download_s3_exports(profile='pears', org='uie', modules=['Site', 'User'])

# Import input data
sites = pd.read_excel(EXPORT_DIR + "Site_Export.xlsx", sheet_name='Site Data')
users = pd.read_excel(EXPORT_DIR + "User_Export.xlsx", sheet_name='User Data')

# Sites Report

prev_month = (pd.to_datetime("today") - pd.DateOffset(months=1))
report_month_int = prev_month.month
report_year_int = prev_month.year

sites['created'] = pd.to_datetime(sites['created'])
sites['created_month'] = sites['created'].dt.month
sites['created_year'] = sites['created'].dt.year

sites = sites.loc[
    (sites['created_month'] == report_month_int) & (sites['created_year'] == report_year_int),
    ['site_id',
     'site_name',
     'created_by',
     'created_by_email',
     'created',
     'address',
     'city', 'city__county',
     'zip_code',
     'setting']
]

sites = pd.merge(sites, users[['full_name', 'program_area']], how='left', left_on='created_by',
                 right_on='full_name').drop(columns=['full_name'])
sites.insert(5, 'program_area', sites.pop('program_area'))

sites['created'] = sites['created'].dt.strftime('%m-%d-%Y')


# Export the Sites Report as an Excel file

sites_report_filename = 'PEARS Sites Report ' + prev_month.strftime('%Y-%m') + '.xlsx'
out_path = ROOT_DIR + "/reports/outputs/"
sites_report_path = out_path + sites_report_filename

utils.write_report(sites_report_path, ['PEARS Sites Report'], [sites])

# Email Sites Report

# IMPORT the following variables from the credentials file
report_cc = 'list@domain.com, of_recipients@domain.com'
creds = utils.load_credentials()

report_recipients = 'recipient@domain.com'
report_subject = 'PEARS Sites Report ' + prev_month.strftime('%Y-%m')

report_html = """<html>
  <head></head>
<body>
            <p>
            Hello,<br><br>
            Here is the PEARS Sites Report for the previous month.
            SITES ADMIN-
            Would you mind verifying that the correct setting is selected and duplicate sites are merged?
            If you have any questions, please reply to this email and I will respond at my earliest opportunity.<br>
            <br>Best Regards,<br>
            <br> <b> FCS Evaluation Team </b> <br>
            <a href = "mailto: your_username@domain.com ">your_username@domain.com </a><br>
            </p>
  </body>
</html>
"""

utils.send_mail(send_from=creds['admin_send_from'],
                send_to=report_recipients,
                cc=report_cc,
                subject=report_subject,
                html=report_html,
                username=creds['admin_username'],
                password=creds['admin_password'],
                is_tls=True,
                wb=True,
                file_path=sites_report_path,
                filename=sites_report_filename)

# Email Unauthorized Site Creators


# List of PEARS users authorized to create sites
# HOW SHOULD OTHER ORGS DEFINE THIS?
site_creators = ['names', 'of', 'PEARS', 'users']

# Create list of staff to notify
staff_list = sites.loc[~sites['created_by'].isin(site_creators)
                       & sites['created_by_email'].str.contains('|'.join(['illinois.edu', 'uic.edu']), na=False),
                       ['created_by', 'created_by_email']].drop_duplicates(keep='first').values.tolist()

notification_subject = "Friendly REMINDER: Adding new sites to PEARS " + prev_month.strftime('%Y-%m')

# HOW SHOULD OTHER ORGS DEFINE THIS?
notification_cc = 'list@domain.com, of_recipients@domain.com'

notification_html = """
<html>
  <head></head>
<body>
            <p>
            Hello {0},<br>
            <br>You are receiving this email as our records show you have added a new site to the PEARS database within
            the last month. This a friendly reminder that new site additions to PEARS are conducted centrally on campus
            for all Extension program areas. Requests for new sites in PEARS must be sent to
            <a href = "mailto: sites_admin@@domain.com">sites_admin@@domain.com </a> for entry.
            We do this to keep our database clean, accurate, and free of accidental duplicates.<br>
            <br>We ask that field staff not add new sites on their own. A member of the state Evaluation Team is trained
            in the process of adding new sites so that they are usable for staff across all  Extension program areas.
            If the individual in receipt of your request has questions they will reach out to you for clarification.<br>

            <br>Please reply to this email if you have any questions or think you have received this message
            in error.<br>
            <br>Thanks and have a great day!<br>
            <br> <b> FCS Evaluation Team </b> <br>
            <a href = "mailto: your_username@domain.com ">your_username@domain.com </a><br>
  </body>
</html>
"""

# Build the following pattern into a wrapper function?

failed_recipients = []

for x in staff_list:
    staff_name = x[0]
    notification_send_to = x[1]
    user_html = notification_html.format(staff_name)
    # Try to send the email, otherwise add the recipient's email address to failed_recipients
    try:
        utils.send_mail(send_from=creds['admin_send_from'],
                        send_to=notification_send_to,
                        cc=notification_cc,
                        subject=notification_subject,
                        html=user_html,
                        username=creds['admin_username'],
                        password=creds['admin_password'],
                        is_tls=True)
    except smtplib.SMTPException:
        failed_recipients.append(x)

# Build the following pattern into a function?

# Notify admin of any failed attempts to send an email
# Else, print success notification to console
if failed_recipients:
    fail_html = """The following recipients failed to receive an email:<br>
    {}
    """
    new_string = '<br>'.join(map(str, failed_recipients))
    new_html = fail_html.format(new_string)
    fail_subject = 'PEARS Sites Report  ' + prev_month.strftime('%b-%Y') + ' Failure Notice'
    utils.send_mail(send_from=creds['admin_send_from'],
                    send_to='your_username@domain.com',
                    cc='',
                    subject=fail_subject,
                    html=fail_html,
                    username=creds['admin_username'],
                    password=creds['admin_password'],
                    is_tls=True)
else:
    print("Unauthorized site creation notifications sent successfully.")
