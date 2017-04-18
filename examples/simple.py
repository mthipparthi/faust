import asyncio
import faust
import io
import os
import sys
from faust.sensors import Sensor

GRAPH = os.environ.get('GRAPH')


class Withdrawal(faust.Record, serializer='json'):
    user: str
    amount: float


topic = faust.topic('f-simple', value_type=Withdrawal)

app = faust.App('f-simple', url='kafka://localhost:9092')
user_to_total = app.table('user_to_total', default=int)

async def find_large_withdrawals(app):
    if GRAPH:
        asyncio.ensure_future(_dump_beacon(app))
    async for key, withdrawal in app.stream(topic).items():
        print('%r Withdrawal: %r' % (key, withdrawal,))
        user_to_total[withdrawal.user] += withdrawal.amount
        if withdrawal.amount > 9999.0:
            print('ALERT: large withdrawal: {0.amount!r}'.format(withdrawal))
        print('CURRENT_TOTAL: %r' % (user_to_total[withdrawal.user],))




async def _dump_beacon(app):
    await asyncio.sleep(4)
    print(app.render_graph())


async def _publish_withdrawals():
    for i in range(100):
        print('+SEND %r' % (i,))
        await app.send(topic, b'K', Withdrawal(user='foo', amount=100.3 + i))
        print('-SEND %r' % (i,))
    await app.send(topic, b'K', Withdrawal(user='foo', amount=999999.0))
    await asyncio.sleep(30)


def produce(loop):
    loop.run_until_complete(_publish_withdrawals())


def consume(loop):
    app.add_task(find_large_withdrawals(app))
    worker = faust.Worker(app, loglevel='INFO', loop=loop)
    worker.execute_from_commandline()
    loop.run_forever()


COMMANDS = {
    'consume': consume,
    'produce': produce,
}


def main(loop=None):
    loop = loop or asyncio.get_event_loop()
    try:
        COMMANDS[sys.argv[1]](loop=loop)
    except KeyError as exc:
        print('Unknown command: {0}'.format(exc))
        raise SystemExit(os.EX_USAGE)
    except IndexError:
        print('Missing command. Try one of: {0}'.format(', '.join(COMMANDS)))
        raise SystemExit(os.EX_USAGE)
    finally:
        loop.close()


if __name__ == '__main__':
    main()
