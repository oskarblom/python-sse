from gevent import monkey; monkey.patch_all()
from gevent.wsgi import WSGIServer
from gevent.event import AsyncResult
import gevent

from flask import Flask, render_template, request, Response

import json
import signal
import time

# SSE protocol is described here: https://developer.mozilla.org/en-US/docs/Server-sent_events/Using_server-sent_events
class ServerSentEvent(object):

    def __init__(self, data):
        self.data = data
        self.event = None
        self.id = None
        self.desc_map = {
            self.data : "data",
            self.event : "event",
            self.id : "id"
        }

    def encode(self):
        if not self.data:
            return ""
        lines = ["%s: %s" % (v, k) for k, v in self.desc_map.iteritems() if k]
        return "%s\n\n" % "\n".join(lines)

app = Flask(__name__)
subscriptions = []

# Client code consumes like this.
@app.route("/")
def index():
    index_template = """
     <html>
     <head></head>
     <body>
         <h1>Realtime app</h1>
         <div id="event"></div>
         <script type="text/javascript">
             var eventOutputContainer = document.getElementById("event");
             var evtSrc = new EventSource("/subscribe");
             console.log("connection init");

             evtSrc.onmessage = function(e) {
                 console.log(e.data);
                 eventOutputContainer.innerHTML = e.data;
             };
        </script>
    </body>
    </html>
    """
    return index_template

@app.route("/debug")
def debug():
    msg = str(len(subscriptions)) + " subscribers registered"
    return msg


@app.route("/test")
def test():
    return "OK"

@app.route("/publish")
def subscription():
    def notify():
        val = str(time.time())
        for s in subscriptions[:]:
            s.set(val)

    gevent.spawn(notify)

    return "OK"

@app.route("/subscribe")
def subscribe():
    def gen():
        sub = AsyncResult()
        try:
            while True:
                subscriptions.append(sub)
                result = sub.get()
                subscriptions.remove(sub)
                sse = ServerSentEvent(result)
                yield sse.encode()
                sub = AsyncResult()
        except GeneratorExit:
            if sub in subscriptions:
                subscriptions.remove(sub)

    return Response(gen(), mimetype="text/event-stream")

if __name__ == "__main__":
    port = 5000
    app.debug = True
    server = WSGIServer(("", 5000), app)
    print "Starting local server on port %d..." % port
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print "Stopping..."
        exit(0)
    # Then visit http://localhost:5000/debug
