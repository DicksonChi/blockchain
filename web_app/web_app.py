import datetime
import json

import requests
from flask import render_template, redirect, request

from bc_server.block_chain_server import app

# Node in the blockchain network that our application will communicate with
# to fetch and add data.
CONNECTED_NODE_ADDRESS = "http://127.0.0.1:8000"

POSTS = []


def fetch_posts():
    """
    Function to fetch the chain from a blockchain node, parse the
    data, and store it locally.
    """
    get_chain_address = "{}/chain".format(CONNECTED_NODE_ADDRESS)
    response = requests.get(get_chain_address)
    if response.status_code == 200:
        content = []
        chain = json.loads(response.content)
        for block in chain["chain"]:
            for tx in block["transaction"]:
                tx["index"] = block["index"]
                tx["hash"] = block["previous_hash"]
                content.append(tx)

        global POSTS
        POSTS = sorted(content,
                       key=lambda k: k['time_stamp'],
                       reverse=True)


@app.route('/submit', methods=['POST'])
def submit():
    """
    Endpoint to create a new transaction via our application
    """
    post_content = request.form["content"]
    author = request.form["author"]

    post_object = {
        'author': author,
        'content': post_content,
    }

    # Submit a transaction
    new_tx_address = "{}/add/transaction".format(CONNECTED_NODE_ADDRESS)

    requests.post(new_tx_address,
                  json=post_object,
                  headers={'Content-type': 'application/json'})

    # Return to the homepage
    return redirect('/')


@app.route('/')
def index():
    fetch_posts()
    return render_template('index.html',
                           title='Python Blockchain App ',
                           posts=POSTS,
                           node_address=CONNECTED_NODE_ADDRESS,
                           readable_time=timestamp_to_string)


def timestamp_to_string(epoch_time):
    return datetime.datetime.fromtimestamp(epoch_time).strftime('%H:%M')


if __name__ == '__main__':
    app.run(debug=True, port=5000)
