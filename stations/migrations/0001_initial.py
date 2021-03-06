# -*- coding: utf-8 -*-
# Generated by Django 1.10.3 on 2016-12-04 17:33
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='CountEvent',
            fields=[
                ('id', models.IntegerField(blank=True, primary_key=True, serialize=False)),
                ('state_type', models.TextField(blank=True, null=True)),
                ('bikes', models.IntegerField(blank=True, null=True)),
                ('docks', models.IntegerField(blank=True, null=True)),
                ('inactives', models.IntegerField(blank=True, null=True)),
                ('poll_time', models.IntegerField(blank=True, null=True)),
                ('lu', models.IntegerField(blank=True, null=True)),
            ],
            options={
                'db_table': 'count_history',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='RefStation',
            fields=[
                ('id', models.IntegerField(blank=True, primary_key=True, serialize=False)),
                ('name', models.TextField(blank=True, null=True)),
                ('dock_qty', models.IntegerField(blank=True, null=True)),
                ('lat', models.FloatField(blank=True, null=True)),
                ('lon', models.FloatField(blank=True, null=True)),
                ('elevation', models.FloatField(blank=True, null=True)),
                ('jurisdiction', models.TextField(blank=True, null=True)),
                ('is_active', models.IntegerField(blank=True, null=True)),
            ],
            options={
                'db_table': 'ref_stations',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='StateEvent',
            fields=[
                ('id', models.IntegerField(blank=True, primary_key=True, serialize=False)),
                ('change_time', models.IntegerField(blank=True, null=True)),
                ('state_type', models.TextField(blank=True, null=True)),
                ('old_state', models.TextField(blank=True, null=True)),
                ('new_state', models.TextField(blank=True, null=True)),
            ],
            options={
                'db_table': 'state_history',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='Station',
            fields=[
                ('ref_station', models.OneToOneField(db_column='station_id', on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to='stations.RefStation')),
                ('bikes', models.IntegerField(blank=True, null=True)),
                ('docks', models.IntegerField(blank=True, null=True)),
                ('inactives', models.IntegerField(blank=True, null=True)),
                ('available_state', models.TextField(blank=True, null=True)),
                ('defective_state', models.TextField(blank=True, null=True)),
                ('poll_time', models.IntegerField(blank=True, null=True)),
                ('lc', models.IntegerField(blank=True, null=True)),
                ('lu', models.IntegerField(blank=True, null=True)),
            ],
            options={
                'db_table': 'curr_stations',
                'managed': True,
            },
        ),
        migrations.AddField(
            model_name='stateevent',
            name='station',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='stations.RefStation'),
        ),
        migrations.AddField(
            model_name='countevent',
            name='station',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='stations.RefStation'),
        ),
    ]
