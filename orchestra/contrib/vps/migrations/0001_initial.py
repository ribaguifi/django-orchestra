# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import orchestra.core.validators


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='VPS',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('hostname', models.CharField(max_length=256, unique=True, validators=[orchestra.core.validators.validate_hostname], verbose_name='hostname')),
                ('type', models.CharField(choices=[('openvz', 'OpenVZ container'), ('lxc', 'LXC container')], default='lxc', max_length=64, verbose_name='type')),
                ('template', models.CharField(choices=[('debian7', 'Debian 7 - Wheezy'), ('placeholder', 'LXC placeholder')], default='placeholder', help_text='Initial template.', max_length=64, verbose_name='template')),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='vpss', to=settings.AUTH_USER_MODEL, verbose_name='Account')),
                ('is_active', models.BooleanField(default=True, verbose_name='active')),
            ],
            options={
                'verbose_name': 'VPS',
                'verbose_name_plural': 'VPSs',
            },
        ),
    ]
