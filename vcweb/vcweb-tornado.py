#!/usr/bin/env python

import tornado.web
from tornad_io import SocketIOHandler
from tornad_io import SocketIOServer

import os
import sys
import logging

logger = logging.getLogger(__name__)

sys.path.append(os.path.abspath('..'))

os.environ['DJANGO_SETTINGS_MODULE'] = 'vcweb.settings'

from vcweb.core.models import ParticipantGroupRelationship, ChatMessage, Experiment

'''
store mappings between beaker session ids and ParticipantGroupRelationship pks
'''
class SessionManager:
    ''' associates beaker session ids with ParticipantGroupRelationship.pks '''
    session_id_to_participant = {}
    ''' the reverse mapping, associates ParticipantGroupRelationship.pks with the beaker session '''
    pgr_to_session = {}

    def get_participant(self, session):
        logger.debug("trying to retrieve participant group relationship for session id %s" % session)
        logger.debug("maps are %s and %s" % (self.session_id_to_participant, self.pgr_to_session))
        return ParticipantGroupRelationship.objects.get(pk=self.session_id_to_participant[session.id])

    def add(self, session, participant_group_relationship):
        if participant_group_relationship.pk in self.pgr_to_session:
            logger.debug("participant already has a session, removing previous mappings.")
            self.remove(self.pgr_to_session[participant_group_relationship.pk])

        self.session_id_to_participant[session.id] = participant_group_relationship.pk
        self.pgr_to_session[participant_group_relationship.pk] = session

    def remove(self, session):
        try:
            participant_group_pk = self.session_id_to_participant[session.id]
            del self.pgr_to_session[participant_group_pk]
            del self.session_id_to_participant[session.id]
        except KeyError, k:
            logger.warning( "caught key error %s while trying to remove session %s" % (session, k) )
            pass

    '''
    Generator function that yields (participant_group_relationship_id, beaker session object) tuples
    for the given group
    '''
    def sessions(self, group):
        pgr_ids = [ pgr.pk for pgr in group.participant_group_relationships.all() ]
        for pgr_id in pgr_ids:
            ''' only return currently connected sessions in this group '''
            if pgr_id in self.pgr_to_session:
                yield (pgr_id, self.pgr_to_session[pgr_id])
            pass

class Struct:
    def __init__(self, **attributes):
        self.__dict__.update(attributes)

def to_event(message):
    return Struct(**message)

class IndexHandler(tornado.web.RequestHandler):
    """Test HTTP handler to serve the chatroom page if we hit host:8888 manually"""
    def get(self):
        self.render("chat.html")

'''
FIXME: make this a class / instance var on ChatHandler? But then it forces us to
type ChatHandler.session_manager instead of just session_manager...
'''
session_manager = SessionManager()

class ChatHandler(SocketIOHandler):
    def on_open(self, *args, **kwargs):
        ''' parse args / kwargs for participant session info so we know which group
        to route this guy to
        '''
        logger.debug("kwargs are: %s" % str(kwargs))
        logger.debug("session is %s" % self.session)

    def on_message(self, message):
        ''' incoming JSON message gets converted to a Python dict via simplejson '''
        logger.debug("received message %s from handler %s" % (message, self))
        logger.debug("handler session is %s" % self.session)
        event = to_event(message)
        if event.type == 'connect':
            participant_group_rel = ParticipantGroupRelationship.objects.get(participant__pk=event.participant_id,
                    group__pk=event.group_id)
            logger.debug("%s joined %s" % (participant_group_rel.participant, participant_group_rel.group))
            event.message = "<div>Participant %s joined group %s chat.</div>" % (participant_group_rel.participant_number, participant_group_rel.group)
            session_manager.add(self.session, participant_group_rel)
            for participant_group_pk, session in session_manager.sessions(participant_group_rel.group):
                session['output_handle'].send(event.message)
            return
        elif event.type == 'experimenter':
            experiment = Experiment.objects.get(pk=event.experiment_id)
            # TODO: should add a second handler just for experimenters with 
            # auth handling
            logger.debug("sending message %s to all participants" %
                  event.message)
            for g in experiment.groups.all():
               for participant_group_pk, session in session_manager.sessions(g):
                  session['output_handle'].send(event.message)
            return
        else:
            # check session id..
            participant_group_rel = session_manager.get_participant(self.session)
            current_round_data = participant_group_rel.group.experiment.current_round_data

            chat_message = ChatMessage.objects.create(participant_group_relationship=participant_group_rel,
                    message=event.message,
                    round_data=current_round_data
                    )
            for participant_group_pk, session in session_manager.sessions(participant_group_rel.group):
                logger.debug("sending message %s to participant %s" % (chat_message, participant_group_rel.participant))
                session['output_handle'].send(chat_message.as_html)

    def on_close(self):
        logger.debug("closing %s" % self)
        session_manager.remove(self.session)

def main(argv=None):
    if argv is None:
        argv = sys.argv
    # use the routes classmethod to build the correct resource
    chatRoute = ChatHandler.routes("chat", extraRE=r'[\w._=]+', extraSep='/')
    # configure the Tornado application
    # currently only allow one command-line argument, the port to run on.
    port = int(argv[1]) if (len(argv) > 1) else 8888

    application = tornado.web.Application(
            [(r'/', IndexHandler), chatRoute],
            enabled_protocols=['websocket', 'flashsocket', 'xhr-multipart', 'xhr-polling'],
            flash_policy_port=8043,
            flash_policy_file='/etc/nginx/flashpolicy.xml',
            socket_io_port=port,
            # only needed for standalone testing
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            )
    return SocketIOServer(application)

if __name__ == "__main__":
    sys.exit(main())
