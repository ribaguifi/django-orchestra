# SaaS - Software as a Service


This app provides support for services that follow the SaaS model. Traditionaly known as multi-site or multi-tenant web applications where a single installation of a CMS provides accounts for multiple isolated tenants.


## Service declaration

Each service is defined by a `SoftwareService` subclass, you can find examples on the [`services` module](services).

The minimal service declaration will be:

```python
class DrupalService(SoftwareService):
    name = 'drupal'
    verbose_name = "Drupal"
    icon = 'orchestra/icons/apps/Drupal.png'
    site_domain = settings.SAAS_MOODLE_DOMAIN
```

Additional attributes can be used to further customize the service class to your needs.

### Custom forms
If the service needs to keep track of additional information you should provide an extra form and serializer. For example, wordpress requires you to provide an email_address during account creation, and the assigned blog ID is required for effectively update account state or delete it. In this case we provide two forms:

```python
class WordPressForm(SaaSBaseForm):
    email = forms.EmailField(label=_("Email"),
        help_text=_("A new user will be created if the above email address is not in the database.<br>"
                    "The username and password will be mailed to this email address."))

class WordPressChangeForm(WordPressForm):
    blog_id = forms.IntegerField(label=("Blog ID"), widget=widgets.SpanWidget, required=False,
        help_text=_("ID of this blog used by WordPress, the only attribute that doesn't change."))
```

WordPressForm provides the email field, and WordPressChangeForm adds the `blog_id` on top of it. `blog_id` will be represented as a *readonly* field on the form, so no modification will be allowed.

### Serializer for extra data

Additionally, we should provide a serializer in order to save the form extra pices of information into the database (into field *data*).

```python
class WordPressDataSerializer(serializers.Serializer):
    email = serializers.EmailField(label=_("Email"))
    blog_id = serializers.IntegerField(label=_("Blog ID"), allow_null=True, required=False)
```

Now we have everything needed for declaring the WordPress service.

```python
class WordPressService(SoftwareService):
    name = 'wordpress'
    verbose_name = "WordPress"
    form = WordPressForm
    change_form = WordPressChangeForm
    serializer = WordPressDataSerializer
    icon = 'orchestra/icons/apps/WordPress.png'
    change_readonly_fields = ('email', 'blog_id')
    site_domain = settings.SAAS_WORDPRESS_DOMAIN
    allow_custom_url = settings.SAAS_WORDPRESS_ALLOW_CUSTOM_URL
```

Notice that two optional forms can be provices `form` and `change_form`. When non of them is provided, SaaS will provide a default one for you. When only `form` is provided, it will be used for both, *add view* and *change view*. If both are provided, `form` will be used for the *add view* and `change_form` for the change view. This last option allows us to display the `blog_id` back to the user, only when we have it (after creation).

`change_readonly_fields` is a tuple with the name of the fields that can not be edditied once the service has been created.


## Backend


A backend class is required to interface with the web application and perform `save()` and `delete()` operations on it. The more reliable way of interfacing with the application is by means of a CLI (e.g. [Moodle](backends/moodle.py), but not all CMS come with this tool. The second preferable way is using some sort of API, possibly HTTP-based (e.g. [gitLab](backends/gitlab.py). This is less realiable because additional moving parts are used underneeth the interface; a busy web server can timeout our requests. The least prefered way is interfacing with an HTTP-HTML interface designed for human consumption, really paintful to implement but sometimes is the only way (e.g. [WordPress](backends/wordpressmu.py)).

Some applications do not support multi-tenancy by default, but we can hack the configuration file of such apps and generate *table prefix* or *database name* based on some property of the URL. Example of this services are [moodle](backends/moodle.py) and [phplist](backends/phplist.py) respectively.


## Settings

Enabled services should be added into the `SAAS_ENABLED_SERVICES` settings tuple, providing its full module path, e.g. `'orchestra.contrib.saas.services.moodle.MoodleService'`. Parameters that should allow easy configuration on each deployment should be defined as settings. e.g. `SAAS_WORDPRESS_DOMAIN`. Take a look at the [`settings` module](settings.py).