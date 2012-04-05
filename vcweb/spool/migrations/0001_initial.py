# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'ExperimentSession'
        db.create_table('spool_experimentsession', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('experiment', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.Experiment'])),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('scheduled_date', self.gf('django.db.models.fields.DateTimeField')()),
            ('scheduled_end_date', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('capacity', self.gf('django.db.models.fields.PositiveIntegerField')(default=20)),
            ('creator', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
        ))
        db.send_create_signal('spool', ['ExperimentSession'])

        # Adding model 'Invitation'
        db.create_table('spool_invitation', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('participant', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.Participant'])),
            ('experiment_session', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['spool.ExperimentSession'])),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('sender', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
        ))
        db.send_create_signal('spool', ['Invitation'])

        # Adding model 'ParticipantSignup'
        db.create_table('spool_participantsignup', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('participant', self.gf('django.db.models.fields.related.ForeignKey')(related_name='signup_set', to=orm['core.Participant'])),
            ('invitation', self.gf('django.db.models.fields.related.ForeignKey')(related_name='signup_set', to=orm['spool.Invitation'])),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('attendance', self.gf('django.db.models.fields.CharField')(max_length=1, null=True, blank=True)),
        ))
        db.send_create_signal('spool', ['ParticipantSignup'])

        # Adding model 'FaqEntry'
        db.create_table('spool_faqentry', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('creator', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('last_modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('question', self.gf('django.db.models.fields.TextField')()),
            ('answer', self.gf('django.db.models.fields.TextField')()),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=32)),
        ))
        db.send_create_signal('spool', ['FaqEntry'])

        # Adding model 'ParticipantStatistics'
        db.create_table('spool_participantstatistics', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('participant', self.gf('django.db.models.fields.related.ForeignKey')(related_name='statistics_set', to=orm['core.Participant'])),
            ('absences', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('discharges', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('participations', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
        ))
        db.send_create_signal('spool', ['ParticipantStatistics'])

    def backwards(self, orm):
        # Deleting model 'ExperimentSession'
        db.delete_table('spool_experimentsession')

        # Deleting model 'Invitation'
        db.delete_table('spool_invitation')

        # Deleting model 'ParticipantSignup'
        db.delete_table('spool_participantsignup')

        # Deleting model 'FaqEntry'
        db.delete_table('spool_faqentry')

        # Deleting model 'ParticipantStatistics'
        db.delete_table('spool_participantstatistics')

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'core.experiment': {
            'Meta': {'ordering': "['date_created', 'status']", 'object_name': 'Experiment'},
            'amqp_exchange_name': ('django.db.models.fields.CharField', [], {'default': "'vcweb.default.exchange'", 'max_length': '64'}),
            'authentication_code': ('django.db.models.fields.CharField', [], {'default': "'vcweb.auth.code'", 'max_length': '32'}),
            'current_round_elapsed_time': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'current_round_sequence_number': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'current_round_start_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'duration': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'experiment_configuration': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.ExperimentConfiguration']"}),
            'experiment_metadata': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.ExperimentMetadata']"}),
            'experimenter': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Experimenter']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_experimenter_driven': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '32', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'start_date_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'INACTIVE'", 'max_length': '32'}),
            'tick_duration': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'total_elapsed_time': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'})
        },
        'core.experimentconfiguration': {
            'Meta': {'ordering': "['experiment_metadata', 'creator', 'date_created']", 'object_name': 'ExperimentConfiguration'},
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'experiment_configuration_set'", 'to': "orm['core.Experimenter']"}),
            'date_created': ('django.db.models.fields.DateField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'experiment_metadata': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'experiment_configuration_set'", 'to': "orm['core.ExperimentMetadata']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'max_group_size': ('django.db.models.fields.PositiveIntegerField', [], {'default': '5'}),
            'max_number_of_participants': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'core.experimenter': {
            'Meta': {'ordering': "['user']", 'object_name': 'Experimenter'},
            'approved': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'authentication_token': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'failed_password_attempts': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'institution': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Institution']", 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'experimenter'", 'unique': 'True', 'to': "orm['auth.User']"})
        },
        'core.experimentmetadata': {
            'Meta': {'ordering': "['namespace', 'date_created']", 'object_name': 'ExperimentMetadata'},
            'about_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'date_created': ('django.db.models.fields.DateField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'default_configuration': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.ExperimentConfiguration']", 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'logo_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'namespace': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'short_name': ('django.db.models.fields.SlugField', [], {'max_length': '32', 'unique': 'True', 'null': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'core.group': {
            'Meta': {'ordering': "['experiment', 'number']", 'object_name': 'Group'},
            'experiment': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Experiment']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_size': ('django.db.models.fields.PositiveIntegerField', [], {'default': '5'}),
            'number': ('django.db.models.fields.PositiveIntegerField', [], {})
        },
        'core.institution': {
            'Meta': {'object_name': 'Institution'},
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'})
        },
        'core.participant': {
            'Meta': {'ordering': "['user']", 'object_name': 'Participant'},
            'authentication_token': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'can_receive_invitations': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'experiments': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'participant_set'", 'symmetrical': 'False', 'through': "orm['core.ParticipantExperimentRelationship']", 'to': "orm['core.Experiment']"}),
            'failed_password_attempts': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'participant_set'", 'symmetrical': 'False', 'through': "orm['core.ParticipantGroupRelationship']", 'to': "orm['core.Group']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'institution': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Institution']", 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'participant'", 'unique': 'True', 'to': "orm['auth.User']"})
        },
        'core.participantexperimentrelationship': {
            'Meta': {'object_name': 'ParticipantExperimentRelationship'},
            'additional_data': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'current_location': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'experiment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'participant_relationship_set'", 'to': "orm['core.Experiment']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_completed_round_sequence_number': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'participant': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'experiment_relationship_set'", 'to': "orm['core.Participant']"}),
            'participant_identifier': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'sequential_participant_identifier': ('django.db.models.fields.PositiveIntegerField', [], {})
        },
        'core.participantgrouprelationship': {
            'Meta': {'ordering': "['group', 'participant_number']", 'object_name': 'ParticipantGroupRelationship'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'participant_group_relationship_set'", 'to': "orm['core.Group']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'notifications_since': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'participant': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'participant_group_relationship_set'", 'to': "orm['core.Participant']"}),
            'participant_number': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'round_joined': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.RoundConfiguration']"})
        },
        'core.roundconfiguration': {
            'Meta': {'ordering': "['experiment_configuration', 'sequence_number', 'date_created']", 'object_name': 'RoundConfiguration'},
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'debriefing': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'display_number': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'duration': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'experiment_configuration': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'round_configuration_set'", 'to': "orm['core.ExperimentConfiguration']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'instructions': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'round_type': ('django.db.models.fields.CharField', [], {'default': "'REGULAR'", 'max_length': '32'}),
            'sequence_number': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'template_name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'})
        },
        'spool.experimentsession': {
            'Meta': {'object_name': 'ExperimentSession'},
            'capacity': ('django.db.models.fields.PositiveIntegerField', [], {'default': '20'}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'experiment': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Experiment']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'scheduled_date': ('django.db.models.fields.DateTimeField', [], {}),
            'scheduled_end_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
        },
        'spool.faqentry': {
            'Meta': {'object_name': 'FaqEntry'},
            'answer': ('django.db.models.fields.TextField', [], {}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'question': ('django.db.models.fields.TextField', [], {}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '32'})
        },
        'spool.invitation': {
            'Meta': {'object_name': 'Invitation'},
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'experiment_session': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['spool.ExperimentSession']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'participant': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Participant']"}),
            'sender': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'spool.participantsignup': {
            'Meta': {'object_name': 'ParticipantSignup'},
            'attendance': ('django.db.models.fields.CharField', [], {'max_length': '1', 'null': 'True', 'blank': 'True'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invitation': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'signup_set'", 'to': "orm['spool.Invitation']"}),
            'participant': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'signup_set'", 'to': "orm['core.Participant']"})
        },
        'spool.participantstatistics': {
            'Meta': {'object_name': 'ParticipantStatistics'},
            'absences': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'discharges': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'participant': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'statistics_set'", 'to': "orm['core.Participant']"}),
            'participations': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'})
        }
    }

    complete_apps = ['spool']