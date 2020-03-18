# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-06-25 16:13
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('websites', '0003_auto_20170528_2011'),
    ]

    operations = [
        migrations.AlterField(
            model_name='websitedirective',
            name='name',
            field=models.CharField(choices=[(None, '-------'), ('ModSecurity', [('sec-rule-remove', 'SecRuleRemoveById'), ('sec-engine', 'SecRuleEngine Off')]), ('HTTPD', [('redirect', 'Redirection'), ('proxy', 'Proxy'), ('error-document', 'ErrorDocumentRoot')]), ('SSL', [('ssl-ca', 'SSL CA'), ('ssl-cert', 'SSL cert'), ('ssl-key', 'SSL key')]), ('SaaS', [('wordpress-saas', 'WordPress SaaS'), ('dokuwiki-saas', 'DokuWiki SaaS'), ('drupal-saas', 'Drupdal SaaS'), ('moodle-saas', 'Moodle SaaS')])], db_index=True, max_length=128, verbose_name='name'),
        ),
    ]
