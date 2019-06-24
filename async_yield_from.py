# python 3.x
__author__ = 'lybroman@hotmail.com'

import socket
import selectors
selector = selectors.DefaultSelector()
stopped = False
urls_todo = {'/1', '/2', '/3'}


class Task(object):
    def __init__(self, coro):
        self.coro = coro
        f = Future()
        f.set_result(None)
        self.step(f)

    def step(self, future):
        try:
            next_future = self.coro.send(future.result)
        except StopIteration:
            print("All sub-tasks are done!")
            return

        next_future.add_done_callback(self.step)


class Future(object):
    def __init__(self):
        self.result = None
        self._callbacks = []

    def set_result(self, result):
        self.result = result
        for fn in self._callbacks:
            fn(self)

    def add_done_callback(self, fn):
        self._callbacks.append(fn)

    def __iter__(self):
        result = yield self
        # result of yield from
        return result


class AsyncSocket(object):
    def __init__(self, url, address):
        self._sock = socket.socket()
        self.url = url
        self.address = address

    def connect(self):
        self._sock.setblocking(False)
        try:
            self._sock.connect(self.address)
        except BlockingIOError:
            pass

        f = Future()

        def callback():
            f.set_result(None)

        selector.register(self._sock.fileno(), selectors.EVENT_WRITE, callback)

        yield from f

        selector.unregister(self._sock.fileno())

    def send(self):
        content = 'GET {0} HTTP/1.0\r\nHost: example.com\r\n\r\n'.format(self.url)
        self._sock.send(content.encode('ascii'))

    def read(self, chunk_size=4096):
        f = Future()

        def callback():
            f.set_result(self._sock.recv(4096))

        selector.register(self._sock.fileno(), selectors.EVENT_READ, callback)
        chunk = yield from f
        selector.unregister(self._sock.fileno())
        self._sock.recv(chunk_size)
        return chunk

    def read_all(self):
        response = ''
        while True:
            chunk = yield from self.read(4096)
            if chunk:
                response += str(chunk)
            else:
                break

        return response


class Crawler(object):
    def __init__(self, url, address):
        self.url = url
        self.response = ''
        self.async_socket = AsyncSocket(url, address)

    def fetch(self):
        yield from self.async_socket.connect()
        self.async_socket.send()
        self.response = yield from self.async_socket.read_all()
        # print(self.response)
        urls_todo.remove(self.url)
        if not urls_todo:
            global stopped
            stopped = True


for url in urls_todo:
    Task(Crawler(url, ('example.com', 80)).fetch())

while not stopped:
    events = selector.select()
    for event_key, event_mask in events:
        callback = event_key.data
        callback()


