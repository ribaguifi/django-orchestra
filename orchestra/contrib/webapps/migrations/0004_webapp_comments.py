# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2020-02-04 11:17
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('webapps', '0003_webapp_target_server'),
    ]

    operations = [
        migrations.AddField(
            model_name='webapp',
            name='comments',
            field=models.TextField(default=''),
            preserve_default=False,
        ),
    ]
