from django.shortcuts import render
from django.http import Http404, HttpResponse, HttpResponseRedirect

from django.db.models import F
import pytz

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
		jurisdiction = stationToJurisdiction[station.id]
		stationsByJurisdiction[jurisdiction].append(station)
	# convert to list of tuples (jurisdiction, list) ordered by name
	names =  sorted(stationsByJurisdiction.keys())
	jurisList = list()
	for name in names:
		subList = stationsByJurisdiction[name]
		jurisList.append((name, subList))
	return jurisList
	
def index(request):
	stations = {}
	stationToJurisdiction = create_jurisdiction_data()
	brokenList = Station.objects.filter(curr_total__lt=F('max_total'))
	# add attribute for difference
	for broken in brokenList:
		broken.difference = broken.max_total - broken.curr_total
		broken.place = 'Blue '
	jurisList = get_list_per_jurisdiction(stationToJurisdiction, brokenList)

	stations['broken'] = jurisList
	stations['nobikes'] = Station.objects.filter(bikes=0)
	stations['nodocks'] = Station.objects.filter(docks=0)
	timestamp = Station.objects.get(id=31000).poll_time
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
		station = Station.objects.get(id=id)
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