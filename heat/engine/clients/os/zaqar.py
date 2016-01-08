#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from oslo_log import log as logging

from heat.common.i18n import _LE

LOG = logging.getLogger(__name__)

from zaqarclient.queues.v1 import client as zaqarclient
from zaqarclient.transport import errors as zaqar_errors

from heat.engine.clients import client_plugin

CLIENT_NAME = 'zaqar'


class ZaqarClientPlugin(client_plugin.ClientPlugin):

    exceptions_module = zaqar_errors

    service_types = [MESSAGING] = ['messaging']

    DEFAULT_TTL = 3600

    def _create(self):
        return self.create_for_tenant(self.context.tenant_id, self.auth_token)

    def create_for_tenant(self, tenant_id, token):
        con = self.context
        if token is None:
            LOG.error(_LE("Zaqar connection failed, no auth_token!"))
            return None

        opts = {
            'os_auth_token': token,
            'os_auth_url': con.auth_url,
            'os_project_id': tenant_id,
            'os_service_type': self.MESSAGING,
        }
        auth_opts = {'backend': 'keystone',
                     'options': opts}
        conf = {'auth_opts': auth_opts}
        endpoint = self.url_for(service_type=self.MESSAGING)

        client = zaqarclient.Client(url=endpoint, conf=conf, version=1.1)

        return client

    def is_not_found(self, ex):
        return isinstance(ex, zaqar_errors.ResourceNotFound)


class ZaqarEventSink(object):

    def __init__(self, target, ttl=None):
        self._target = target
        self._ttl = ttl

    def consume(self, context, event):
        zaqar_plugin = context.clients.client_plugin('zaqar')
        zaqar = zaqar_plugin.client()
        queue = zaqar.queue(self._target, auto_create=False)
        ttl = self._ttl if self._ttl is not None else zaqar_plugin.DEFAULT_TTL
        queue.post({'body': event, 'ttl': ttl})
