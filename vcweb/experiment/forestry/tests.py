from vcweb.core.models import (GroupRoundDataValue, ParticipantExperimentRelationship)
from vcweb.core.tests import BaseVcwebTest
from vcweb.experiment.forestry.models import *

import logging

logger = logging.getLogger(__name__)


class BaseTest(BaseVcwebTest):
    pass


class ForestryRoundSignalTest(BaseTest):
    def verify_resource_level(self, group, value=100):
        self.assertEqual(get_resource_level(group), value)

    def test_round_ended_signal(self):
        e = self.test_round_started_signal()
        self.verify_round_ended(e, lambda e: e.end_round(sender=EXPERIMENT_METADATA_NAME))

    def test_round_started_signal(self):
        e = self.advance_to_data_round()
        for group in e.group_set.all():
            self.verify_resource_level(group)
        return e

    def test_round_setup(self):
        e = self.advance_to_data_round()
        # manually invoke round_setup, otherwise start_round should work as
        # well (but that's tested in the signal tests)
        round_started_handler(None, e)
        for group in e.group_set.all():
            self.verify_resource_level(group)
        return e

    def verify_round_ended(self, e, end_round_func):
        round_data = e.get_round_data()
        e.end_round()
        harvest_decision_parameter = get_harvest_decision_parameter()
        for group in e.group_set.all():
            ds = get_harvest_decisions(group)
            self.verify_resource_level(group)
            self.assertEqual(len(ds), group.participant_set.count())
            for pgr in group.participant_group_relationship_set.all():
                pdv = ParticipantRoundDataValue.objects.get(
                    parameter=harvest_decision_parameter,
                    participant_group_relationship=pgr,
                    round_data=round_data
                )
                self.assertTrue(pdv.pk > 0)
                self.assertFalse(pdv.value)
                pdv.value = 5
                pdv.save()
        end_round_func(e)

    def test_round_ended(self):
        e = self.test_round_setup()
        self.verify_round_ended(e, lambda experiment: round_ended_handler(None, experiment))


class TransferParametersTest(BaseTest):
    def test_transfer_parameters(self):
        def calculate_expected_resource_level(resource_level, harvested):
            after_harvest = max(resource_level - harvested, 0)
            return min(100, int(after_harvest + (after_harvest * .10)))

        e = self.advance_to_data_round()
        expected_resource_level = 100
        while e.has_next_round:
            current_round_configuration = e.current_round
            if should_reset_resource_level(current_round_configuration, e):
                expected_resource_level = get_initial_resource_level(current_round_configuration)

            if current_round_configuration.is_playable_round:
                max_harvest_decision = get_max_harvest_decision(expected_resource_level)
                for pgr in e.participant_group_relationships:
                    self.assertEquals(get_resource_level(pgr.group), expected_resource_level)
                    set_harvest_decision(pgr, max_harvest_decision)
                expected_resource_level = calculate_expected_resource_level(expected_resource_level, max_harvest_decision * 5)

            e.end_round()
            for group in e.groups:
                self.assertEquals(get_resource_level(group), expected_resource_level, "Group resource levels were not equal")
            e.advance_to_next_round()


class ForestryParametersTest(BaseTest):

    def test_parameters_set_at_round_end(self):
        e = self.advance_to_data_round()
        round_data = e.current_round_data
        group_parameters = (get_regrowth_parameter(), get_group_harvest_parameter(), get_resource_level_parameter())
        # Ending the round to see if the round values are set or not
        e.end_round()
        for group in e.groups:
            for parameter in group_parameters:
                gdv = group.get_data_value(round_data=round_data, parameter=parameter)
                self.assertTrue(gdv.parameter in group_parameters)
                self.assertTrue(gdv)
            # single participant data parameter, harvest decisions
            for pgr in group.participant_group_relationship_set.all():
                prdv = ParticipantRoundDataValue.objects.get(participant_group_relationship=pgr, round_data=round_data, parameter=get_harvest_decision_parameter())
                self.assertTrue(prdv)
                self.assertEquals(prdv.parameter, get_harvest_decision_parameter())

    def test_get_set_harvest_decisions(self):
        e = self.advance_to_data_round()
        # generate harvest decisions
        e.end_round()
        round_data = e.get_round_data()
        harvest_decision_parameter = get_harvest_decision_parameter()
        for group in e.groups:
            ds = get_harvest_decisions(group)
            self.assertEquals(len(ds), group.participant_set.count())
            for p in group.participant_set.all():
                pgr = ParticipantGroupRelationship.objects.get(participant=p, group=group)
                pdv, created = ParticipantRoundDataValue.objects.get_or_create(
                    round_data=round_data,
                    participant_group_relationship=pgr,
                    parameter=harvest_decision_parameter)
                self.assertFalse(created)
                self.assertTrue(pdv.pk > 0)
                self.assertFalse(pdv.value)
                pdv.value = 3
                pdv.save()
            ds = get_harvest_decisions(group)
            self.assertTrue(ds)
            for hd in ds.all():
                self.assertEqual(hd.value, 3)

            for pgr in ParticipantGroupRelationship.objects.filter(group=group):
                set_harvest_decision(participant_group_relationship=pgr, value=5)

            for hd in ds.all():
                self.assertEqual(hd.value, 5)

    def test_simple_cache_parameters(self):
        def verify_cached_data(func):
            self.assertEqual(func(), func())
            self.assertEqual(id(func()), id(func()))

        caching_funcs = (get_harvest_decision_parameter, get_group_harvest_parameter, get_regrowth_parameter,
                         get_resource_level_parameter, get_experiment_metadata)
        for i in range(0, 25):
            for func in caching_funcs:
                verify_cached_data(func)

    def test_simple_cache_parameter_refresh(self):
        def verify_refreshed_data(func):
            self.assertEqual(func(), func())
            a = func()
            b = func(refresh=True)
            self.assertNotEqual(id(a), id(b))
            self.assertEqual(a, b)

        caching_funcs = (get_harvest_decision_parameter, get_group_harvest_parameter, get_regrowth_parameter,
                         get_resource_level_parameter, get_experiment_metadata)
        for i in range(0, 25):
            for func in caching_funcs:
                verify_refreshed_data(func)

    def test_get_set_resource_level(self):
        e = self.advance_to_data_round()
        # should initially be 100
        for group in e.group_set.all():
            resource_level = get_resource_level(group)
            self.assertEqual(resource_level, 100)

        for group in e.group_set.all():
            set_resource_level(group, 3)
            self.assertEqual(get_resource_level(group), 3)

        for group in e.group_set.all():
            set_resource_level(group, 77)
            self.assertEqual(get_resource_level(group), 77)

    def test_group_round_data(self):
        data_round_number = 1
        round_data = None
        for e in self.all_data_rounds():
            self.assertNotEqual(round_data, e.get_round_data())
            round_data = e.get_round_data()
            for data_value in round_data.group_data_value_set.filter(parameter__name='resource_level'):
                self.assertTrue(data_value.pk > 0)
                self.assertEqual('resource_level', data_value.parameter.name)
                data_value.value = 50
                data_value.save()
                self.assertEqual(50, data_value.value)
                data_value.value = 100
                data_value.save()
                self.assertEqual(100, data_value.value)
            self.assertEqual(e.get_round_data().group_data_value_set.count(),
                             GroupRoundDataValue.objects.filter(group__experiment=e, round_data=round_data).count())
            self.assertEqual(e.parameters(scope=Parameter.Scope.GROUP).count(), 3)
            data_round_number += 1

    def test_data_parameters(self):
        e = self.experiment
        self.assertEqual(Parameter.objects.count(), e.parameters().count(),
                "Should have added all %s parameters to Experiment %s" % (Parameter.objects.count(), e))


    def test_data_value_conversion(self):
        e = self.experiment
        e.activate()
        e.start_round()
        round_data = e.get_round_data()
        for data_param in e.parameters(scope=Parameter.Scope.PARTICIPANT):
            for p in self.participants:
                per = ParticipantExperimentRelationship.objects.get(participant=p, experiment=e)
                pgr = ParticipantGroupRelationship.objects.get(group__experiment=e, participant=p)
                prdv = ParticipantRoundDataValue.objects.create(round_data=round_data, participant_group_relationship=pgr, parameter=data_param)
                if data_param.type == 'int':
                    prdv.update_int(per.sequential_participant_identifier * 2)
        round_data = e.get_round_data()
        for p in self.participants:
            participant_data_values = round_data.participant_data_value_set.filter(
                participant_group_relationship__participant=p)
            self.assertEqual(participant_data_values.count(), 6)
            pexpr = e.get_participant_experiment_relationship(p)
            for dv in participant_data_values.filter(parameter__type='int'):
                self.assertEqual(pexpr.sequential_participant_identifier * 2, dv.value)
                self.assertTrue(dv.value)
                self.assertEqual(dv.int_value, pexpr.sequential_participant_identifier * 2)
                self.assertEqual(dv.int_value, dv.value, "int_value should be == value")
                self.assertFalse(dv.string_value)
                self.assertFalse(dv.boolean_value)
                self.assertFalse(dv.float_value)
        e.advance_to_next_round()
        self.assertEqual(10,
                         ParticipantRoundDataValue.objects.filter(round_data=round_data, parameter__type='int').count())