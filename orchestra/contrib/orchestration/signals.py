import django.dispatch

pre_action = django.dispatch.Signal()

post_action = django.dispatch.Signal()

pre_prepare = django.dispatch.Signal()

post_prepare = django.dispatch.Signal()

pre_commit = django.dispatch.Signal()

post_commit = django.dispatch.Signal()

