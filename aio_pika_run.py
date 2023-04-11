import argparse
import asyncio
import logging
import os
import signal
import aio_pika


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s,%(msecs)d %(levelname)s %(filename)s:%(lineno)s - %(funcName)s: %(message)s",
    datefmt="%H:%M:%S",
)


class Consumers:
    def __init__(self) -> None:
        self.tasks: set[asyncio.Task] = set()
        
    def add_consumer(self, task: asyncio.Task) -> None:
        self.tasks.add(task)
    
    def remove_consumer(self, task: asyncio.Task) -> None:
        if task in self.tasks:
            self.tasks.remove(task)
    
    def cancel_all(self) -> None:
        for _task in self.tasks:
            _task.cancel()
    
    async def wait_all(self) -> None:
        pending_tasks = [_task for _task in self.tasks if not _task.done() and not _task.cancelled()]
        await asyncio.gather(*pending_tasks)


rabbit_kill_event: asyncio.Event = asyncio.Event()
consumers = Consumers()


async def process_message_with_simple_await(message: aio_pika.abc.AbstractIncomingMessage) -> None:
    global consumers
    async with message.process(requeue=False):
        current_task = asyncio.current_task()
        try:
            logging.info(f"Add current task: {current_task.get_name()} to consumers set")
            consumers.add_consumer(current_task)
            logging.info(message.body)
            
            await asyncio.sleep(300)
        except asyncio.CancelledError:
            logging.info(f"Task {current_task.get_name()} was cancelled")
        else:
            consumers.remove_consumer(current_task)


async def process_message_with_wait_other_tasks(message: aio_pika.abc.AbstractIncomingMessage) -> None:
    global consumers
    async with message.process(requeue=False):
        current_task = asyncio.current_task()
        try:
            logging.info(f"Add current task: {current_task.get_name()} to consumers set")
            consumers.add_consumer(current_task)
            logging.info(message.body)
            
            task_list = [asyncio.create_task(asyncio.sleep(300))]
            done, pending = await asyncio.wait(task_list, return_when=asyncio.ALL_COMPLETED)
            for done_task in done:
                if done_task.exception():
                    logging.error(f"Exception in task {done_task.get_name()}", exc_info=done_task.exception())
            for pending_task in pending:
                pending_task.cancel()
        except asyncio.CancelledError:
            logging.info(f"Task {current_task.get_name()} was cancelled")
        else:
            consumers.remove_consumer(current_task)


async def shutdown(s: signal.Signals):
    global rabbit_kill_event, consumers
    logging.info(f"Received exit signal {s.name}...")
    consumers.cancel_all()
    rabbit_kill_event.set()


async def main(args) -> None:
    
    loop = asyncio.get_running_loop()
    signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)
    for s in signals:
        loop.add_signal_handler(
            s, lambda s=s: asyncio.create_task(shutdown(s))
        )
    
    connection = await aio_pika.connect_robust(args.amqp_url)
    try:
        async with connection:
            channel: aio_pika.RobustChannel = await connection.channel()
            await channel.set_qos(prefetch_count=1)
            queue: aio_pika.RobustQueue = await channel.declare_queue("test_queue", durable=True, auto_delete=False)
            await queue.consume(process_message_with_simple_await)
            # await queue.consume(process_message_with_wait_other_tasks)
            # Waiting for SIGTERM or KeybordInterrupt
            await rabbit_kill_event.wait()
            # Waiting for all consumer tasks is finished ()
            await consumers.wait_all()
    except KeyboardInterrupt as kie:
        logging.error("Keyboard interrupt", exc_info=kie)
        await shutdown(signal.SIGINT)
    
    logging.info("Exiting...")
    

def init_argparse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Graceful aio-pika rabbitmq consumer shutdown example with message ack on term"
    )
    parser.add_argument("--amqp-url", default="amqp://guest:guest@localhost:5672", type=str,
                        help="Rabbitmq amqp url string like 'amqp://guest:guest@localhost:5672' to connect")
    return parser

    
if __name__ == "__main__":
    parser = init_argparse()
    args = parser.parse_args()
    
    logging.info(f"pid: {os.getpid()}")
    asyncio.run(main(args), debug=True)
