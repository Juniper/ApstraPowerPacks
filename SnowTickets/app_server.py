from flask import Flask, render_template

from snow_tickets import SNOWPowerPack

app = Flask(__name__,static_url_path='',
            static_folder='./snow-apstra-app/build',
            template_folder='./snow-apstra-app/build')
pp = SNOWPowerPack()

@app.route("/")
def hello():
    return render_template("index.html")


@app.after_request
def add_header(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response


@app.route('/bps')
def get_bps():
    return pp.bp_ids


@app.route('/tickets')
def get_tickets():
    print(pp.tickets.values())
    return list(pp.tickets.values())


@app.route('/status')
def status():
    return {"running": not pp.is_paused()}


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
