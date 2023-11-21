from django.middleware.csrf import rotate_token
from django.utils.crypto import constant_time_compare

SESSION_KEY_TOKEN = '_auth_token'
SESSION_KEY_USERNAME = '_auth_username'


def login(request, username, token):
    """
    Persist a user id and a backend in the request. This way a user doesn't
    have to reauthenticate on every request. Note that data set during
    the anonymous session is retained when the user logs in.
    """
    if SESSION_KEY_TOKEN in request.session:
        if request.session[SESSION_KEY_USERNAME] != username:
            # To avoid reusing another user's session, create a new, empty
            # session if the existing session corresponds to a different
            # authenticated user.
            request.session.flush()
    else:
        request.session.cycle_key()

    request.session[SESSION_KEY_TOKEN] = token
    request.session[SESSION_KEY_USERNAME] = username
    # if hasattr(request, 'user'):
    #     request.user = user
    rotate_token(request)


def logout(request):
    """
    Remove the authenticated user's ID from the request and flush their session
    data.
    """
    request.session.flush()
    # if hasattr(request, 'user'):
    #     from django.contrib.auth.models import AnonymousUser
    #     request.user = AnonymousUser()
