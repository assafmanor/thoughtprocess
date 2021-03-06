import pika
from .abstractmq import AbstractMQ
from .mq_registrator import MessageQueueRegistrator
from .exceptions import MQConnectionError


@MessageQueueRegistrator.register('rabbitmq')
class RabbitMQ(AbstractMQ):
    def __init__(self, connection, channel):
        self.connection = connection
        self.channel = channel

    @classmethod
    def connect(cls, host, port):
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host, port))
        except pika.exceptions.AMQPConnectionError as e:
            raise MQConnectionError(e.__str__())
        channel = connection.channel()
        return cls(connection, channel)

    def declare_queue(self, name):
        self.channel.queue_declare(queue=name)

    def declare_exchange(self, name):
        self.channel.exchange_declare(exchange=name,
                                      exchange_type='fanout')

    def consume_queue(self, name, callback):
        valid_callback = lambda ch, method, properties, body: callback(body)
        self.channel.basic_consume(queue=name,
                                   auto_ack=True,
                                   on_message_callback=valid_callback)

    def consume_exchange(self, name, callback):
        result = self.channel.queue_declare(queue='', exclusive=True)
        queue_name = result.method.queue
        self.channel.queue_bind(exchange=name,
                                queue=queue_name)
        self.consume_queue(queue_name, callback)
        self.start_consuming()

    def start_consuming(self):
        self.channel.start_consuming()

    def publish(self, message, exchange_name='', queue_name=''):
        try:
            self.channel.basic_publish(exchange=exchange_name,
                                       routing_key=queue_name,
                                       body=message)
        except pika.exceptions.ChannelWrongStateError:
            raise MQConnectionError("channel is closed")
        except pika.exceptions.StreamLostError:
            raise MQConnectionError("connection reset")

    
