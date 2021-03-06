# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-05-28 18:11
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('bills', '0006_auto_20150709_1016'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='billline',
            options={'get_latest_by': 'id'},
        ),
        migrations.RemoveField(
            model_name='bill',
            name='total',
        ),
        migrations.AlterField(
            model_name='billcontact',
            name='country',
            field=models.CharField(choices=[('LR', 'Liberia'), ('BJ', 'Benin'), ('FM', 'Micronesia (Federated States of)'), ('GS', 'South Georgia and the South Sandwich Islands'), ('AU', 'Australia'), ('PR', 'Puerto Rico'), ('MZ', 'Mozambique'), ('CR', 'Costa Rica'), ('ST', 'Sao Tome and Principe'), ('PL', 'Poland'), ('NG', 'Nigeria'), ('AS', 'American Samoa'), ('LS', 'Lesotho'), ('SG', 'Singapore'), ('BT', 'Bhutan'), ('TG', 'Togo'), ('DM', 'Dominica'), ('GP', 'Guadeloupe'), ('CI', "Côte d'Ivoire"), ('SR', 'Suriname'), ('ZM', 'Zambia'), ('CX', 'Christmas Island'), ('ME', 'Montenegro'), ('TR', 'Turkey'), ('UG', 'Uganda'), ('RU', 'Russian Federation'), ('PG', 'Papua New Guinea'), ('VG', 'Virgin Islands (British)'), ('CW', 'Curaçao'), ('PM', 'Saint Pierre and Miquelon'), ('KP', "Korea (the Democratic People's Republic of)"), ('TJ', 'Tajikistan'), ('FR', 'France'), ('AX', 'Åland Islands'), ('CU', 'Cuba'), ('BA', 'Bosnia and Herzegovina'), ('NA', 'Namibia'), ('MS', 'Montserrat'), ('US', 'United States of America'), ('PS', 'Palestine, State of'), ('MF', 'Saint Martin (French part)'), ('NE', 'Niger'), ('BH', 'Bahrain'), ('CK', 'Cook Islands'), ('JE', 'Jersey'), ('DJ', 'Djibouti'), ('GI', 'Gibraltar'), ('AL', 'Albania'), ('CA', 'Canada'), ('AI', 'Anguilla'), ('GF', 'French Guiana'), ('AW', 'Aruba'), ('PE', 'Peru'), ('SM', 'San Marino'), ('LK', 'Sri Lanka'), ('PN', 'Pitcairn'), ('KM', 'Comoros'), ('ER', 'Eritrea'), ('SK', 'Slovakia'), ('SH', 'Saint Helena, Ascension and Tristan da Cunha'), ('SN', 'Senegal'), ('PW', 'Palau'), ('HT', 'Haiti'), ('MA', 'Morocco'), ('CY', 'Cyprus'), ('GT', 'Guatemala'), ('IT', 'Italy'), ('PY', 'Paraguay'), ('DO', 'Dominican Republic'), ('JO', 'Jordan'), ('AT', 'Austria'), ('NL', 'Netherlands'), ('AM', 'Armenia'), ('BN', 'Brunei Darussalam'), ('BB', 'Barbados'), ('IE', 'Ireland'), ('LB', 'Lebanon'), ('SI', 'Slovenia'), ('TM', 'Turkmenistan'), ('PH', 'Philippines'), ('GE', 'Georgia'), ('BQ', 'Bonaire, Sint Eustatius and Saba'), ('GD', 'Grenada'), ('KI', 'Kiribati'), ('NZ', 'New Zealand'), ('SL', 'Sierra Leone'), ('VN', 'Viet Nam'), ('BZ', 'Belize'), ('TF', 'French Southern Territories'), ('HK', 'Hong Kong'), ('BY', 'Belarus'), ('SD', 'Sudan'), ('UM', 'United States Minor Outlying Islands'), ('ES', 'Spain'), ('GH', 'Ghana'), ('GL', 'Greenland'), ('AD', 'Andorra'), ('ML', 'Mali'), ('NC', 'New Caledonia'), ('IS', 'Iceland'), ('TC', 'Turks and Caicos Islands'), ('FI', 'Finland'), ('DK', 'Denmark'), ('MM', 'Myanmar'), ('MT', 'Malta'), ('TT', 'Trinidad and Tobago'), ('SZ', 'Swaziland'), ('QA', 'Qatar'), ('TN', 'Tunisia'), ('EC', 'Ecuador'), ('CM', 'Cameroon'), ('WF', 'Wallis and Futuna'), ('CO', 'Colombia'), ('MP', 'Northern Mariana Islands'), ('KH', 'Cambodia'), ('MY', 'Malaysia'), ('WS', 'Samoa'), ('NR', 'Nauru'), ('MV', 'Maldives'), ('LI', 'Liechtenstein'), ('BF', 'Burkina Faso'), ('BW', 'Botswana'), ('PF', 'French Polynesia'), ('HM', 'Heard Island and McDonald Islands'), ('SC', 'Seychelles'), ('GU', 'Guam'), ('TZ', 'Tanzania, United Republic of'), ('MQ', 'Martinique'), ('IN', 'India'), ('BE', 'Belgium'), ('SO', 'Somalia'), ('DZ', 'Algeria'), ('AQ', 'Antarctica'), ('TV', 'Tuvalu'), ('GB', 'United Kingdom of Great Britain and Northern Ireland'), ('MC', 'Monaco'), ('KW', 'Kuwait'), ('RO', 'Romania'), ('BL', 'Saint Barthélemy'), ('CV', 'Cabo Verde'), ('BR', 'Brazil'), ('JP', 'Japan'), ('NF', 'Norfolk Island'), ('IO', 'British Indian Ocean Territory'), ('SB', 'Solomon Islands'), ('IM', 'Isle of Man'), ('LC', 'Saint Lucia'), ('ID', 'Indonesia'), ('LA', "Lao People's Democratic Republic"), ('SE', 'Sweden'), ('KG', 'Kyrgyzstan'), ('HN', 'Honduras'), ('KR', 'Korea (the Republic of)'), ('BI', 'Burundi'), ('ZW', 'Zimbabwe'), ('IQ', 'Iraq'), ('SA', 'Saudi Arabia'), ('CN', 'China'), ('NU', 'Niue'), ('GQ', 'Equatorial Guinea'), ('UY', 'Uruguay'), ('LV', 'Latvia'), ('TH', 'Thailand'), ('CC', 'Cocos (Keeling) Islands'), ('EH', 'Western Sahara'), ('PA', 'Panama'), ('GN', 'Guinea'), ('SY', 'Syrian Arab Republic'), ('TK', 'Tokelau'), ('KY', 'Cayman Islands'), ('CD', 'Congo (the Democratic Republic of the)'), ('FO', 'Faroe Islands'), ('KN', 'Saint Kitts and Nevis'), ('EE', 'Estonia'), ('LU', 'Luxembourg'), ('MX', 'Mexico'), ('AF', 'Afghanistan'), ('SV', 'El Salvador'), ('AE', 'United Arab Emirates'), ('BG', 'Bulgaria'), ('BD', 'Bangladesh'), ('IR', 'Iran (Islamic Republic of)'), ('BS', 'Bahamas'), ('TW', 'Taiwan (Province of China)'), ('EG', 'Egypt'), ('GM', 'Gambia'), ('MG', 'Madagascar'), ('OM', 'Oman'), ('IL', 'Israel'), ('FJ', 'Fiji'), ('AG', 'Antigua and Barbuda'), ('LT', 'Lithuania'), ('DE', 'Germany'), ('KE', 'Kenya'), ('BV', 'Bouvet Island'), ('PT', 'Portugal'), ('AZ', 'Azerbaijan'), ('MN', 'Mongolia'), ('RW', 'Rwanda'), ('MR', 'Mauritania'), ('NI', 'Nicaragua'), ('YT', 'Mayotte'), ('SS', 'South Sudan'), ('YE', 'Yemen'), ('GY', 'Guyana'), ('SJ', 'Svalbard and Jan Mayen'), ('MH', 'Marshall Islands'), ('SX', 'Sint Maarten (Dutch part)'), ('GG', 'Guernsey'), ('HR', 'Croatia'), ('VU', 'Vanuatu'), ('MW', 'Malawi'), ('CZ', 'Czech Republic'), ('CH', 'Switzerland'), ('RS', 'Serbia'), ('LY', 'Libya'), ('MO', 'Macao'), ('MK', 'Macedonia (the former Yugoslav Republic of)'), ('HU', 'Hungary'), ('GA', 'Gabon'), ('KZ', 'Kazakhstan'), ('TO', 'Tonga'), ('ET', 'Ethiopia'), ('UZ', 'Uzbekistan'), ('TD', 'Chad'), ('MD', 'Moldova (the Republic of)'), ('BO', 'Bolivia (Plurinational State of)'), ('AO', 'Angola'), ('GW', 'Guinea-Bissau'), ('VA', 'Holy See'), ('VC', 'Saint Vincent and the Grenadines'), ('TL', 'Timor-Leste'), ('VE', 'Venezuela (Bolivarian Republic of)'), ('FK', 'Falkland Islands  [Malvinas]'), ('ZA', 'South Africa'), ('PK', 'Pakistan'), ('CF', 'Central African Republic'), ('NO', 'Norway'), ('CG', 'Congo'), ('UA', 'Ukraine'), ('AR', 'Argentina'), ('CL', 'Chile'), ('VI', 'Virgin Islands (U.S.)'), ('MU', 'Mauritius'), ('JM', 'Jamaica'), ('RE', 'Réunion'), ('GR', 'Greece'), ('NP', 'Nepal'), ('BM', 'Bermuda')], default='ES', max_length=20, verbose_name='country'),
        ),
        migrations.AlterField(
            model_name='billline',
            name='order',
            field=models.ForeignKey(blank=True, help_text='Informative link back to the order', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='lines', to='orders.Order'),
        ),
        migrations.AlterField(
            model_name='billline',
            name='verbose_quantity',
            field=models.CharField(blank=True, max_length=16, verbose_name='Verbose quantity'),
        ),
    ]
