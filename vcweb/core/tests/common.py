import random

from datetime import datetime, date
from django.conf import settings
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.client import RequestFactory, Client

from ..models import (Experiment, Experimenter, ExperimentConfiguration, RoundConfiguration, Parameter, Group, User,
                      PermissionGroup, Participant, ParticipantSignup, Institution, ExperimentSession, Invitation)

from ..subjectpool.views import get_potential_participants

import logging

logger = logging.getLogger(__name__)


class BaseVcwebTest(TestCase):

    """
    base class for vcweb.core tests, sets up test fixtures for participants,
    and a number of participants, experiments, etc.
    """
    DEFAULT_EXPERIMENTER_PASSWORD = 'test.experimenter'
    DEFAULT_EXPERIMENTER_EMAIL = 'vcweb.test@mailinator.com'

    def load_experiment(self, experiment_metadata=None, experimenter_password=None, **kwargs):
        if experiment_metadata is None:
            # FIXME: assumes that there is always some Experiment available to load. revisit this, or figure out some
            # better way to bootstrap tests
            experiment = Experiment.objects.first().clone()
        else:
            experiment = self.create_new_experiment(
                experiment_metadata, **kwargs)
        if experimenter_password is None:
            experimenter_password = BaseVcwebTest.DEFAULT_EXPERIMENTER_PASSWORD

        self.experiment = experiment
        # currently associating all available Parameters with this
        # ExperimentMetadata
        if not experiment.experiment_metadata.parameters.exists():
            experiment.experiment_metadata.parameters.add(
                *Parameter.objects.values_list('pk', flat=True))
        experiment.experiment_configuration.round_configuration_set.exclude(
            sequence_number=1).update(duration=60)
        experiment.save()
        u = experiment.experimenter.user
        u.set_password(experimenter_password)
        u.save()
        return experiment

    @property
    def login_url(self):
        return reverse('core:login')

    @property
    def profile_url(self):
        return reverse('core:profile')

    @property
    def dashboard_url(self):
        return reverse('core:dashboard')

    @property
    def update_experiment_url(self):
        return reverse('core:update_experiment')

    @property
    def check_email_url(self):
        return reverse('core:check_email')

    @property
    def experiment_metadata(self):
        return self.experiment.experiment_metadata

    @property
    def experiment_configuration(self):
        return self.experiment.experiment_configuration

    @property
    def experimenter(self):
        return self.experiment.experimenter

    @property
    def round_configurations(self):
        return self.experiment_configuration.round_configuration_set

    @property
    def participants(self):
        return self.experiment.participant_set.all()

    @property
    def participant_group_relationships(self):
        return self.experiment.participant_group_relationships

    def update_experiment(self, action=None, **kwargs):
        kwargs.update(experiment_id=self.experiment.pk, action=action)
        return self.post(self.update_experiment_url, kwargs)

    def reverse(self, *args, **kwargs):
        return reverse(*args, **kwargs)

    def login(self, *args, **kwargs):
        return self.client.login(*args, **kwargs)

    def login_participant(self, participant, password='test'):
        return self.client.login(username=participant.email, password=password)

    def login_experimenter(self, experimenter=None, password=None):
        if experimenter is None:
            experimenter = self.experimenter
        if password is None:
            password = BaseVcwebTest.DEFAULT_EXPERIMENTER_PASSWORD
        return self.client.login(username=experimenter.email, password=password)

    def create_new_experiment(self, experiment_metadata, experimenter=None):
        """
        Creates a new Experiment and ExperimentConfiguration based on the given ExperimentMetadata.
        """
        if experimenter is None:
            experimenter = self.demo_experimenter
        experiment_configuration = ExperimentConfiguration.objects.create(experiment_metadata=experiment_metadata,
                                                                          name='Test Experiment Configuration',
                                                                          creator=experimenter)
        for index in xrange(1, 10):
            should_initialize = (index == 1)
            experiment_configuration.round_configuration_set.create(sequence_number=index,
                                                                    randomize_groups=should_initialize,
                                                                    initialize_data_values=should_initialize)
        return Experiment.objects.create(experimenter=experimenter,
                                         experiment_metadata=experiment_metadata,
                                         experiment_configuration=experiment_configuration)

    def add_participants(self, demo_participants=True, number_of_participants=None, participant_emails=None,
                         test_email_suffix='asu.edu', **kwargs):
        if number_of_participants is None:
            # set default number of participants to max group size * 2
            number_of_participants = self.experiment.experiment_configuration.max_group_size * \
                2
        experiment = self.experiment
        if demo_participants:
            if experiment.participant_set.count() == 0:
                logger.debug(
                    "no participants found. adding %d participants to %s", number_of_participants, experiment)
                experiment.setup_test_participants(email_suffix=test_email_suffix,
                                                   count=number_of_participants, password='test')
        else:
            if participant_emails is None:
                # generate participant emails
                participant_emails = [
                    'generated-test-%d@asu.edu' % index for index in range(0, number_of_participants)]
            self.experiment.register_participants(
                emails=participant_emails, password='test')
            # XXX: should can_receive_invitations automatically be set to true in Experiment.register_participants
            # instead?
            self.experiment.participant_set.update(
                can_receive_invitations=True)

    def setUp(self, **kwargs):
        self.client = Client()
        self.factory = RequestFactory()
        self.load_experiment(**kwargs)
        self.add_participants(**kwargs)
        logging.disable(settings.DISABLED_TEST_LOGLEVEL)

    @property
    def demo_experimenter(self):
        if getattr(self, '_demo_experimenter', None) is None:
            self._demo_experimenter = Experimenter.objects.get(
                user__email=settings.DEMO_EXPERIMENTER_EMAIL)
        return self._demo_experimenter

    def create_experimenter(self, email=None, password=None):
        if email is None:
            email = BaseVcwebTest.DEFAULT_EXPERIMENTER_EMAIL
        if password is None:
            password = BaseVcwebTest.DEFAULT_EXPERIMENTER_PASSWORD
        u = User.objects.create_user(
            username=email, email=email, password=password)
        u.groups.add(PermissionGroup.experimenter.get_django_group())
        return Experimenter.objects.create(user=u, approved=True)

    def advance_to_data_round(self):
        e = self.experiment
        e.activate()
        while e.has_next_round:
            if e.current_round.is_playable_round:
                return e
            e.advance_to_next_round()

    def reload_experiment(self):
        self.experiment = Experiment.objects.get(pk=self.experiment.pk)
        return self.experiment

    def post(self, *args, **kwargs):
        response = self.client.post(*args, **kwargs)
        self.reload_experiment()
        return response

    def get(self, *args, **kwargs):
        return self.client.get(*args, **kwargs)

    def all_data_rounds(self):
        e = self.experiment
        e.activate()
        while e.has_next_round:
            if e.current_round.is_playable_round:
                yield self.experiment
            e.advance_to_next_round()

    def create_new_round_configuration(self, round_type='REGULAR', template_filename='', template_id=''):
        return RoundConfiguration.objects.create(experiment_configuration=self.experiment_configuration,
                                                 sequence_number=(
                                                     self.experiment_configuration.last_round_sequence_number + 1),
                                                 round_type=round_type,
                                                 template_filename=template_filename,
                                                 template_id=template_id)

    def create_parameter(self, name='test.parameter', scope=Parameter.Scope.EXPERIMENT, parameter_type='string'):
        return Parameter.objects.create(creator=self.experimenter, name=name, scope=scope, type=parameter_type)

    def create_group(self, max_size=10, experiment=None):
        if not experiment:
            experiment = self.experiment
        return Group.objects.create(number=1, max_size=max_size, experiment=experiment)

    class Meta:
        abstract = True


class SubjectPoolTest(BaseVcwebTest):

    def setup_participants(self):
        password = "test"
        participants = []
        for x in xrange(500):
            email = "student" + str(x) + "asu@asu.edu"
            user = User.objects.create_user(first_name='xyz', last_name='%d' % x, username=email, email=email,
                                            password=password)
            # Assign the user to participant permission group
            user.groups.add(PermissionGroup.participant.get_django_group())
            user.save()

            p = Participant(user=user)
            p.can_receive_invitations = random.choice([True, False])
            p.gender = random.choice(['M', 'F'])
            year = random.choice(range(1980, 1995))
            month = random.choice(range(1, 12))
            day = random.choice(range(1, 28))
            random_date = datetime(year, month, day)
            p.birthdate = random_date
            p.major = 'CS'
            p.class_status = random.choice(
                ['Freshman', 'Sophomore', 'Junior', 'Senior'])
            p.institution = Institution.objects.get(
                name="Arizona State University")
            participants.append(p)
        Participant.objects.bulk_create(participants)
        # logger.debug("TOTAL PARTICIPANTS %d", len(Participant.objects.all()))

    def setup_experiment_sessions(self):
        e = self.experiment
        es_pk = []
        for x in xrange(4):
            es = ExperimentSession()
            es.experiment_metadata = e.experiment_metadata
            year = date.today().year
            month = date.today().month
            day = random.choice(range(1, 30))
            random_date = datetime(year, month, day)
            es.scheduled_date = random_date
            es.scheduled_end_date = random_date
            es.capacity = 1
            es.location = "Online"
            es.creator = self.demo_experimenter.user
            es.date_created = datetime.now()
            es.save()
            es_pk.append(es.pk)
        return es_pk

    def get_final_participants(self):
        potential_participants = get_potential_participants(
            self.experiment_metadata.pk, "Arizona State University")
        potential_participants_count = len(potential_participants)
        # logger.debug(potential_participants)
        no_of_invitations = 50

        if potential_participants_count == 0:
            final_participants = []
        else:
            if potential_participants_count < no_of_invitations:
                final_participants = potential_participants
            else:
                final_participants = random.sample(potential_participants,
                                                   no_of_invitations)
        return final_participants

    def setup_participant_signup(self, participant_list, es_pk_list):
        participant_list = participant_list[:25]

        for person in participant_list:
            inv = Invitation.objects.filter(
                participant=person, experiment_session__pk__in=es_pk_list).order_by('?')[:1]
            ps = ParticipantSignup()
            ps.invitation = inv[0]
            year = date.today().year
            month = date.today().month - 1
            day = random.choice(range(1, 30))
            random_date = datetime(year, month, day)
            ps.date_created = random_date
            # logger.debug(random_date)
            ps.attendance = random.choice([0, 1, 2, 3])
            # logger.debug(ps.attendance)
            ps.save()

    def setup_invitations(self, participants, es_pk_list):
        invitations = []
        experiment_sessions = ExperimentSession.objects.filter(
            pk__in=es_pk_list)
        user = self.demo_experimenter.user

        for participant in participants:
            # recipient_list.append(participant.email)
            for es in experiment_sessions:
                year = date.today().year
                month = date.today().month - 1
                day = random.choice(range(1, 30))
                random_date = datetime(year, month, day)
                invitations.append(Invitation(participant=participant, experiment_session=es, date_created=random_date,
                                              sender=user))

        Invitation.objects.bulk_create(invitations)
