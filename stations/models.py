# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey has `on_delete` set to the desired behavior.
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from __future__ import unicode_literals

from django.db import models

class RefStation(models.Model):
    id = models.IntegerField(primary_key=True, blank=True, null=False)
    
    name = models.TextField(blank=True, null=True)
    dock_qty = models.IntegerField(blank=True, null=True)
    lat = models.FloatField(blank=True, null=True)
    lon = models.FloatField(blank=True, null=True)
    elevation = models.FloatField(blank=True, null=True)
    jurisdiction = models.TextField(blank=True, null=True)
    is_active = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'ref_stations'

class Station(models.Model):
    ref_station = models.OneToOneField (RefStation, primary_key=True, db_column='station_id')
    bikes = models.IntegerField(blank=True, null=True)
    docks = models.IntegerField(blank=True, null=True)
    inactives = models.IntegerField(blank=True, null=True)
    available_state = models.TextField(blank=True, null=True)
    defective_state = models.TextField(blank=True, null=True)
    poll_time = models.IntegerField(blank=True, null=True)
    available_start = models.IntegerField(blank=True, null=True)
    defective_start = models.IntegerField(blank=True, null=True)
    lc = models.IntegerField(blank=True, null=True)
    lu = models.IntegerField(blank=True, null=True)
    

    class Meta:
        managed = True
        db_table = 'curr_stations'
        
class CountEvent(models.Model):
    id = models.IntegerField(primary_key=True, blank=True, null=False)
    # Django will name column as station_id for this ForeignKey
    station = models.ForeignKey(RefStation, blank=False, null=False, on_delete=models.PROTECT)

    state_type = models.TextField(blank=True, null=True)
    bikes = models.IntegerField(blank=True, null=True)
    docks = models.IntegerField(blank=True, null=True)
    inactives = models.IntegerField(blank=True, null=True)
    poll_time = models.IntegerField(blank=True, null=True)
    lu = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'count_history'
        
class StateEvent(models.Model):
    id = models.IntegerField(primary_key=True, blank=True, null=False)
    # Django will name column as station_id for this ForeignKey
    station = models.ForeignKey(RefStation, blank=False, null=False, on_delete=models.PROTECT)
    change_time = models.IntegerField(blank=True, null=True)
    state_type = models.TextField(blank=True, null=True)
    old_state = models.TextField(blank=True, null=True)
    new_state = models.TextField(blank=True, null=True)
    
    class Meta:
        managed = True
        db_table = 'state_history'
