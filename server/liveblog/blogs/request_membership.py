# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


from superdesk.resource import Resource
from liveblog.common import get_user
import logging
from superdesk.activity import add_activity
from superdesk import get_resource_service
from flask import current_app as app, render_template
from bson.objectid import ObjectId
from superdesk.notification import push_notification
from superdesk.services import BaseService
from superdesk.emails import send_email
from flask import g
from superdesk.errors import SuperdeskApiError

logger = logging.getLogger('superdesk')


def notify_the_owner(doc, origin):
    if not get_user():
        logger.info('there is no logged in user so no membership is allowed')
    else:
        blog = get_resource_service('blogs').find_one(req=None, _id=doc.get('blog'))
        owner = blog.get('original_creator')
        add_activity('notify', 'one user requested liveblog membership', resource=None, item=doc, notify=str(owner))
        send_email_to_owner(doc, owner, origin)


def send_email_to_owner(doc, owner, origin):
    blog = get_resource_service('blogs').find_one(req=None, _id=doc.get('blog'))
    prefs_service = get_resource_service('preferences')
    if prefs_service.email_notification_is_enabled(user_id=doc['original_creator']):
        user_doc = get_resource_service('users').find_one(req=None, _id=doc['original_creator'])
        recipients = user_doc['email']
    if recipients:
        username = g.user.get('display_name') or g.user.get('username')
        url = '{}/#/liveblog/settings/{}'.format(origin, doc['_id'])
        title = blog['title']
        admins = app.config['ADMINS']
        app_name = app.config['APPLICATION_NAME']
        subject = render_template("owner_email_subject.txt", app_name=app_name)
        text_body = render_template("owner_request.txt", app_name=app_name, link=url,
                                    name_of_user=username, title=title)
        html_body = render_template("owner_request.html", app_name=app_name, link=url,
                                    name_of_user=username, title=title)
        send_email.delay(subject=subject, sender=admins[0], recipients=recipients,
                         text_body=text_body, html_body=html_body)


request_schema = {
    'blog': Resource.rel('blogs', True),
    'original_creator': Resource.rel('users', True),
    'message': {
        'type': 'string'
    }
}


class MembershipResource(Resource):
    schema = request_schema
    datasource = {
        'source': 'request_membership',
        'default_sort': [('_updated', -1)]
    }
    resource_methods = ['POST']
    privileges = {'POST': 'request_membership'}


class MembershipService(BaseService):
    notification_key = 'request'

    def on_create(self, docs):
        for doc in docs:
            doc['original_creator'] = str(get_user().get('_id'))
            request_service = get_resource_service('request_membership').get(req=None, lookup={})
            if request_service:
                for r in request_service:
                    if (str(get_user().get('_id')) == r['original_creator']):
                        raise SuperdeskApiError.badRequestError(message='A request has already been sent')
        super().on_create(docs)

    def on_created(self, docs):
        for doc in docs:
            push_notification(self.notification_key, created=1, request_id=str(doc.get('_id')))
        # and members with emails
            notify_the_owner(doc, app.config['CLIENT_URL'])


class MemberListResource(Resource):
    url = 'blogs/<regex("[a-f0-9]{24}"):blog_id>/request_membership'
    schema = request_schema
    datasource = {
        'source': 'request_membership'
    }
    resource_methods = ['GET']


class MemberListService(BaseService):
    def get(self, req, lookup):
        if lookup.get('blog_id'):
            lookup['blog'] = ObjectId(lookup['blog_id'])
            del lookup['blog_id']
        docs = super().get(req, lookup)
        return docs
