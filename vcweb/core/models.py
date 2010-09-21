from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.db import models, transaction
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _
from string import Template
from vcweb import settings
import base64
import datetime
import hashlib
import logging
import random
import re
import signals

SHA1_RE = re.compile('^[a-f0-9]{40}$')

logger = logging.getLogger('vcweb.core.models')

"""
Contains all data models used in the core as well as a number of helper functions.  
Is getting pretty big / unwieldy.  Should probably refactor and split into smaller pieces.
"""

"""
tick handlers.

handles each second tick.  Might rethink this and use timed / delayed tasks in celery execute at the end of each round for 
controlled experiments and for longer-scale experiments use 1 minute granularity for performance sake.
"""
def second_tick_handler(sender, time=None, **kwargs):
    logger.debug("handling second tick signal at %s" % time)
    # inspect all active experiments and update their time left
    Experiment.objects.increment_elapsed_time(status='ROUND_IN_PROGRESS')

signals.second_tick.connect(second_tick_handler, sender=None)

# FIXME: separate accounts / registration / experimenter / participant app from the core app
# registration manager included / forked from http://bitbucket.org/ubernostrum/django-registration/
class RegistrationManager(models.Manager):
    """
    Custom manager for the ``RegistrationProfile`` model.
    
    The methods defined here provide shortcuts for account creation
    and activation (including generation and emailing of activation
    keys), and for cleaning out expired inactive accounts.
    
    """
    def activate_user(self, activation_key):
        """
        Validate an activation key and activate the corresponding
        ``User`` if valid.
        
        If the key is valid and has not expired, return the ``User``
        after activating.
        
        If the key is not valid or has expired, return ``False``.
        
        If the key is valid but the ``User`` is already active,
        return ``False``.
        
        To prevent reactivation of an account which has been
        deactivated by site administrators, the activation key is
        reset to the string constant ``RegistrationProfile.ACTIVATED``
        after successful activation.

        """
        # Make sure the key we're trying conforms to the pattern of a
        # SHA1 hash; if it doesn't, no point trying to look it up in
        # the database.
        if SHA1_RE.search(activation_key):
            try:
                profile = self.get(activation_key=activation_key)
            except self.model.DoesNotExist:
                return False
            if not profile.activation_key_expired():
                user = profile.user
                user.is_active = True
                user.save()
                profile.activation_key = self.model.ACTIVATED
                profile.save()
                return user
        return False

    def create_inactive_user(self, username, email, password,
                             site, send_email=True):
        """
        Create a new, inactive ``User``, generate a
        ``RegistrationProfile`` and email its activation key to the
        ``User``, returning the new ``User``.

        By default, an activation email will be sent to the new
        user. To disable this, pass ``send_email=False``.
        
        """
        new_user = User.objects.create_user(username, email, password)
        new_user.is_active = False
        new_user.save()

        registration_profile = self.create_profile(new_user)

        if send_email:
            registration_profile.send_activation_email(site)

        return new_user
    create_inactive_user = transaction.commit_on_success(create_inactive_user)

    def create_profile(self, user):
        """
        Create a ``RegistrationProfile`` for a given
        ``User``, and return the ``RegistrationProfile``.
        
        The activation key for the ``RegistrationProfile`` will be a
        SHA1 hash, generated from a combination of the ``User``'s
        username and a random salt.
        
        """

        salt = hashlib.sha1(str(random.random())).hexdigest()[:5]
        activation_key = hashlib.sha1(salt + user.username).hexdigest()
        return self.create(user=user,
                           activation_key=activation_key)

    def delete_expired_users(self):
        """
        Remove expired instances of ``RegistrationProfile`` and their
        associated ``User``s.
        
        Accounts to be deleted are identified by searching for
        instances of ``RegistrationProfile`` with expired activation
        keys, and then checking to see if their associated ``User``
        instances have the field ``is_active`` set to ``False``; any
        ``User`` who is both inactive and has an expired activation
        key will be deleted.
        
        It is recommended that this method be executed regularly as
        part of your routine site maintenance; this application
        provides a custom management command which will call this
        method, accessible as ``manage.py cleanupregistration``.
        
        Regularly clearing out accounts which have never been
        activated serves two useful purposes:
        
        1. It alleviates the ocasional need to reset a
           ``RegistrationProfile`` and/or re-send an activation email
           when a user does not receive or does not act upon the
           initial activation email; since the account will be
           deleted, the user will be able to simply re-register and
           receive a new activation key.
        
        2. It prevents the possibility of a malicious user registering
           one or more accounts and never activating them (thus
           denying the use of those usernames to anyone else); since
           those accounts will be deleted, the usernames will become
           available for use again.
        
        If you have a troublesome ``User`` and wish to disable their
        account while keeping it in the database, simply delete the
        associated ``RegistrationProfile``; an inactive ``User`` which
        does not have an associated ``RegistrationProfile`` will not
        be deleted.
        
        """
        for profile in self.all():
            if profile.activation_key_expired():
                user = profile.user
                if not user.is_active:
                    user.delete()


class RegistrationProfile(models.Model):
    """
    A simple profile which stores an activation key for use during
    user account registration.
    
    Generally, you will not want to interact directly with instances
    of this model; the provided manager includes methods
    for creating and activating new accounts, as well as for cleaning
    out accounts which have never been activated.
    
    While it is possible to use this model as the value of the
    ``AUTH_PROFILE_MODULE`` setting, it's not recommended that you do
    so. This model's sole purpose is to store data temporarily during
    account registration and activation.
    
    """
    ACTIVATED = u"ALREADY_ACTIVATED"

    user = models.ForeignKey(User, unique=True, verbose_name=_('user'))
    activation_key = models.CharField(_('activation key'), max_length=40)

    objects = RegistrationManager()

    class Meta:
        verbose_name = _('registration profile')
        verbose_name_plural = _('registration profiles')

    def __unicode__(self):
        return u"Registration information for %s" % self.user

    def activation_key_expired(self):
        """
        Determine whether this ``RegistrationProfile``'s activation
        key has expired, returning a boolean -- ``True`` if the key
        has expired.
        
        Key expiration is determined by a two-step process:
        
        1. If the user has already activated, the key will have been
           reset to the string constant ``ACTIVATED``. Re-activating
           is not permitted, and so this method returns ``True`` in
           this case.

        2. Otherwise, the date the user signed up is incremented by
           the number of days specified in the setting
           ``ACCOUNT_ACTIVATION_DAYS`` (which should be the number of
           days after signup during which a user is allowed to
           activate their account); if the result is less than or
           equal to the current date, the key has expired and this
           method returns ``True``.
        
        """
        expiration_date = datetime.timedelta(days=settings.ACCOUNT_ACTIVATION_DAYS)
        return self.activation_key == self.ACTIVATED or \
               (self.user.date_joined + expiration_date <= datetime.datetime.now())
    activation_key_expired.boolean = True

    def send_activation_email(self, site):
        """
        Send an activation email to the user associated with this
        ``RegistrationProfile``.
        
        The activation email will make use of two templates:

        ``registration/activation_email_subject.txt``
            This template will be used for the subject line of the
            email. Because it is used as the subject line of an email,
            this template's output **must** be only a single line of
            text; output longer than one line will be forcibly joined
            into only a single line.

        ``registration/activation_email.txt``
            This template will be used for the body of the email.

        These templates will each receive the following context
        variables:

        ``activation_key``
            The activation key for the new account.

        ``expiration_days``
            The number of days remaining during which the account may
            be activated.

        ``site``
            An object representing the site on which the user
            registered; depending on whether ``django.contrib.sites``
            is installed, this may be an instance of either
            ``django.contrib.sites.models.Site`` (if the sites
            application is installed) or
            ``django.contrib.sites.models.RequestSite`` (if
            not). Consult the documentation for the Django sites
            framework for details regarding these objects' interfaces.

        """
        ctx_dict = { 'activation_key': self.activation_key,
                     'expiration_days': settings.ACCOUNT_ACTIVATION_DAYS,
                     'site': site }
        subject = render_to_string('registration/activation_email_subject.txt',
                                   ctx_dict)
        # Email subject *must not* contain newlines
        subject = ''.join(subject.splitlines())

        message = render_to_string('registration/activation_email.txt',
                                   ctx_dict)

        self.user.email_user(subject, message, settings.DEFAULT_FROM_EMAIL)

# manager classes
class ExperimentMetadataManager(models.Manager):
    def get_by_natural_key(self, key):
        return self.get(namespace=key)

"""
ExperimentMetadata contains records for each type of supported and implement experiment.  A single app could add multiple experiment metadata records 
but they should be closely related.  
"""
class ExperimentMetadata(models.Model):
    title = models.CharField(max_length=255)
    # the URL fragment that this experiment_metadata will occupy,
    namespace_regex = re.compile(r'^(?:[/]?[a-z0-9_]+\/?)+$')
    namespace = models.CharField(max_length=255, unique=True, validators=[RegexValidator(regex=namespace_regex)])
    description = models.TextField(null=True, blank=True)
    date_created = models.DateField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    about_url = models.URLField(null=True, blank=True, verify_exists=True)
    logo_url = models.URLField(null=True, blank=True, verify_exists=True)
    default_configuration = models.ForeignKey('ExperimentConfiguration', null=True, blank=True)

    objects = ExperimentMetadataManager()

    @property
    def name(self):
        return self.title

    def natural_key(self):
        return [self.namespace]

    def __unicode__(self):
        return u"Experiment Type: %s (namespace: %s, created on %s)" % (self.title, self.namespace, self.date_created)

    class Meta:
        ordering = ['namespace', 'date_created']

class Institution(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(null=True, blank=True)
    url = models.URLField(null=True, blank=True, verify_exists=True)
    date_created = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return u"%s (%s)" % (self.name, self.url)

class CommonsUser(models.Model):
    """
    for docs on related_name see
        http://docs.djangoproject.com/en/dev/topics/db/models/#be-careful-with-related-name
    this related name makes user.experimenter and user.participant resolvable.  
    FIXME: should revisit to see if this is recommended practice.
    (either one or the other)
    """
    user = models.OneToOneField(User, related_name='%(class)s', verbose_name=u'Django User', unique=True)
    failed_password_attempts = models.PositiveIntegerField(default=0)
    institution = models.ForeignKey(Institution, null=True, blank=True)
    # opt in or opt out for ability to receive invitations 

    def is_authenticated(self):
        return self.user.is_authenticated()

    def __unicode__(self):
        return u"%s (%s)" % (self.user.get_full_name(), self.user.email)

    class Meta:
        abstract = True


class Experimenter(CommonsUser):
    approved = models.BooleanField(default=False)
    class Meta:
        ordering = ['user']

class ExperimentConfiguration(models.Model):
    experiment_metadata = models.ForeignKey(ExperimentMetadata)
    creator = models.ForeignKey(Experimenter)
    name = models.CharField(max_length=255)
    max_number_of_participants = models.PositiveIntegerField(default=0)
    date_created = models.DateField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    is_public = models.BooleanField(default=True)
    max_group_size = models.PositiveIntegerField(default=5)

    @property
    def namespace(self):
        return self.experiment_metadata.namespace

    def __unicode__(self):
        return u"ExperimentConfiguration %s for %s" % (self.name, self.experiment_metadata)

    class Meta:
        ordering = ['experiment_metadata', 'creator', 'date_created']


class ExperimentManager(models.Manager):
    def get_all_active(self):
        return self.filter(status='ACTIVE')

    def increment_elapsed_time(self, status='ROUND_IN_PROGRESS'):
        if status:
            es = self.filter(status=status)
            es.update(current_round_elapsed_time=models.F('current_round_elapsed_time') + 1,
                      total_elapsed_time=models.F('total_elapsed_time') + 1)


# an actual instance of an experiment; represents a concrete
# parameterization of this experiment.
class Experiment(models.Model):
    STATUS_CHOICES = (
                           ('INACTIVE', 'Not active'),
                           ('ACTIVE', 'Active'),
                           ('PAUSED', 'Paused'),
                           ('INSTRUCTIONS', 'Instructions'),
                           ('QUIZ', 'Quiz in progress'),
                           ('ROUND_IN_PROGRESS', 'Round in progress'),
                           ('DEBRIEFING', 'Debriefing'),
                           ('COMPLETED', 'Completed'),
                           )
    authentication_code = models.CharField(max_length=32, default="vcweb.auth.code")
    current_round_number = models.PositiveIntegerField(default=0)
    experimenter = models.ForeignKey(Experimenter)
    experiment_metadata = models.ForeignKey(ExperimentMetadata)
    experiment_configuration = models.ForeignKey(ExperimentConfiguration,
                                                 related_name='experiments')
    status = models.CharField(max_length=32, choices=STATUS_CHOICES,
                              default='INACTIVE')
    date_created = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    start_date_time = models.DateTimeField(null=True, blank=True)
    # how long this experiment should run in a date format
    # 1w2d = 1 week 2 days = 9d
    duration = models.CharField(max_length=32, null=True, blank=True)
    """ how often the experiment_metadata server should tick. """
    tick_duration = models.CharField(max_length=32, null=True, blank=True)

    """ total elapsed time in seconds since this experiment_metadata was started, 
    incremented by the heartbeat monitor. """
    total_elapsed_time = models.PositiveIntegerField(default=0)
    """ current round start time """
    current_round_start_time = models.DateTimeField(null=True, blank=True)
    """ elapsed time in seconds for the current round. """
    current_round_elapsed_time = models.PositiveIntegerField(default=0)
    """
    Experimenter driven experiments have checkpoints where the experimenter needs to
     explicitly signal the system to 
    move to the next round or stage.
    """
    is_experimenter_driven = models.BooleanField(default=True)
    """ name of the AMQP exchange hosting this experiment """
    amqp_exchange_name = models.CharField(max_length=64, default="vcweb.default.exchange")


    objects = ExperimentManager()


    @property
    def channel_name(self):
        return "%s.%s" % (self.experiment_metadata.namespace, self.id)

    def start(self):
        if not self.is_running():
            self.allocate_groups()
            self.status = 'ACTIVE'
            self.save()
            logger.debug("About to send round started signal")
            # notify game handlers...
            signals.round_started.send_robust(None, experiment_id=self.id, time=datetime.datetime.now(), round_configuration_id=self.get_current_round().id)


    def allocate_groups(self, randomize=True):
        current_group = Group(number=1, max_size=self.experiment_configuration.max_group_size, experiment=self)
        current_group.save()
        if randomize:
            participants = list(self.participants.all())
            random.shuffle(participants)
        else:
            participants = self.participants.all()

        """
        group.add_participant returns a new group or the existing group depending on whether or not the group is full. 
        """
        for p in participants:
            current_group = current_group.add_participant(p)


    def is_running(self):
        return self.status != 'INACTIVE'


    def advance_to_next_round(self):
        self.current_round_elapsed_time = 0
        self.current_round_number = models.F('current_round_number') + 1
        self.save()
        return Experiment.objects.get(pk=self.pk)

    def start_round(self):
        self.status = 'ROUND_IN_PROGRESS'

    """ returns a fresh copy of this experiment with configuration / metadata intact """
    def clone(self, experimenter=None):
        if not experimenter:
            experimenter = self.experimenter
        return Experiment(experimenter=experimenter,
                          authentication_code=self.authentication_code,
                          experiment_metadata=self.experiment_metadata,
                          experiment_configuration=self.experiment_configuration,
                          duration=self.duration,
                          tick_duration=self.tick_duration,
                          is_experimenter_driven=self.is_experimenter_driven
                          )

    def get_current_round(self):
        return RoundConfiguration.objects.get(experiment_configuration=self.experiment_configuration,
                                              sequence_number=self.current_round_number)

    @property
    def url(self, request):
        user = request.user
        if user.is_authenticated():
            return "/{0}/{1}".format("participant" if is_participant(user) else "experimenter", self.url_id)
        else:
            return self.namespace


    @property
    def participant_url(self):
        return "/%s" % (self.url_id)

    @property
    def management_url(self):
        return "/%s/experimenter" % (self.url_id)

    @property
    def namespace(self):
        return self.experiment_metadata.namespace

    @property
    def url_id(self):
        return "%s/%s" % (self.experiment_metadata.namespace, self.id)

    def __unicode__(self):
        return u"%s (status: %s, last updated on %s)" % (self.experiment_metadata.name, self.status, self.last_modified)

    def ___eq___(self, other):
        return self.id == other.id

    def ___cmp___(self, other):
        return self.id.___cmp___(other.id)

    def ___hash___(self):
        return self.id.___hash___()

class RoundConfiguration(models.Model):
    ROUND_TYPE_CHOICES = (
                          ('INSTRUCTIONS', 'Instructions round'),
                          ('QUIZ', 'Quiz round'),
                          ('CHAT', 'Chat round'),
                          ('PRACTICE', 'Practice round'),
                          ('PLAY', 'Interactive experiment round'),
                          ('DEBRIEFING', 'Debriefing round'),
                          )
    experiment_configuration = models.ForeignKey(ExperimentConfiguration,
                                                 related_name='round_configurations')
    sequence_number = models.PositiveIntegerField(help_text='Determines the ordering of the rounds in an experiment in ascending order, e.g., 1,2,3,4,5')
    date_created = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    """
    How long should this round execute before advancing to the next?  
    Interpreted as whole seconds.
    """
    duration = models.PositiveIntegerField(default=0,
                                           help_text='Duration in seconds.  0 means an untimed round that can only be advanced by an experimenter.')
    """ instructions, if any, to display before the round begins """
    instructions = models.TextField(null=True, blank=True)
    """ debriefing, if any, to display after the round ends """
    debriefing = models.TextField(null=True, blank=True)
    round_type = models.CharField(max_length=32,
                                  choices=ROUND_TYPE_CHOICES,
                                  default='PLAY')

    """ 
    name of the quiz template to be used this round.  
    Won't be used unless round_type='QUIZ' and should be just the template filename, 
    e.g., if set to quiz_2.html in the forestry experiment app, this should be loaded 
    from forestry/templates/forestry/quiz_2.html 
    FIXME: figure out better method for storing template names.  should we manage quizzes as Quiz objects instead? 
    """
    quiz_template = models.CharField(max_length=32,
                                     null=True,
                                     blank=True,
                                     help_text='quiz template filename e.g., "quiz_2.html"')

    @property
    def quiz_template_path(self):
        return "%s/%s" % (self.experiment_configuration.namespace, self.quiz_template)

    def get_debriefing(self, participant_id=None, **kwargs):
        return self.templatize(self.debriefing, participant_id, kwargs)

    def get_instructions(self, participant_id=None, **kwargs):
        return self.templatize(self.instructions, participant_id, kwargs)

    def is_debriefing_round(self):
        return self.round_type == 'DEBRIEFING'

    def is_chat_round(self):
        return self.round_type == 'CHAT'

    def is_instructions_round(self):
        return self.round_type == 'INSTRUCTIONS'

    def is_quiz_round(self):
        return self.round_type == 'QUIZ'

    def templatize(self, template_string, participant_id=None, **kwargs):
        return Template(template_string).substitute(kwargs, round_number=self.sequence_number, participant_id=participant_id)

    def __unicode__(self):
        return u"Round %d for %s" % (self.sequence_number, self.experiment_configuration)

    class Meta:
        ordering = [ 'experiment_configuration', 'sequence_number', 'date_created' ]


class Parameter(models.Model):
    PARAMETER_TYPES = (
                    ('int', 'Integer'),
                    ('string', 'String'),
                    ('float', 'Float'),
                    ('boolean', (('True', True), ('False', False))),
                    ('enum', 'enum')
                    )
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=32, choices=PARAMETER_TYPES)
    date_created = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    creator = models.ForeignKey(Experimenter)


    def __unicode__(self):
        return u"%s (%s)" % (self.name, self.type)

    class Meta:
        abstract = True
        ordering = ['name']

"""
Configuration parameters are used to tune the 
"""
class ConfigurationParameter(Parameter):
    is_required = models.BooleanField(default=False)
    def __unicode__(self):
        return u"CPRM: [name:%s, type:%s]" % (self.name, self.type)

#    class Meta:
#        db_table = 'vcweb_configuration_parameter'


class DataParameter(Parameter):

    def ___eq___(self, other):
        return self.name == other.name

    def ___cmp___(self, other):
        return self.name.__cmp__(other.name)

    def ___hash___(self):
        return self.name.__hash__()


    def __unicode__(self):
        return u"Name: {0} - Type: {1}".format(self.name, self.type)

#    class Meta:
#        db_table = 'vcweb_data_parameter'

# round parameters are 
class RoundParameter(models.Model):
    round_configuration = models.ForeignKey(RoundConfiguration, related_name='parameters')
    parameter = models.ForeignKey(ConfigurationParameter)
    parameter_value = models.CharField(max_length=255)

    def __unicode__(self):
        return u"{0} -> [{1}: {2}]".format(self.round_configuration, self.parameter, self.parameter_value)


class Group(models.Model):
    number = models.PositiveIntegerField()
    """ how many members can this group hold at a maximum? Should be specified as a ConfigurationParameter somewhere """
    max_size = models.PositiveIntegerField(default=5)
    experiment = models.ForeignKey(Experiment, related_name='groups')

    """ should return a unique chat / event channel to communicate on """
    @property
    def channel(self):
        return u"%s.%d" % (self.experiment.event_channel_name, self.number)


    @property
    def experiment_channel(self):
        return self.experiment.event_channel_name

    @property
    def size(self):
        return self.participants.count()

    def is_full(self):
        return self.size >= self.max_size

    def is_open(self):
        return self.size < self.max_size

    def create_next_group(self, size=0):
        g = Group(number=self.number + 1, max_size=self.max_size, experiment=self.experiment)
        g.save()
        return g
    """
    Adds the given participant to this group or a new group if this group is full.
    Returns the group the participant was added to.
    If participant is invalid, returns this group as a no-op.
    """
    def add_participant(self, participant):
        if not participant:
            logger.warning("Trying to add invalid participant %s to group %s" % (participant, self))
            return self

        group = self
        if not group.is_open():
            logger.warning("Group is full: ({0} of {1})".format(self.size, self.max_size))
            group = self.create_next_group()

        participant_group_rel = ParticipantGroupRelationship(participant=participant, group=group, round_joined=self.experiment.get_current_round(), participant_number=group.size + 1)
        participant_group_rel.save()
        return group

    def __unicode__(self):
        return u"Group #{0} in {1}".format(self.number, self.experiment)

    class Meta:
        ordering = ['experiment', 'number']


"""
Data values stored for a particular group in a particular round.
"""
class GroupRoundData (models.Model):
    group = models.ForeignKey(Group, related_name='group_round_data')
    round = models.ForeignKey(RoundConfiguration, related_name='group_round_data')
    """ show instructions before the round begins? """
    show_instructions = models.BooleanField(default=True)
    """ show debriefing after the round ends? """
    show_debriefing = models.BooleanField(default=False)
    elapsed_time = models.PositiveIntegerField(default=0)

    def __unicode__(self):
        return u"Round Data for {0} in {1}".format(self.group, self.round)

#    class Meta:
#        db_table = 'vcweb_group_round_data'

class DataValue(models.Model):
    parameter = models.ForeignKey(DataParameter)
    parameter_value = models.CharField(max_length=512)
    # FIXME: change to DateTimeField
    time_recorded = models.DateTimeField(auto_now_add=True)
    experiment = models.ForeignKey(Experiment)

    def __unicode__(self):
        return u"Data value: [parameter {0}, value {1}], recorded at {2} for experiment {3}".format(self.parameter, self.parameter_value, self.time_recorded, self.experiment)

    class Meta:
        abstract = True

class GroupRoundDataValue(DataValue):
    group_round_data = models.ForeignKey(GroupRoundData, related_name='group_round_data_values')
    def __unicode__(self):
        return u"data value {0}: {1} for group {2}".format(self.parameter, self.parameter_value, self.group_round_data.group)
    class Meta:
        ordering = [ 'parameter' ]

class Participant(CommonsUser):
    can_receive_invitations = models.BooleanField(default=False)
    groups = models.ManyToManyField(Group, through='ParticipantGroupRelationship', related_name='participants')
    experiments = models.ManyToManyField(Experiment, through='ParticipantExperimentRelationship', related_name='participants')

    def get_participant_number(self, experiment):
        return ParticipantGroupRelationship.objects.get_participant_number(experiment, self)

    def get_group(self, experiment):
        return ParticipantGroupRelationship.objects.get_group(experiment, self)
#    objects = ParticipantManager()
    class Meta:
        ordering = ['user']

"""
Many-to-many relationship entity storing a participant and the experiment they are participating in.
"""
class ParticipantExperimentRelationship(models.Model):
    participant = models.ForeignKey(Participant)
    participant_identifier = models.CharField(max_length=32)
    sequential_participant_identifier = models.PositiveIntegerField()
    experiment = models.ForeignKey(Experiment)
    date_created = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User)

    def __init__(self, *args, **kwargs):
        super(ParticipantExperimentRelationship, self).__init__(*args, **kwargs)
        self.generate_identifier()

    """ generates a unique identifier for the given participant and experiment stored in this relationship """
    def generate_identifier(self):
        """ set participant_identifier if it hasn't been set already.  """
        if not self.participant_identifier:
            sha1 = hashlib.sha1()
            sha1.update("%s%i%s" % (self.participant.user.email, self.experiment.id, self.date_created))
            self.participant_identifier = base64.urlsafe_b64encode(sha1.digest())
            self.sequential_participant_identifier = ParticipantExperimentRelationship.objects.filter(experiment=self.experiment).count() + 1
        return self.participant_identifier


    def __unicode__(self):
        return u"Experiment {0} - participant {1} (created {2})".format(self.experiment, self.participant, self.date_created)

class ChatMessage(models.Model):
    participant = models.ForeignKey(Participant, related_name='chat_messages')
    message = models.CharField(max_length=512)
    """ if set, this is a targeted message.  If null, this is a broadcast message to the entire group """
    target_participant = models.ForeignKey(Participant, null=True, blank=True, related_name='targets')
    target_group = models.ForeignKey(Group, null=True, blank=True)
    date_created = models.DateTimeField(auto_now_add=True)
    round_configuration = models.ForeignKey(RoundConfiguration, related_name='chat_messages')
    experiment = models.ForeignKey(Experiment, related_name='chat_messages')

    def __unicode__(self):
        """ return this participant's sequence number combined with the message """
        participant_number = self.participant.get_participant_number(self.experiment)
        return u"{0}: {1}".format(participant_number, self.message)


class ParticipantGroupRelationshipManager(models.Manager):

    def get_group(self, experiment, participant):
        participant_group = self.get_participant_group(experiment, participant)
        return participant_group.group if participant_group else None

    def get_participant_group(self, experiment, participant):
        try:
            return self.get(group__experiment=experiment, participant=participant)
        except ParticipantGroupRelationship.DoesNotExist:
            logger.warning("Participant %s does not belong to a group in %s" % (participant, experiment))
            return None

    def get_participant_number(self, experiment, participant):
        participant_group = self.get_participant_group(experiment, participant)
        return participant_group.participant_number if participant_group else None

"""
Many-to-many relationship entity storing a participant, group, their participant number in that group, the 
round in which they joined the group, and the datetime that they joined the group.
"""
class ParticipantGroupRelationship(models.Model):
    participant_number = models.PositiveIntegerField()
    participant = models.ForeignKey(Participant)
    group = models.ForeignKey(Group)
    round_joined = models.ForeignKey(RoundConfiguration)
    date_joined = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)

    objects = ParticipantGroupRelationshipManager()

    def __unicode__(self):
        return u"{0}: {1} (in {2})".format(self.participant, self.participant_number, self.group)

    class Meta:
        ordering = ['participant_number', 'participant']

"""
holds all participant data for a given round and participant.
"""
class ParticipantRoundData(models.Model):
    participant = models.ForeignKey(Participant, related_name='round_data')
    round_configuration = models.ForeignKey(RoundConfiguration, related_name='round_data')

"""
The particular participant data value for a given ParticipantRoundData (round + participant entity)
"""
class ParticipantDataValue(DataValue):
    participant_data = models.ForeignKey(ParticipantRoundData, related_name='participant_data')
    class Meta:
        ordering = [ 'parameter' ]

class SessionTracker(models.Model):
    login_time = models.DateTimeField(auto_now_add=True)
    logout_time = models.DateTimeField()
    # hook into logout signal?

class ExperimenterSession(SessionTracker):
    experimenter_id = models.ForeignKey(Experimenter)

class ParticipantSession(SessionTracker):
    participant_id = models.ForeignKey(Participant)

def is_experimenter(user):
    try:
        return user.experimenter
    except Experimenter.DoesNotExist:
        return None

def is_participant(user):
    try:
        return user.participant
    except Participant.DoesNotExist:
        return None


