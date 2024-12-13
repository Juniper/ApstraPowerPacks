from flask import Flask

from snow_tickets import SNOWPowerPack

app = Flask(__name__)
pp = SNOWPowerPack()


@app.after_request
def add_header(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response


@app.route('/get_bps')
def get_bps():
    return pp.bp_ids


@app.route('/get_tickets')
def get_tickets():
    print(pp.tickets.values())
    return list(pp.tickets.values())


@app.route('/status')
def is_paused():
    return {"paused": pp.is_paused()}


@app.route('/pause', methods=['POST'])
def pause():
    pp.pause()
    print("paused")
    return {}


@app.route('/unpause', methods=['POST'])
def unpause():
    print("unpaused")
    pp.unpause()
    return {}


if __name__ == '__main__':
    print("IN MAIN")
    pp.start_threads(blocking=False, pause_check=False)
    app.run(debug=False)
