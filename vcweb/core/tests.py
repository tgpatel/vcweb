from django.test import TestCase
from vcweb.core import signals
from vcweb.core.models import (Experiment, Experimenter, ExperimentConfiguration,
    Participant, ParticipantExperimentRelationship, ParticipantGroupRelationship, Group,
    ExperimentMetadata, RoundConfiguration, Parameter, RoundParameterValue,
    GroupActivityLog)
import logging

logger = logging.getLogger(__name__)

"""
base class for vcweb.core tests, sets up test fixtures for participants,
forestry_test_data, and a number of participants, experiments, etc.,
based on the forestry experiment
"""
class BaseVcwebTest(TestCase):
    fixtures = ['test_users_participants', 'forestry_test_data']

    def load_experiment(self):
        self.experiment = Experiment.objects.get(pk=1)
        return self.experiment

    def setUp(self):
        self.participants = Participant.objects.all()
        self.load_experiment()
        self.experimenter = Experimenter.objects.get(pk=1)
        self.experiment_metadata = ExperimentMetadata.objects.get(pk=1)
        self.experiment_configuration = ExperimentConfiguration.objects.get(pk=1)

    def advance_to_data_round(self):
        self.experiment.activate()
        while self.experiment.has_next_round:
            if self.experiment.current_round.is_playable_round:
                return self.experiment
            self.experiment.advance_to_next_round()

    def all_data_rounds(self):
        self.experiment.activate()
        while self.experiment.has_next_round:
            if self.experiment.current_round.is_playable_round:
                yield self.experiment
            self.experiment.advance_to_next_round()

    def create_new_round_configuration(self, round_type='REGULAR', template_name=None):
        return RoundConfiguration.objects.create(experiment_configuration=self.experiment_configuration,
                sequence_number=(self.experiment_configuration.last_round_sequence_number + 1),
                round_type=round_type,
                template_name=template_name
                )

    def create_new_experiment(self):
        return Experiment.objects.create(experimenter=self.experimenter,
                experiment_configuration=self.experiment_configuration,
                experiment_metadata=self.experiment_metadata)

    def create_new_parameter(self, name='vcweb.test.parameter', scope='EXPERIMENT_SCOPE', parameter_type='string'):
        return self.experiment_metadata.parameters.create(creator=self.experimenter, 
                name=name, scope=scope, type=parameter_type)


    def create_new_group(self, max_size=10, experiment=None):
        if not experiment:
            experiment = self.experiment
        return Group.objects.create(number=1, max_size=max_size, experiment=experiment)

    class Meta:
        abstract = True

class QueueTest(BaseVcwebTest):
    def test_simple(self):
        from kombu.connection import BrokerConnection
        connection = BrokerConnection(transport="djkombu.transport.DatabaseTransport")
        q = connection.SimpleQueue("chat")
        for test_string in ('testing', '1-2-3', 'good gravy'):
            q.put(test_string)
            self.assertEqual(test_string, q.get().body)

    def test_publish(self):
        pass


class ExperimentMetadataTest(BaseVcwebTest):
    namespace_regex = ExperimentMetadata.namespace_regex

    def create_experiment_metadata(self, namespace=None):
        return ExperimentMetadata(title="test title: %s" % namespace, namespace=namespace)

    def test_valid_namespaces(self):
        valid_namespaces = ('forestry/hooha', 'furestry', 'f', 'hallo/h', '/f',
                            'abcdefghijklmnopqrstuvwxyz1234567890/abcdefghijklmnopqrstuvwxyz1234567890',
                            )
        for namespace in valid_namespaces:
            self.assertTrue(self.namespace_regex.match(namespace))
            em = self.create_experiment_metadata(namespace)
            em.save()

    def test_invalid_namespaces(self):
        from django.core.exceptions import ValidationError
        invalid_namespaces = ('#$what the!',
                              "$$!it's a trap!",
                              '/!@')
        for namespace in invalid_namespaces:
            em = self.create_experiment_metadata(namespace)
            self.assertRaises(ValidationError, em.full_clean)
            self.assertFalse(self.namespace_regex.match(namespace))

    def test_unicode(self):
        em = self.create_experiment_metadata('test_unicode_namespace')
        em.save()
        self.assertTrue(em.pk and (em.pk > 0), 'test unicode namespace experiment metadata record should have valid id now')
        self.assertTrue(unicode(em))
        #self.assertRaises(ValueError, unicode(em).index, '{')


class ExperimentConfigurationTest(BaseVcwebTest):
    def test_final_sequence_number(self):
        e = self.experiment
        ec = e.experiment_configuration
        self.assertEqual(ec.final_sequence_number, ec.last_round_sequence_number)

class ExperimentTest(BaseVcwebTest):
    def round_started_test_handler(self, experiment=None, time=None, round_configuration=None, **kwargs):
        logger.debug("invoking round started test handler with args experiment:%s time:%s round_configuration_id:%s", experiment, time, round_configuration)
        self.assertEqual(experiment, self.experiment)
        self.assertEqual(round_configuration, self.experiment.current_round)
        self.assertTrue(time, "time should be set")
        raise AssertionError

    def test_start_round(self):
        signals.round_started.connect(self.round_started_test_handler, sender=self)
        with self.assertRaises(AssertionError):
            self.experiment.start_round(sender=self)
        self.assertTrue(self.experiment.is_active)

    def test_group_allocation(self):
        experiment = self.experiment
        experiment.allocate_groups(randomize=False)
        self.assertEqual(experiment.groups.count(), 2, "there should be 2 groups after non-randomized allocation")
        self.assertEqual(sum(map(lambda group:group.participants.count(), experiment.groups.all())), 10)

    def test_participant_numbering(self):
        experiment = self.experiment
        experiment.allocate_groups(randomize=False)
        for pgr in ParticipantGroupRelationship.objects.by_experiment(experiment):
            participant_number = pgr.participant_number
            group = pgr.group
            self.assertTrue(0 < participant_number <= group.max_size)
            # FIXME: this relies on the fact that non-randomized group allocation will match the auto increment pk
            # generation for the participants.  Remove?
            self.assertEqual(participant_number % group.max_size, pgr.participant.pk % group.max_size)

    def test_next_round(self):
        experiment = self.experiment
        round_number = experiment.current_round_sequence_number
        self.assertTrue(round_number >= 0)
        self.assertTrue(experiment.has_next_round)
        while (experiment.has_next_round):
            round_number += 1
            experiment.advance_to_next_round()
            self.assertTrue(experiment.current_round_sequence_number == round_number)

    def test_increment_elapsed_time(self):
        experiment = self.experiment
        current_round_elapsed_time = experiment.current_round_elapsed_time
        self.assertTrue(current_round_elapsed_time == 0)
        total_elapsed_time = experiment.total_elapsed_time
        self.assertTrue(total_elapsed_time == 0)
        Experiment.objects.increment_elapsed_time(status=experiment.status)
        experiment = self.load_experiment()
        self.assertEqual(experiment.current_round_elapsed_time, current_round_elapsed_time + 1)
        self.assertEqual(experiment.total_elapsed_time, total_elapsed_time + 1)

class GroupTest(BaseVcwebTest):
    def test_set_data_value_activity_log(self):
        e = self.advance_to_data_round()
        test_data_value = 10
        for g in e.groups.all():
            activity_log_counter = GroupActivityLog.objects.filter(group=g).count()
            for data_value in g.data_values.all():
                # XXX: pathological use of set_data_value, no point in doing it
                # this way since typical usage would do a lookup by name.
                g.set_data_value(parameter=data_value.parameter, value=test_data_value)
                activity_log_counter += 1
                self.assertEqual(activity_log_counter, GroupActivityLog.objects.filter(group=g).count())
                self.assertEqual(g.get_scalar_data_value(parameter=data_value.parameter), test_data_value)

    def test_transfer_to_next_round(self):
        parameter = self.create_new_parameter(scope=Parameter.GROUP_SCOPE, name='test_group_parameter', parameter_type='int')
        test_data_value = 37
        e = self.experiment
        first_pass = True
        while e.has_next_round:
            if first_pass:
                for g in e.groups.all():
                    g.set_data_value(parameter=parameter, value=test_data_value)
                    self.assertEqual(g.get_data_value(parameter=parameter).value, test_data_value)
                    self.assertEqual(g.get_scalar_data_value(parameter=parameter), test_data_value)
                    g.transfer_to_next_round(parameter)
                first_pass = False
            else:
                for g in e.groups.all():
                    self.assertEqual(g.get_data_value(parameter=parameter).value, test_data_value)
                    self.assertEqual(g.get_scalar_data_value(parameter=parameter), test_data_value)
                    g.transfer_to_next_round(parameter)
            e.advance_to_next_round()

    def test_initialize_data_parameters(self):
        e = self.experiment
        e.activate()
        e.start_round()
        # instructions round
        for g in e.groups.all():
            g.initialize_data_parameters()
            self.assertEqual(e.current_round_data.group_data_values.count(), 0)
            self.assertEqual(e.current_round_data.participant_data_values.count(), 0)
        # quiz round
        e.advance_to_next_round()
        e.start_round()
        for g in e.groups.all():
            g.initialize_data_parameters()
# FIXME: (changed to practice round for demo purposes)
            #self.assertEqual(e.current_round_data.group_data_values.count(), 0)
            #self.assertEqual(e.current_round_data.participant_data_values.count(), 0)
        # first practice round
        e.advance_to_next_round()
        e.start_round()
        for g in e.groups.all():
            for i in xrange(10):
                self.assertEqual(e.current_round_data.group_data_values.count(), 2)
                # multiple invocations to initialize_data_parameters should be harmless.
                g.initialize_data_parameters()
                self.assertEqual(e.current_round_data.group_data_values.count(), 2)
                g.initialize_data_parameters()
                self.assertEqual(e.current_round_data.group_data_values.count(), 2)
                g.initialize_data_parameters()
        # first chat round (practice)
        e.end_round()
        e.advance_to_next_round()
        e.start_round()
        for g in e.groups.all():
            g.initialize_data_parameters()
            self.assertEqual(e.current_round_data.group_data_values.count(), 2)
            self.assertEqual(e.current_round_data.participant_data_values.count(), 0)
        # second practice round


    def test_group_add(self):
        """
        Tests get_participant_number after groups have been assigned
        """
        g = self.create_new_group(max_size=10, experiment=self.experiment)
        count = 0;
        for p in self.participants:
            g.add_participant(p)
            count += 1
            self.assertTrue(g.participants)
            self.assertEqual(g.participants.count(), count, "group.participants size should be %i" % count)
            self.assertEqual(g.size, count, "group size should be %i" % count)


class ParticipantExperimentRelationshipTest(BaseVcwebTest):

    def test_participant_identifier(self):
        """ exercises the generation of participant_identifier """
        e = self.create_new_experiment()
        for p in self.participants:
            per = ParticipantExperimentRelationship.objects.create(participant=p,
                    experiment=e, created_by=self.experimenter.user)
            self.assertTrue(per.id > 0)
            logger.debug("Participant identifier is %s - sequential id is %i", per.participant_identifier, per.sequential_participant_identifier)
            self.assertTrue(per.participant_identifier)
            self.assertTrue(per.sequential_participant_identifier > 0)

        self.assertEqual(e.participants.count(), self.participants.count())


class RoundConfigurationTest(BaseVcwebTest):

    def test_round_configuration_enums(self):
        self.assertEqual(len(RoundConfiguration.ROUND_TYPES), len(RoundConfiguration.ROUND_TYPES_DICT))
        self.assertEqual(RoundConfiguration.PRACTICE, 'PRACTICE')
        self.assertEqual(RoundConfiguration.REGULAR, 'REGULAR')
        choices = RoundConfiguration.ROUND_TYPE_CHOICES
        self.assertEqual(len(choices), len(RoundConfiguration.ROUND_TYPES_DICT))
        for pair in choices:
            self.assertTrue(pair[0] in RoundConfiguration.ROUND_TYPES_DICT.keys())
            self.assertTrue(pair[0] in RoundConfiguration.ROUND_TYPES)
            self.assertFalse(pair[1].isupper())

    def test_get_set_parameter(self):
        e = self.experiment
# current_round is instructions, with no available parameters.
        round_configuration = e.current_round
        name = 'initial.resource_level'
        round_configuration.set_parameter(name=name, value=501)
        self.assertEqual(round_configuration.get_parameter_value(name), 501)
        self.assertEqual(round_configuration.get_parameter(name).value, round_configuration.get_parameter_value(name))

    def test_parameterized_value(self):
        e = self.experiment
        p = Parameter.objects.create(scope='round', name='test_round_parameter', type='int', creator=e.experimenter, experiment_metadata=e.experiment_metadata)
        rp = RoundParameterValue.objects.create(parameter=p, round_configuration=e.current_round, value='14')
        self.assertEqual(14, rp.int_value)


    def test_round_parameters(self):
        e = self.experiment
        p = Parameter.objects.create(scope='round', name='test_round_parameter', type='int', creator=e.experimenter, experiment_metadata=e.experiment_metadata)
        self.assertTrue(p.pk > 0)
        self.assertEqual(p.value_field_name, 'int_value')

        for val in (14, '14', 14.0, '14.0'):
            rp = RoundParameterValue.objects.create(parameter=p, round_configuration=e.current_round, value=val)
            self.assertTrue(rp.pk > 0)
            self.assertEqual(rp.value, 14)

        '''
        The type field in Parameter generates the value_field_name property by concatenating the name of the type with _value.
        '''
        sample_values_for_type = {'int':3, 'float':3.0, 'string':'ich bin ein mublumubla', 'boolean':True}
        for type in ('int', 'float', 'string', 'boolean'):

            p = Parameter.objects.create(scope='round', name="test_nonunique_round_parameter_%s" % type, type=type, creator=e.experimenter, experiment_metadata=e.experiment_metadata)
            self.assertTrue(p.pk > 0)
            self.assertEqual(p.value_field_name, '%s_value' % type)
            rp = RoundParameterValue.objects.create(parameter=p, round_configuration=e.current_round, value=sample_values_for_type[type])
            self.assertEqual(rp.value, sample_values_for_type[type])


    def test_get_templates(self):
        e = self.experiment
        for round_type, data in RoundConfiguration.ROUND_TYPES_DICT.items():
            logger.debug("inspecting round type: %s with data %s", round_type, data)
            rc = self.create_new_round_configuration(round_type=round_type)
            e.current_round_sequence_number = rc.sequence_number
            self.assertEqual(e.current_round_template, "%s/%s" % (e.namespace, data[1]), 'should have returned template for ' + data[0])
