from django.http import HttpResponse
from django.shortcuts import redirect, render
from django_tables2 import RequestConfig
from imghdr import what
from mimetypes import guess_type
from os.path import exists
from subprocess import Popen

from log import filters
from log import models
from log import tables
from log.charts.json import (campaigns_chart, injections_charts, results_charts,
                             target_bits_chart)

navigation_items = (('All Campaigns', '/', 'campaigns', 'flag'),
                    ('All Results', '/results', 'results', 'list'),
                    ('All Events', '/events', 'events', 'calendar'),
                    ('All Injections', '/injections', 'injections',
                     'crosshairs'),
                    ('All Charts', '/category_charts', 'charts', 'bar-chart'))

campaign_items = (('Campaign Information', 'info', 'info', 'info'),
                  ('Campaign Results', 'results', 'results', 'list'),
                  ('Campaign Events', 'events', 'events', 'calendar'),
                  ('Campaign Injections', 'injections', 'injections',
                   'crosshairs'),
                  ('Campaign Charts', 'category_charts', 'charts', 'bar-chart'))

table_length = 50


def campaigns_page(request):
    campaign = models.campaign.objects.all()
    campaign_table = tables.campaigns(campaign)
    chart_data = campaigns_chart(models.result.objects.all())
    RequestConfig(request).configure(campaign_table)
    return render(request, 'campaigns.html', {
        'campaign_table': campaign_table,
        'chart_data': chart_data,
        'navigation_items': navigation_items})


def campaign_page(request, campaign_id):
    campaign = models.campaign.objects.get(id=campaign_id)
    chart_data = target_bits_chart(campaign)
    output_file = ('campaign-data/'+str(campaign_id) +
                   '/gold_'+campaign.output_file)
    output_image = exists(output_file) and what(output_file) is not None
    campaign_table = tables.campaign(models.campaign.objects.filter(
        id=campaign_id))
    event_table = tables.event(models.event.objects.filter(
        campaign_id=campaign_id))
    RequestConfig(request, paginate=False).configure(campaign_table)
    RequestConfig(request, paginate=False).configure(event_table)
    return render(request, 'campaign.html', {
        'campaign': campaign,
        'campaign_items': campaign_items,
        'campaign_table': campaign_table,
        'chart_data': chart_data,
        'event_table': event_table,
        'navigation_items': navigation_items,
        'output_image': output_image})


def category_charts_page(request, campaign_id=None):
    return charts_page(request, campaign_id, True)


def charts_page(request, campaign_id=None, group_categories=False):
    if campaign_id is not None:
        campaign = models.campaign.objects.get(id=campaign_id)
        campaign_items_ = campaign_items
        results = models.result.objects.filter(campaign_id=campaign_id)
    else:
        campaign = None
        campaign_items_ = None
        results = models.result.objects.all()
    result_filter = filters.result(request.GET, queryset=results)
    error_title = None
    error_message = None
    if not result_filter.qs.count() and results.count():
        error_title = 'Filter Error'
        error_message = 'Filter did not return any results and was ignored.'
        result_filter = filters.result(None, queryset=results)
    else:
        results = result_filter.qs
    if results.count() > 0:
        chart_data, chart_list = results_charts(results, group_categories)
        chart_list = sorted(chart_list, key=lambda x: x['order'])
    else:
        chart_data = None
        chart_list = None
    return render(request, 'charts.html', {
        'campaign': campaign,
        'campaign_items': campaign_items_,
        'categories': group_categories,
        'chart_data': chart_data,
        'chart_list': chart_list,
        'error_message': error_message,
        'error_title': error_title,
        'filter': result_filter,
        'filter_tabs': True,
        'navigation_items': navigation_items})


def events_page(request, campaign_id=None):
    if campaign_id is not None:
        campaign = models.campaign.objects.get(id=campaign_id)
        campaign_items_ = campaign_items
        events = models.event.objects.filter(result__campaign_id=campaign_id)
    else:
        campaign = None
        campaign_items_ = None
        events = models.event.objects.all()
    event_filter = filters.event(request.GET, queryset=events)
    error_title = None
    error_message = None
    if not event_filter.qs.count() and events.count():
        error_title = 'Filter Error'
        error_message = 'Filter did not return any events and was ignored.'
        event_filter = filters.event(None, queryset=events)
    else:
        events = event_filter.qs
    event_table = tables.events(events)
    RequestConfig(
        request, paginate={'per_page': table_length}).configure(event_table)
    return render(request, 'events.html', {
        'campaign': campaign,
        'campaign_items': campaign_items_,
        'error_message': error_message,
        'error_title': error_title,
        'event_count': '{:,}'.format(events.count()),
        'event_table': event_table,
        'filter': event_filter,
        'navigation_items': navigation_items})


def injections_page(request, campaign_id=None):
    if campaign_id is not None:
        campaign = models.campaign.objects.get(id=campaign_id)
        campaign_items_ = campaign_items
        injections = models.injection.objects.filter(
            result__campaign_id=campaign_id)
    else:
        campaign = None
        campaign_items_ = None
        injections = models.injection.objects.all()
    injection_filter = filters.injection(request.GET, queryset=injections)
    error_title = None
    error_message = None
    if not injection_filter.qs.count() and injections.count():
        error_title = 'Filter Error'
        error_message = 'Filter did not return any injections and was ignored.'
        injection_filter = filters.injection(None, queryset=injections)
    else:
        injections = injection_filter.qs
    injections = injection_filter.qs
    if injections.count() > 0:
        chart_data, chart_list = injections_charts(injections)
        chart_list = sorted(chart_list, key=lambda x: x['order'])
    else:
        chart_data = None
        chart_list = None
    injection_table = tables.injections(injections)
    RequestConfig(
        request, paginate={'per_page': table_length}).configure(injection_table)
    return render(request, 'injections.html', {
        'campaign': campaign,
        'campaign_items': campaign_items_,
        'chart_data': chart_data,
        'chart_list': chart_list,
        'error_message': error_message,
        'error_title': error_title,
        'filter': injection_filter,
        'injection_count': '{:,}'.format(injections.count()),
        'injection_table': injection_table,
        'navigation_items': navigation_items})


def results_page(request, campaign_id=None):
    if campaign_id is not None:
        campaign = models.campaign.objects.get(id=campaign_id)
        campaign_items_ = campaign_items
        output_file = ('campaign-data/'+campaign_id+'/gold_' +
                       campaign.output_file)
        if exists(output_file) and what(output_file) is not None:
            output_image = True
        else:
            output_image = False
        results = models.result.objects.filter(campaign_id=campaign_id)
    else:
        campaign = None
        campaign_items_ = None
        output_image = True
        results = models.result.objects.all()
    result_filter = filters.result(request.GET, queryset=results)
    error_title = None
    error_message = None
    if not result_filter.qs.count() and results.count():
        error_title = 'Filter Error'
        error_message = 'Filter did not return any results and was ignored.'
        result_filter = filters.result(None, queryset=results)
    else:
        results = result_filter.qs
    if request.method == 'GET':
        if (('view_output' in request.GET or
                'view_output_image' in request.GET) and
                'select_box' in request.GET):
            result_ids = map(int, dict(request.GET)['select_box'])
            results = models.result.objects.filter(
                id__in=result_ids).order_by('-id')
            image = 'view_output_image' in request.GET
            if image:
                result_ids = []
                for result in results:
                    if exists(
                        'campaign-data/'+str(result.campaign_id)+'/results/' +
                            str(result.id)+'/'+result.campaign.output_file):
                        result_ids.append(result.id)
                results = models.result.objects.filter(
                    id__in=result_ids).order_by('-id')
            if results.count():
                return render(request, 'output.html', {
                    'campaign': campaign,
                    'campaign_items': campaign_items if campaign else None,
                    'image': image,
                    'navigation_items': navigation_items,
                    'results': results})
            else:
                results = result_filter.qs
        elif ('view_output_all' in request.GET or
              'view_output_image_all' in request.GET):
            image = 'view_output_image_all' in request.GET
            if image:
                result_ids = []
                for result in results:
                    if exists(
                        'campaign-data/'+str(result.campaign_id)+'/results/' +
                            str(result.id)+'/'+result.campaign.output_file):
                        result_ids.append(result.id)
            else:
                result_ids = results.values_list('id', flat=True)
            results = models.result.objects.filter(
                id__in=result_ids).order_by('-id')
            if results.count():
                return render(request, 'output.html', {
                    'campaign': campaign,
                    'campaign_items': campaign_items if campaign else None,
                    'image': image,
                    'navigation_items': navigation_items,
                    'results': results})
            else:
                results = result_filter.qs
    elif request.method == 'POST':
        if 'new_outcome_category' in request.POST:
            results.values('outcome_category').update(
                outcome_category=request.POST['new_outcome_category'])
        elif 'new_outcome' in request.POST:
            results.values('outcome').update(
                outcome=request.POST['new_outcome'])
        elif 'delete' in request.POST and 'results[]' in request.POST:
            result_ids = [int(result_id) for result_id
                          in dict(request.POST)['results[]']]
            models.event.objects.filter(result_id__in=result_ids).delete()
            models.injection.objects.filter(result_id__in=result_ids).delete()
            models.simics_memory_diff.objects.filter(
                result_id__in=result_ids).delete()
            models.simics_register_diff.objects.filter(
                result_id__in=result_ids).delete()
            models.result.objects.filter(id__in=result_ids).delete()
        elif 'delete_all' in request.POST:
            result_ids = results.values('id')
            models.event.objects.filter(result_id__in=result_ids).delete()
            models.injection.objects.filter(result_id__in=result_ids).delete()
            models.simics_memory_diff.objects.filter(
                result_id__in=result_ids).delete()
            models.simics_register_diff.objects.filter(
                result_id__in=result_ids).delete()
            results.delete()
            if campaign_id:
                return redirect('/campaign/'+campaign_id+'/results')
            else:
                return redirect('/results')
    result_table = tables.results(results)
    RequestConfig(
        request, paginate={'per_page': table_length}).configure(result_table)
    return render(request, 'results.html', {
        'campaign': campaign,
        'campaign_items': campaign_items_,
        'error_message': error_message,
        'error_title': error_title,
        'filter': result_filter,
        'filter_tabs': True,
        'navigation_items': navigation_items,
        'output_image': output_image,
        'result_count': '{:,}'.format(results.count()),
        'result_table': result_table})


def result_page(request, result_id):
    result = models.result.objects.get(id=result_id)
    campaign_items_ = [
        (item[0], '/campaign/'+str(result.campaign_id)+'/'+item[1], item[2],
         item[3]) for item in campaign_items]
    output_file = ('campaign-data/'+str(result.campaign_id)+'/results/' +
                   result_id+'/'+result.campaign.output_file)
    output_image = exists(output_file) and what(output_file) is not None
    result_table = tables.result(models.result.objects.filter(id=result_id))
    event_table = tables.event(models.event.objects.filter(result_id=result_id))
    if request.method == 'POST' and 'launch' in request.POST:
        drseus = 'drseus.py'
        if not exists(drseus):
            drseus = 'drseus.sh'
        Popen(['./'+drseus, 'regenerate', result_id])
    if request.method == 'POST' and 'save' in request.POST:
        result.outcome = request.POST['outcome']
        result.outcome_category = request.POST['outcome_category']
        result.save()
    elif request.method == 'POST' and 'delete' in request.POST:
        models.event.objects.filter(result_id=result.id).delete()
        models.injection.objects.filter(result_id=result.id).delete()
        models.simics_register_diff.objects.filter(result_id=result.id).delete()
        models.simics_memory_diff.objects.filter(result_id=result.id).delete()
        result.delete()
        return redirect('/campaign/'+str(result.campaign_id)+'/results')
    injections = models.injection.objects.filter(result_id=result_id)
    if result.campaign.simics:
        injection_table = tables.simics_injection(injections)
        register_diffs = models.simics_register_diff.objects.filter(
            result_id=result_id)
        register_filter = filters.simics_register_diff(
            request.GET, queryset=register_diffs)
        register_table = tables.simics_register_diff(register_filter.qs)
        RequestConfig(
            request,
            paginate={'per_page': table_length}).configure(register_table)
        memory_diffs = models.simics_memory_diff.objects.filter(
            result_id=result_id)
        memory_table = tables.simics_memory_diff(memory_diffs)
        RequestConfig(
            request,
            paginate={'per_page': table_length}).configure(memory_table)
    else:
        register_filter = None
        memory_table = None
        register_table = None
        injection_table = tables.hw_injection(injections)
    RequestConfig(request, paginate=False).configure(result_table)
    RequestConfig(request, paginate=False).configure(event_table)
    RequestConfig(request, paginate=False).configure(injection_table)
    return render(request, 'result.html', {
        'campaign_items': campaign_items_,
        'event_table': event_table,
        'filter': register_filter,
        'injection_table': injection_table,
        'memory_table': memory_table,
        'navigation_items': navigation_items,
        'output_image': output_image,
        'register_table': register_table,
        'result': result,
        'result_table': result_table})


def output(request, result_id=None, campaign_id=None):
    if result_id is not None:
        result = models.result.objects.get(id=result_id)
        output_file = ('campaign-data/'+str(result.campaign_id)+'/results/' +
                       result_id+'/'+result.campaign.output_file)
    elif campaign_id is not None:
        campaign = models.campaign.objects.get(id=campaign_id)
        output_file = ('campaign-data/'+campaign_id+'/gold_' +
                       campaign.output_file)
    if exists(output_file):
        return HttpResponse(open(output_file, 'rb').read(),
                            content_type=guess_type(output_file))
    else:
        return HttpResponse()