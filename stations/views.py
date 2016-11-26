from django.shortcuts import render
from django.http import Http404, HttpResponse, HttpResponseRedirect

from django.db.models import F
from stations.models import Station
from datetime import datetime
from additional import cabi_status

def index(request):
	stations = {}
	stations['broken'] = Station.objects.filter(curr_total__lt=F('max_total'))
	stations['nobikes'] = Station.objects.filter(bikes=0)
	stations['nodocks'] = Station.objects.filter(docks=0)
	timestamp = Station.objects.get(id=31000).poll_time
	# convert timestamp to human-readable string
	poll_dt = datetime.fromtimestamp(timestamp)
	polltime = poll_dt.strftime('%Y-%m-%d %H:%M:%S')
	question = 'Answer the question'
	return render(request, 'status/index.html', {
		'stations':stations,'polltime':polltime,'question':question,
	})
	
def station_detail(request, id):
	try:
		station = Station.objects.get(id=id)
	except Station.DoesNotExist:
		raise Http404('This station does not exist')
	return render(request, 'status/station_detail.html', {
		'station': station
	})
	
def poll(request):
	answer = request.POST['word']
	# execute the cabi_status.py in the additional directory
	cabi_status.run()
	return HttpResponseRedirect('/')