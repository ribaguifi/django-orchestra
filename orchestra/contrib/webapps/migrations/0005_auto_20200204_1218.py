# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2020-02-04 11:18
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('webapps', '0004_webapp_comments'),
    ]

    operations = [
        migrations.AlterField(
            model_name='webapp',
            name='comments',
            field=models.TextField(default=''),
        ),
    ]
