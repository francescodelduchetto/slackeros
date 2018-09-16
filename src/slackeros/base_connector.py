import web

import logging
from pprint import pformat
from json import dumps
from os import _exit
import signal
from requests import post
from os import environ

logging.basicConfig(level=logging.DEBUG)


def __signal_handler(signum, frame):
    print "stopped."
    _exit(signal.SIGTERM)


class SlackConnector(web.application):
    """
    Baseclass Slack Connector for Slash commands and incoming webhooks
    see https://api.slack.com/incoming-webhooks
    see https://api.slack.com/slash-commands
    configure at https://api.slack.com/apps/
    * slash webhook should be https://THISERVER:THISPORT/[PREFIX/]slash/PARAM
    * incoming webhook needs to be enabled and given here as argument
    """

    def __init__(
        self,
        incoming_webhook=None,
        whitelist_channels=[],
        whitelist_users=[],
        prefix=''
    ):
        self.incoming_webhook = incoming_webhook
        self.whitelist_channels = set(whitelist_channels)
        self.whitelist_users = set(whitelist_users)
        self.urls = (
            prefix + '/slash/(.+)', 'slash_dispatcher'
        )

        web.application.__init__(self, self.urls, SlackConnector.__dict__)
        web.config.update({"controller": self})

    class index():
        def GET(self):
            controller = web.config.controller
            return pformat(controller)

    class slash_dispatcher():
        def GET(self, param):
            return web.notacceptable()

        def POST(self, param):
            payload = dict(web.input())
            web.header('Content-Type', 'application/json')
            ret = {
                'text': (
                            '*Sorry, the channel "%s" or the user "%s" are not'
                            ' permitted to run this command.*' % (
                                payload['channel_id'],
                                payload['user_name']
                            )
                        )
            }
            controller = web.config.controller
            if (
                (
                    not bool(controller.whitelist_channels) or
                    payload['channel_id'] in controller.whitelist_channels
                ) and (
                    not bool(controller.whitelist_users) or
                    payload['user_name'] in controller.whitelist_users
                )
            ):
                cb_ret = controller.on_slash(param, payload)
                ret = controller._generate_message(cb_ret)
            return dumps(ret)

    def _generate_message(self, msg):
        if type(msg) is dict:
            ret = msg
        else:
            ret = {
                'text': str(msg)
            }
        ret["response_type"] = "in_channel"
        return ret

    def send(self, msg):
        if self.incoming_webhook:
            post(self.incoming_webhook, json=self._generate_message(msg))

    def on_slash(self, param, payload):
        ret = {
            'text': '_default handler called_',
            'attachments': [
                {
                    "title": "Synopsis",
                    "text": "```\n%s\n```" % pformat(payload)
                }
            ]
        }
        self.send('incoming!')
        logging.info('on_slash(%s, %s)', param, pformat(payload))
        return ret

    def run(self):
        web.application.run(self)

if __name__ == '__main__':
    signal.signal(signal.SIGINT, __signal_handler)

    sc = SlackConnector(
        incoming_webhook=environ.get(
            'SLACK_WEBHOOK',
            'https://hooks.slack.com/services/'
            'TCTBP6280/BCU8QFBE1/l2B4r7TRzLJJ37zyhXqtICov'),
        whitelist_users=['mhanheide']
    )
    sc.run()