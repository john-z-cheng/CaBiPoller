from django.shortcuts import render
from django.http import Http404, HttpResponse, HttpResponseRedirect

from django.db.models import Max
import pytz
import time

from collections import defaultdict
from stations.models import Station
from stations.models import RefStation
from datetime import datetime
from additional import cabi_status

def create_jurisdiction_data():
	refStationAry = RefStation.objects.all()
	stationToJurisdiction = {}
	for ref in refStationAry:
		stationToJurisdiction[ref.id] = ref.jurisdiction
	return stationToJurisdiction
	
def get_list_per_jurisdiction(stationToJurisdiction, stationList):
	stationsByJurisdiction = defaultdict(list)
	for station in stationList:
		jurisdiction = stationToJurisdiction[station.ref_station.id]
		stationsByJurisdiction[jurisdiction].append(station)
	# convert to list of tuples (jurisdiction, list) ordered by name
	names =  sorted(stationsByJurisdiction.keys())
	jurisList = list()
	for name in names:
		subList = stationsByJurisdiction[name]
		jurisList.append((name, subList))
	return jurisList

def get_duration_string(seconds):
	m, s = divmod(seconds, 60)
	h, m = divmod(m, 60)
	d, h = divmod(h, 24)
	if d == 0:
		return "%02d:%02d" % (h, m)
	else:
		return "%d days %02d:%02d" % (d, h, m)

def assign_duration(nowtime, state_type, stationList):
    for station in stationList:
        if state_type == 'available':
            station.duration = get_duration_string(nowtime - station.available_start)
        if state_type == 'defective':
            station.duration = get_duration_string(nowtime - station.defective_start)
	
def index(request):
	stations = {}
	nowtime = int(time.time())
	stationToJurisdiction = create_jurisdiction_data()
	brokenList = Station.objects.filter(defective_state='unacceptable')
	assign_duration(nowtime, 'defective', brokenList)
	jurisList = get_list_per_jurisdiction(stationToJurisdiction, brokenList)

	stations['broken'] = jurisList
	stations['nobikes'] = Station.objects.filter(available_state='empty')
	assign_duration(nowtime, 'available', stations['nobikes'])
	stations['nodocks'] = Station.objects.filter(available_state='full')
	assign_duration(nowtime, 'available', stations['nodocks'])

	value_dict = Station.objects.all().aggregate(Max('poll_time'))
	timestamp = value_dict['poll_time__max']    
	# convert timestamp to human-readable string
	poll_dt = datetime.utcfromtimestamp(timestamp)
	utc_tz = pytz.timezone('UTC')
	est_tz = pytz.timezone('US/Eastern')
	est_dt = utc_tz.localize(poll_dt).astimezone(est_tz)
	est_dt = est_tz.normalize(est_dt)
	polltime = est_dt.strftime('%Y-%m-%d %H:%M:%S')
	question = 'Answer the question'
	return render(request, 'status/index.html', {
		'stations':stations,'polltime':polltime,'question':question,
	})
	
def station_detail(request, id):
	try:
		station = Station.objects.get(ref_station=id)
		refStation = RefStation.objects.get(id=id)
		station.jurisdiction = refStation.jurisdiction
	except (Station.DoesNotExist, RefStation.DoesNotExist):
		raise Http404('This station does not exist')
	return render(request, 'status/station_detail.html', {
		'station': station
	})
	
def poll(request):
	answer = request.POST['word']
	# execute the cabi_status.py in the additional directory
	cabi_status.run()
	return HttpResponseRedirect('/')