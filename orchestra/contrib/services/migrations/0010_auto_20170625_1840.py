# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-06-25 16:40
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0009_auto_20170625_1840'),
    ]

    operations = [
        migrations.AlterField(
            model_name='service',
            name='rate_algorithm',
            field=models.CharField(choices=[('orchestra.contrib.plans.ratings.best_price', 'Best price'), ('orchestra.contrib.plans.ratings.match_price', 'Match price'), ('orchestra.contrib.plans.ratings.step_price', 'Step price')], default='orchestra.contrib.plans.ratings.step_price', help_text='Algorithm used to interprete the rating table.<br>&nbsp;&nbsp;Best price: Produces the best possible price given all active rating lines (those with quantity lower or equal to the metric).<br>&nbsp;&nbsp;Match price: Only <b>the rate</b> with a) inmediate inferior metric and b) lower price is applied. Nominal price will be used when initial block is missing.<br>&nbsp;&nbsp;Step price: All rates with a quantity lower or equal than the metric are applied. Nominal price will be used when initial block is missing.', max_length=64, verbose_name='rate algorithm'),
        ),
    ]
