
import pika
import sys
import json
from datetime import datetime


class MQClient:

    def __init__(self, exch = 'notices'):
        self.connection = None
        self.channel = None
        self.exchange = exch
        try:
            self.connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
            self.channel = self.connection.channel()
            self.channel.exchange_declare(exchange=exch, type='fanout')
        except Exception as ex:
#            print 'MQ broker not found on localhost, disabling publishing'
#            print ex
            pass

    def publish(self, message, level = 'info'):
        if not self.channel:
            return
        payload = { 'publisher': 'stratosource', 'level': level, 'when': datetime.now().isoformat() }
        if isinstance(message, str):
            payload['messagetype'] =  'string'
            payload['message'] = message
        elif isinstance(message, dict):
            payload['messagetype'] =  'json'
            payload['payload'] = message
        print('!!! PAYLOAD !!!!')
        print(payload)
        self.channel.basic_publish(exchange=self.exchange, routing_key='', body=json.dumps(payload))
        return self

    def close(self):
        if not self.connection: return
        self.connection.close()


if __name__ == '__main__':
  mq = MQClient()
  mq.publish(sys.argv[1])

