import nsq
import tornado.ioloop
import time


def pub_message():
    timestamp = time.strftime('%H:%M:%S').encode()
    print(timestamp, end=' ')
    writer.pub('skripsi', timestamp, finish_pub)


def finish_pub(conn, data):
    print(data)


writer = nsq.Writer(['localhost:4150'])
tornado.ioloop.PeriodicCallback(pub_message, 1000).start()
nsq.run()
