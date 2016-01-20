from django.http import HttpResponse
from django.shortcuts import redirect, render
from django_tables2 import RequestConfig
from imghdr import what
from mimetypes import guess_type
from subprocess import Popen
import os

from .charts import campaigns_chart, results_charts, target_bits_chart
from .filters import injection_filter, simics_register_diff_filter
from .models import (campaign, injection, result, simics_memory_diff,
                     simics_register_diff)
from .tables import (campaign_table, campaigns_table, hw_injection_table,
                     result_table, results_table, simics_injection_table,
                     simics_memory_diff_table, simics_register_diff_table)

navigation_items = (('Campaign Information', 'info'),
                    ('Charts (Grouped by Category)', 'category_charts'),
                    ('Charts (Grouped by Outcome)', 'outcome_charts'),
                    ('Results Table', 'results'))


def campaigns_page(request):
    campaign_objects = campaign.objects.all()
    if len(campaign_objects) == 1:
        return redirect('/campaign/'+str(campaign_objects[0].id)+'/results')
    table = campaigns_table(campaign_objects)
    chart_array = campaigns_chart(result.objects.all())
    RequestConfig(request).configure(table)
    return render(request, 'campaigns.html', {'chart_array': chart_array,
                                              'table': table})


def campaign_page(request, campaign_id):
    campaign_data = campaign.objects.get(id=campaign_id)
    chart_array = target_bits_chart(campaign_data)
    page_items = [('Campaign Data', 'campaign_data'),
                  ('Injection Targets', 'target_bits_chart')]
    output_file = ('campaign-data/'+str(campaign_id) +
                   '/gold_'+campaign_data.output_file)
    if os.path.exists(output_file) and what(output_file) is not None:
        output_image = True
        page_items.append(('Output Image', 'output_image'))
    else:
        output_image = False
    page_items.append(('DUT Output', 'dut_output'))
    if campaign_data.use_aux:
        page_items.append(('AUX Output', 'aux_output'))
    page_items.append(('Debugger Output', 'debugger_output'))
    table = campaign_table(campaign.objects.filter(id=campaign_id))
    RequestConfig(request, paginate=False).configure(table)
    return render(request, 'campaign.html', {
        'campaign_data': campaign_data, 'chart_array': chart_array,
        'navigation_items': navigation_items, 'output_image': output_image,
        'page_items': page_items, 'table': table})


def category_charts_page(request, campaign_id):
    return charts_page(request, campaign_id, True)


def outcome_charts_page(request, campaign_id):
    return charts_page(request, campaign_id, False)


def charts_page(request, campaign_id, group_categories):
    campaign_data = campaign.objects.get(id=campaign_id)
    page_items = [('Results Overview', 'overview_chart'),
                  ('Injections By Target', 'targets_charts')]
    if campaign_data.use_simics:
        page_items.append(('Fault Propagation', 'propagation_chart'))
    page_items.extend([('Data Diff By Target', 'diff_targets_chart'),
                       ('Injections By Register', 'registers_chart'),
                       ('Injections By Bit', 'bits_chart')])
    if campaign_data.use_simics:
        page_items.extend([('Injections By TLB Entry', 'tlbs_chart'),
                          ('Injections By TLB Field', 'tlb_fields_chart')])
    page_items.extend([('Injections Over Time', 'times_charts'),
                       ('Results By Injection Count', 'counts_charts')])
    filter_ = injection_filter(request.GET, queryset=injection.objects.filter(
        result__campaign_id=campaign_id), campaign=campaign_id)
    if filter_.qs.count() > 0:
        chart_array = results_charts(filter_.qs, campaign_data,
                                     group_categories)
    else:
        chart_array = None
    return render(request, 'charts.html', {
        'campaign_data': campaign_data, 'chart_array': chart_array,
        'filter': filter_, 'navigation_items': navigation_items,
        'page_items': page_items})


def results_page(request, campaign_id):
    campaign_data = campaign.objects.get(id=campaign_id)
    injection_objects = injection.objects.filter(
        result__campaign_id=campaign_id)
    if len(injection_objects) == 0:
        return redirect('/campaign/'+str(campaign_id)+'/info')
    filter_ = injection_filter(request.GET, queryset=injection_objects,
                               campaign=campaign_id)
    result_ids = filter_.qs.values('result_id').distinct()
    result_objects = result.objects.filter(id__in=result_ids)
    if request.method == 'POST':
        if 'delete' in request.POST and 'select_box' in request.POST:
            result_ids = [int(result_id) for result_id
                          in dict(request.POST)['select_box']]
            injection.objects.filter(result_id__in=result_ids).delete()
            simics_memory_diff.objects.filter(result_id__in=result_ids).delete()
            simics_register_diff.objects.filter(
                result_id__in=result_ids).delete()
            result.objects.filter(id__in=result_ids).delete()
        elif 'delete_all' in request.POST:
            injection.objects.filter(result_id__in=result_ids).delete()
            simics_memory_diff.objects.filter(result_id__in=result_ids).delete()
            simics_register_diff.objects.filter(
                result_id__in=result_ids).delete()
            result.objects.filter(id__in=result_ids).delete()
            return redirect('/campaign/'+str(campaign_id)+'/results')
        elif (('view_output' in request.POST or
               'view_output_image' in request.POST) and
              'select_box' in request.POST):
            result_ids = []
            page_items = []
            for result_id in dict(request.POST)['select_box']:
                result_ids.append(int(result_id))
                page_items.append(('Result ID '+result_id, result_id))
            results = result.objects.filter(id__in=result_ids)
            image = 'view_output_image' in request.POST
            return render(request, 'output.html', {'campaign': campaign_id,
                                                   'image': image,
                                                   'navigation_items':
                                                       navigation_items,
                                                   'page_items': page_items,
                                                   'results': results})
        elif ('view_output_all' in request.POST or
              'view_output_image_all' in request.POST):
            page_items = [('Result ID '+str(result_id), result_id) for result_id
                          in result_objects.values_list('id', flat=True)]
            image = 'view_output_image_all' in request.POST
            return render(request, 'output.html', {'campaign': campaign_id,
                                                   'image': image,
                                                   'navigation_items':
                                                       navigation_items,
                                                   'page_items': page_items,
                                                   'results': result_objects})
        elif 'new_outcome_category' in request.POST:
            result_objects.values('outcome_category').update(
                outcome_category=request.POST['new_outcome_category'])
        elif 'new_outcome' in request.POST:
            result_objects.values('outcome').update(
                outcome=request.POST['new_outcome'])
        elif 'refresh' in request.POST:
            return redirect('/campaign/'+str(campaign_id)+'/results')
    table = results_table(result_objects)
    RequestConfig(request, paginate={'per_page': 100}).configure(table)
    return render(request, 'results.html', {
        'campaign_data': campaign_data, 'filter': filter_,
        'navigation_items': navigation_items, 'table': table})


def result_page(request, campaign_id, result_id):
    campaign_data = campaign.objects.get(id=campaign_id)
    navigation_items_ = [(item[0], '../'+item[1])
                         for item in navigation_items]
    page_items = [('Result', 'result'), ('Injections', 'injections')]
    output_file = ('campaign-data/'+campaign_id+'/results/'+result_id +
                   '/'+campaign_data.output_file)
    if os.path.exists(output_file) and what(output_file) is not None:
        output_image = True
        page_items.append(('Output Image', 'output_image'))
    else:
        output_image = False
    page_items.append(('DUT Output', 'dut_output'))
    if campaign_data.use_aux:
        page_items.append(('AUX Output', 'aux_output'))
    page_items.append(('Debugger Output', 'debugger_output'))
    if campaign_data.use_simics:
        page_items.extend([('Register Diffs', 'register_diffs'),
                           ('Memory Diffs', 'memory_diffs')])
    result_object = result.objects.get(id=result_id)
    table = result_table(result.objects.filter(id=result_id))
    if request.method == 'GET' and 'launch' in request.GET:
        drseus = 'drseus.py'
        if not os.path.exists(drseus):
            drseus = 'drseus.sh'
        Popen(['./'+drseus, 'regenerate', result_id])
    if request.method == 'POST' and 'save' in request.POST:
        result_object.outcome = request.POST['outcome']
        result_object.outcome_category = request.POST['outcome_category']
        result_object.save()
    elif request.method == 'POST' and 'delete' in request.POST:
        injection.objects.filter(result_id=result_object.id).delete()
        simics_register_diff.objects.filter(result_id=result_object.id).delete()
        simics_memory_diff.objects.filter(result_id=result_object.id).delete()
        result_object.delete()
        return HttpResponse('Result deleted.')
    injection_objects = injection.objects.filter(result_id=result_id)
    if campaign_data.use_simics:
        injection_table = simics_injection_table(injection_objects)
        register_objects = simics_register_diff.objects.filter(
            result_id=result_id)
        register_filter = simics_register_diff_filter(
            request.GET, queryset=register_objects, campaign=campaign_id)
        register_table = simics_register_diff_table(register_filter.qs)
        RequestConfig(request,
                      paginate={'per_page': 25}).configure(register_table)
        memory_objects = simics_memory_diff.objects.filter(result_id=result_id)
        memory_table = simics_memory_diff_table(memory_objects)
        RequestConfig(request,
                      paginate={'per_page': 25}).configure(memory_table)
    else:
        register_filter = None
        memory_table = None
        register_table = None
        injection_table = hw_injection_table(injection_objects)
    RequestConfig(request, paginate=False).configure(table)
    RequestConfig(request, paginate=False).configure(injection_table)
    return render(request, 'result.html', {
        'campaign_data': campaign_data, 'filter': register_filter,
        'injection_table': injection_table, 'memory_table': memory_table,
        'navigation_items': navigation_items_, 'output_image': output_image,
        'page_items': page_items, 'register_table': register_table,
        'result': result_object, 'table': table})


def output(request, campaign_id, result_id):
    campaign_data = campaign.objects.get(id=campaign_id)
    if result_id == '0':
        output_file = ('campaign-data/'+campaign_id+'/'
                       'gold_'+campaign_data.output_file)
    else:
        output_file = ('campaign-data/'+campaign_id+'/results/' +
                       result_id+'/'+campaign_data.output_file)
    if os.path.exists(output_file):
        return HttpResponse(open(output_file, 'rb').read(),
                            content_type=guess_type(output_file))
    else:
        return HttpResponse()
