import socket
import selectors
selector = selectors.DefaultSelector()
stopped = False


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


class Crawler(object):
    def __init__(self, url):
        self.url = url
        self.response = ''

    def fetch(self):
        sock = socket.socket()
        sock.setblocking(False)
        try:
            sock.connect(('example.com', 80))
        except BlockingIOError:
            pass

        f = Future()

        def on_connected():
            f.set_result(None)

        selector.register(sock.fileno(), selectors.EVENT_WRITE, on_connected)

        yield f

        selector.unregister(sock.fileno())
        get = 'GET {0} HTTP/1.0\r\nHost: example.com\r\n\r\n'.format(self.url)
        sock.send(get.encode('ascii'))

        global stopped
        while True:
            f = Future()

            def on_readable():
                f.set_result(sock.recv(4096))

            selector.register(sock.fileno(), selectors.EVENT_READ, on_readable)

            chunk = yield f
            selector.unregister(sock.fileno())
            if chunk:
                self.response += str(chunk)
            else:
                urls_todo.remove(self.url)
                if not urls_todo:
                    stopped = True
                break


urls_todo = {'/1', '/2', '/3'}

for url in urls_todo:
    Task(Crawler(url).fetch())

print('event loop...')
while not stopped:
    events = selector.select()
    for event_key, event_mask in events:
        callback = event_key.data
        callback()

