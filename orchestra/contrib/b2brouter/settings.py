from orchestra.contrib.settings import Setting

B2BROUTER_API_KEY = Setting(
    "B2BROUTER_API_KEY",
    "",
    help_text="API Key for B2B Router integration.",
    # TODO(@slamora): seems that validation doesn't work
    validators=[Setting.validate_non_empty_string],
)

B2BROUTER_API_URL = Setting(
    "B2BROUTER_API_URL",
    "https://api-staging.b2brouter.net",
    help_text="Base URL for B2B Router API.",
)

B2BROUTER_ACCOUNT_ID = Setting(
    "B2BROUTER_ACCOUNT_ID",
    "",
    help_text="Account ID for B2B Router integration.",
    # TODO(@slamora): seems that validation doesn't work
    validators=[Setting.validate_integer],
)
