# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-05-28 18:11
from __future__ import unicode_literals

from django.db import migrations, models
import orchestra.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('systemusers', '0002_auto_20150429_1413'),
    ]

    operations = [
        migrations.AlterField(
            model_name='systemuser',
            name='shell',
            field=models.CharField(choices=[('/dev/null', 'No shell, FTP only'), ('/bin/rssh', 'No shell, SFTP/RSYNC only'), ('/usr/bin/git-shell', 'No shell, GIT only'), ('/bin/bash', '/bin/bash')], default='/dev/null', max_length=32, verbose_name='shell'),
        ),
        migrations.AlterField(
            model_name='systemuser',
            name='username',
            field=models.CharField(help_text='Required. 32 characters or fewer. Letters, digits and ./-/_ only.', max_length=32, unique=True, validators=[orchestra.core.validators.validate_username], verbose_name='username'),
        ),
    ]