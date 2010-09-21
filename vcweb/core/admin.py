'''
registering django models with django admin
'''

from django.contrib import admin
from django.contrib.auth.models import Permission
from vcweb.core.models import DataParameter, RoundParameter, \
    ConfigurationParameter, ExperimentConfiguration, RoundConfiguration, \
    Experimenter, Participant, Group, Experiment, ParticipantExperimentRelationship, \
    ParticipantGroupRelationship


admin.site.register(DataParameter)
admin.site.register(RoundParameter)
admin.site.register(ConfigurationParameter)
admin.site.register(ExperimentConfiguration)
admin.site.register(RoundConfiguration)
admin.site.register(Experimenter)
admin.site.register(Participant)
admin.site.register(Group)
admin.site.register(Experiment)
admin.site.register(ParticipantExperimentRelationship)
admin.site.register(ParticipantGroupRelationship)
admin.site.register(Permission)
