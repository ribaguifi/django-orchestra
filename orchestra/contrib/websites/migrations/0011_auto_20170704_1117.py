# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-07-04 09:17
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('orchestration', '0007_auto_20170528_2011'),
        ('websites', '0010_auto_20170625_2214'),
    ]

    operations = [
        migrations.AddField(
            model_name='website',
            name='target_server',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='websites', to='orchestration.Server', verbose_name='Target Server'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='websitedirective',
            name='name',
            field=models.CharField(choices=[(None, '-------'), ('ModSecurity', [('sec-rule-remove', 'SecRuleRemoveById'), ('sec-engine', 'SecRuleEngine Off')]), ('SaaS', [('wordpress-saas', 'WordPress SaaS'), ('dokuwiki-saas', 'DokuWiki SaaS'), ('drupal-saas', 'Drupdal SaaS'), ('moodle-saas', 'Moodle SaaS')]), ('HTTPD', [('redirect', 'Redirection'), ('proxy', 'Proxy'), ('error-document', 'ErrorDocumentRoot')]), ('SSL', [('ssl-ca', 'SSL CA'), ('ssl-cert', 'SSL cert'), ('ssl-key', 'SSL key')])], db_index=True, max_length=128, verbose_name='name'),
        ),
    ]
