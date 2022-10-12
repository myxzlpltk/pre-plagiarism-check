import nsq


def handler(message):
    print(message.body)
    return True


r = nsq.Reader(message_handler=handler,
               lookupd_http_addresses=['http://localhost:4161'],
               topic='skripsi', channel='method5', lookupd_poll_interval=15)
nsq.run()
