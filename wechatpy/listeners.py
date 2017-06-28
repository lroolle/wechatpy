
import pika
import logging

log = logging.getLogger('assbot')


def rooms_listener(callback, queue='room'):
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host='localhost'))

    channel = connection.channel()
    channel.queue_declare(queue=queue)

    channel.basic_consume(
        callback,
        queue=queue,
        no_ack=True,
    )
    log.info('%s listener start consuming' % queue)
    channel.start_consuming()


LISTENERS = [
    rooms_listener,
]
