# Graceful aio-pika rabbitmq consumer terminate example, with message ack on termination

Example of consuming messages from rabbitmq, with mandatory ack message on terminate or Ctrl+C signal received.
Once I had a need of an asynchronous service that would consume the rabbit queue by executing commands from messages. I faced with the peculiarity of the asynchronous context manager message.process() in case when application terminates. Whatever settings I applied for message.process(requeue=False/True) and others, in all cases the message was not acknowledged and remained in the queue after the service stop. But I needed to confirm the message in any case. Acking the message immediately upon receipt was also not suitable, the next one was immediately received by async consumer.

This example is an attempt to create a service that tries to ack a message that has consumed and is processing even if a service terminates.

### Prerequisites
RabbitMQ message queue as source of data;

### Deployment
docker build . -t aio-pika-run

### CLI arguments
--amqp-url  default value: --amqp-url=amqp://guest:guest@localhost:5672

### Testing
After executing aio_pika_run.py with necessary --amqp-url, it will print a pid of its process in terminal log. It will consume a message from 'test_queue' and wait for 300sec to emulate message processing. You can terminate message processing by Ctrl+C or by sending shell command 'kill <pid_no>' from a terminal. Message will ack and then consumer service will stop.