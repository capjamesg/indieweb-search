# start flask app
from flask import render_template, request, redirect, send_from_directory, jsonify, Blueprint, Flask
from bs4 import BeautifulSoup
import requests
import sqlite3
import random
import string

app = Flask(__name__)

@app.route("/")
def home():
    message = "This is capjamesg's WebSub endpoint."
    
    return jsonify({'message': message})

@app.route("/subscriptions")
def subscribe():
    hub_callback = request.form.get('hub.callback')

    hub_mode = request.form.get('hub.mode')

    hub_topic = request.form.get('hub.topic')

    hub_lease_seconds = request.form.get('hub.lease_seconds')

    hub_secret = request.form.get('hub.secret')

    connection = sqlite3.connect('websub.db')

    with connection:
        cursor = connection.cursor()

        # check if subscription exists
        subscription_exists = cursor.execute("SELECT * FROM subscriptions WHERE hub_callback = ? AND hub_topic = ?", (hub_callback, hub_topic)).fetchall()

        if hub_mode == "subscribe":
            if len(subscription_exists) > 0:
                cursor.execute("DELETE FROM subscriptions WHERE hub_callback = ? AND hub_topic = ?", (hub_callback, hub_topic))

            # verify publisher url 
            r = requests.get(hub_callback)

            if r.status_code != 200:
                return jsonify({'message': 'Invalid topic url.'})
            
            soup = BeautifulSoup(r.text, 'html.parser')

            get_all_link_hub = soup.find_all('link', rel='hub')

            if len(get_all_link_hub) == 0:
                return jsonify({'message': 'No hub link found on source page.'}), 400
                
            challenge = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10))

            verify_request = requests.get(hub_callback + "?hub.mode=subscribe&hub.topic=" + hub_topic + "&hub.challenge=" + challenge + "&hub.lease_seconds=" + hub_lease_seconds)

            if verify_request.status_code == 200:
                if verify_request.text and verify_request.text != hub_topic:
                    return jsonify({'message': 'Bad request.'}), 400

            cursor.execute("INSERT INTO subscriptions (hub_callback, hub_mode, hub_topic, hub_lease_seconds, hub_secret) VALUES (?, ?, ?, ?, ?)", (hub_callback, hub_mode, hub_topic, hub_lease_seconds, hub_secret))

            return jsonify({"message": "Accepted"}), 202

        elif hub_mode == "unsubscribe":
            if len(subscription_exists) == 0:
                return jsonify({'message': 'Subscription does not exist.'})
            
            cursor.execute("DELETE FROM subscriptions WHERE hub_callback = ? AND hub_topic = ?", (hub_callback, hub_topic))

            return jsonify({"message": "Accepted"}), 202
        else:
            return jsonify({'message': 'Bad request.'}), 400