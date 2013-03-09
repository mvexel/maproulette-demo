#!/usr/bin/env python

from flask import Flask, request, abort, jsonify, session
from flask_oauth import OAuth
import geojson
from pyspatialite import dbapi2 as db
from markdown import markdown
import setting

# creating/connecting the test_db`
conn = db.connect('noaddr.sqlite')
app = Flask(__name__)
app.config.from_object(__name__)
app.config.from_envvar('REMAPATRON_SETTINGS', silent = True)
app.debug = True

# instantiate OAuth object
oauth = OAuth()
osm = oauth.remote_app(
    'osm',
    base_url='http://openstreetmap.org/',
    request_token_url='http://www.openstreetmap.org/oauth/request_token',
    access_token_url='http://www.openstreetmap.org/oauth/access_token',
    authorize_url='http://www.openstreetmap.org/oauth/authorize',
    consumer_key='zoTZ4nLqQ1Y5ncemWkzvc3b3hG156jgvryIjiEkX',
    consumer_secret='e6nIgyAUqPt8d9kJymX6J86i5sG5mI8Rvv7XfRUb'
)

@osm.tokengetter
def get_osm_token(token=None):
    return session.get('osm_token')

@app.route('/')
def splash():
  return 'This is MapRoulette - but you probably want to be somplace else.'

@app.route('/meta')
def meta():
    """Returns the metadata for the current challenge"""
    return geojson.dumps({
        'slug': settings.slug,
        'name': settings.name,
        'description': settings.description,
        'difficulty': settings.difficulty,
        'blurb': settings.blurb,
        'help': markdown(settings.help),
        'polygon': settings.polygon,
        })

@app.route('/stats')
def stats():
    """Returns statistics about the challenge"""
    conn = db.connect('noaddr.sqlite')
    cur = conn.cursor()
    results = cur.execute("SELECT COUNT(id) from anomaly").fetchall()
    total = results[0][0]
    results = cur.execute("SELECT COUNT (id) from anomaly WHERE seen > 2").fetchall()
    done = results[0][0]
    return jsonify({'total': total, 'done': done})

@app.route('/task')
def get_task():
    """Retrieves a candidate task and returns as geoJSON"""
    conn = db.connect('noaddr.sqlite')
    cur = conn.cursor()
    recs = cur.execute("""
SELECT id, description, AsGeoJSON(pt) from anomaly WHERE seen < 3
ORDER BY RANDOM() LIMIT 1""").fetchall()
    task_id, text, point = recs[0]
    fc = geojson.FeatureCollection([
            geojson.Feature(geometry = geojson.loads(point),
                            properties = {
                    # There must be one object in the FeatureCollection
                    # That has a key = True. Then that object must have
                    # it's OSM element type (type) and OSM ID (id)
                    'selected': True,
                    'type': 'node',
                    'id': task_id,
                    'text': text})])
    
    return geojson.dumps({
            'challenge': settings.name,
            'id': task_id,
            'text': text,
            'features': fc})

@app.route('/task/<task_id>', methods = ['POST'])
def store_attempt(task_id):
    """Stores information about the task"""
    conn = db.connect('noaddr.sqlite')
    cur = conn.cursor()
    res = cur.execute("SELECT id from anomaly where id IS %d" % int(task_id))
    recs = res.fetchall()
    if not len(recs) == 1:
        abort(404)
    #dct = geojson.loads(request.json)
    dct = request.form
    # We can now handle this object as we like, but for now, let's
    # just handle the action
    action = dct['action']
    if action == 'fixed':
        pass
    elif action == 'notfixed':
        pass
    elif action == 'someonebeatme':
        pass
    elif action == 'falsepositive':
        pass
    elif action == 'skip':
        pass
    elif action == 'noerrorafterall':
        pass
    # We need to return something, so let's return an empty
    # string. Maybe in the future we'll think of something useful to
    # return and return that instead
    return ""

@app.route('/oauth/authenticate')
"""Initiates OAuth authentication agains the OSM server"""
def oauth_authenticate():
    return osm.authorize(callback=url_for('oauth_authorized',
      next=request.args.get('next') or request.referrer or None))

@app.route('/oauth/callback')
"""Receives the OAuth callback from OSM"""
def oauth_authorized(resp):
    next_url = request.args.get('next') or url_for('index')
    if resp is None:
      flash(u'You denied the request to sign in.')
      return redirect(next_url)
    session['osm_token'] = (
        resp['oauth_token'],
        resp['oauth_token_secret']
        )
    session['twitter_user'] = resp['screen_name']
    flash('You were signed in as %s' % resp['screen_name'])
    return redirect(next_url)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type = int, default = '8000' , help = "the port to bind to (defaults to 8000)")
    args = parser.parse_args()
    app.run(host='0.0.0.0', port=args.port)
