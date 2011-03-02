from django.http import HttpResponse
from django.template.loader_tags import BlockNode, ExtendsNode
from django.template import loader, Context, RequestContext

from vcweb.core.decorators import experimenter_required, dajaxice_register
from vcweb.core.models import Experiment

import simplejson

import logging
logger = logging.getLogger(__name__)

def get_template(template):
    if isinstance(template, (tuple, list)):
        return loader.select_template(template)
    return loader.get_template(template)

class BlockNotFound(Exception):
    pass

def render_template_block(template, block, context):
    """
    Renders a single block from a template. This template should have previously been rendered.
    """
    return render_template_block_nodelist(template.nodelist, block, context)

def render_template_block_nodelist(nodelist, block, context):
    for node in nodelist:
        if isinstance(node, BlockNode) and node.name == block:
            return node.render(context)
        for key in ('nodelist', 'nodelist_true', 'nodelist_false'):
            if hasattr(node, key):
                try:
                    return render_template_block_nodelist(getattr(node, key), block, context)
                except:
                    pass
    for node in nodelist:
        if isinstance(node, ExtendsNode):
            try:
                return render_template_block(node.get_parent(context), block, context)
            except BlockNotFound:
                pass
    raise BlockNotFound

def render_block_to_string(template_name, block, dictionary=None, context_instance=None):
    """
    Loads the given template_name and renders the given block with the given dictionary as
    context. Returns a string.
    """
    dictionary = dictionary or {}
    t = get_template(template_name)
    if context_instance:
        context_instance.update(dictionary)
    else:
        context_instance = Context(dictionary)
    t.render(context_instance)
    return render_template_block(t, block, context_instance)

def direct_block_to_template(request, template, block, extra_context=None, mimetype=None, **kwargs):
    """
    Render a given block in a given template with any extra URL parameters in the context as
    ``{{ params }}``.
    """
    if extra_context is None:
        extra_context = {}
    dictionary = {'params': kwargs}
    for key, value in extra_context.items():
        if callable(value):
            dictionary[key] = value()
        else:
            dictionary[key] = value
    c = RequestContext(request, dictionary)
    t = get_template(template)
    t.render(c)
    return HttpResponse(render_template_block(t, block, c), mimetype=mimetype)

def _get_experiment(request, experiment_id):
    experiment = Experiment.objects.get(pk=experiment_id)
    if request.user.experimenter == experiment.experimenter:
        return experiment
    raise Experiment.DoesNotExist("Sorry, %s - you do not have access to experiment %s" % (experiment.experimenter, experiment_id))

def _render_experiment_monitor_block(block, experiment, request):
    return render_block_to_string('monitor.html', block, { 'experiment': experiment },
            context_instance=RequestContext(request))

@experimenter_required
@dajaxice_register
def experiment_controller(request, experiment_id, action=''):
    try:
        experiment = _get_experiment(request, experiment_id)
        experiment_func = getattr(experiment, action.replace('-', '_'), None)
        if experiment_func:
            experiment_func()
        else:
            logger.warning("tried to invoke nonexistent action %s on experiment %s", action, experiment.status_line)
        status_block = _render_experiment_monitor_block('status', experiment, request)
        data_block = _render_experiment_monitor_block('data', experiment, request)
        return simplejson.dumps({
            'status': status_block,
            'experimentData': data_block,
            'active_round_number': experiment.current_round.sequence_number,
            'round_data_count': experiment.round_data.count(),
            })
    except Experiment.DoesNotExist, error:
        return HttpResponse(error)