# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-05-28 18:11
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('websites', '0002_auto_20160219_1036'),
    ]

    operations = [
        migrations.AlterField(
            model_name='websitedirective',
            name='name',
            field=models.CharField(choices=[(None, '-------'), ('SaaS', [('wordpress-saas', 'WordPress SaaS'), ('dokuwiki-saas', 'DokuWiki SaaS'), ('drupal-saas', 'Drupdal SaaS'), ('moodle-saas', 'Moodle SaaS')]), ('ModSecurity', [('sec-rule-remove', 'SecRuleRemoveById'), ('sec-engine', 'SecRuleEngine Off')]), ('SSL', [('ssl-ca', 'SSL CA'), ('ssl-cert', 'SSL cert'), ('ssl-key', 'SSL key')]), ('HTTPD', [('redirect', 'Redirection'), ('proxy', 'Proxy'), ('error-document', 'ErrorDocumentRoot')])], db_index=True, max_length=128, verbose_name='name'),
        ),
        migrations.AlterField(
            model_name='websitedirective',
            name='value',
            field=models.CharField(blank=True, max_length=256, verbose_name='value'),
        ),
    ]