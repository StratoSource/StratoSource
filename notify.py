
#import pika
#import sys


#try:
#  connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
#  channel = connection.channel()
#  channel.exchange_declare(exchange='notices', type='fanout')
#except Exception as ex:
#  print 'MQ broker not found on localhost, disabling publishing'
#  print ex
#  exit(0)
#
#channel.basic_publish(exchange='notices', routing_key='', body=sys.argv[1])
#connection.close()

