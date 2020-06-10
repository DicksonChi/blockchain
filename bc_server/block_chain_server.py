import requests
import json
import time

from bc_entities.block import Block
from bc_entities.block_chain import BlockChain
from flask import Flask, request
from flask_api import status

app = Flask(__name__)

# chain
BLOCK_CHAIN = BlockChain()

# peers in this chain network
PEERS = set()


# endpoint to to add new transaction to the blockchain
@app.route('/add/transaction', methods=['POST'])
def add_transaction():
    trans_data = request.get_json()
    trans_data['time_stamp'] = time.time()
    BLOCK_CHAIN.add_new_transaction(trans_data)

    return 'Success', status.HTTP_201_CREATED


# get the chain
@app.route('/chain', methods=['GET'])
def get_chain():
    chain_data = list()
    for block in BLOCK_CHAIN.chain:
        chain_data.append(block.__dict__)
    return json.dumps({'length': len(chain_data),
                       'chain': chain_data}, default=str)


@app.route('/pending_transactions')
def get_pending_transactions():
    return json.dumps(BLOCK_CHAIN.unconfirmed_transactions, default=str)


# Endpoint to add new peers to the network
@app.route('/register_node', methods=['POST'])
def register_new_node():
    # The host address to the peer node
    node_address = request.get_json()['node_address']
    if not node_address:
        return 'Invalid data', status.HTTP_400_BAD_REQUEST

    # Add the node to the peer list
    PEERS.add(node_address)

    # Return the blockchain to the newly registered node so that it can sync
    return get_chain(), status.HTTP_200_OK


@app.route('/register_with', methods=['POST'])
def register_with_existing_node():
    """
    Internally calls the `register_node` endpoint to
    register current node with the remote node specified in the
    request, and sync the blockchain as well with the remote node.
    """
    node_address = request.get_json()['node_address']
    if not node_address:
        return 'Invalid data', status.HTTP_400_BAD_REQUEST

    data = {'node_address': request.host_url}
    headers = {'Content-Type': 'application/json'}

    # Make a request to register with remote node and obtain information
    response = requests.post(node_address + '/register_node',
                             data=json.dumps(data), headers=headers)

    if response.status_code == status.HTTP_200_OK:
        global BLOCK_CHAIN
        global PEERS
        # update chain and the peers
        chain_dump = response.json()['chain']
        BLOCK_CHAIN = create_chain_from_dump(chain_dump)
        PEERS.update(response.json()['peers'])
        return 'Registration successful', status.HTTP_200_OK
    else:
        # if something goes wrong, pass it on to the API response
        return response.content, response.status_code


def create_chain_from_dump(chain_dump):
    block_chain = BlockChain()
    for idx, block_data in enumerate(chain_dump):
        block = Block(block_data['index'],
                      block_data['transactions'],
                      block_data['timestamp'],
                      block_data['previous_hash'])
        proof = block_data['hash']
        if idx > 0:
            added = block_chain.add_block(block, proof)
            if not added:
                raise Exception('The chain dump is tampered!!')
        else:  # the block is a genesis block, no verification needed
            block_chain.chain.append(block)
    return block_chain


# this consensus algorithm wont be efficient for P2P networks with plenty nodes
def consensus():
    """
    Consensus algorithm in bitcoin paper (longest chain).
    """
    global BLOCK_CHAIN

    longest_chain = None
    current_longest_len = len(BLOCK_CHAIN.chain)

    for node in PEERS:
        response = requests.get('{}/chain'.format(node))
        length = response.json()['length']
        chain = response.json()['chain']
        if length > current_longest_len and BLOCK_CHAIN.check_chain_validity(chain):
            current_longest_len = length
            longest_chain = chain

    if longest_chain:
        BLOCK_CHAIN = longest_chain
        return True

    return False


@app.route('/add_block', methods=['POST'])
def verify_and_add_block():
    block_data = request.get_json()
    block = Block(block_data['index'],
                  block_data['transactions'],
                  block_data['timestamp'],
                  block_data['previous_hash'])

    proof = block_data['hash']
    added = BLOCK_CHAIN.add_block(block, proof)

    if not added:
        return 'The block was discarded by the node', status.HTTP_400_BAD_REQUEST

    return 'Block added to the chain', status.HTTP_201_CREATED


def announce_new_block(block):
    """
    A function to announce to the network once a block has been mined.
    Other blocks can simply verify the proof of work and add it to their
    respective chains.
    """
    for peer in PEERS:
        url = "{}add_block".format(peer)
        requests.post(url, data=json.dumps(block.__dict__, sort_keys=True, default=str))


@app.route('/mine', methods=['GET'])
def mine_unconfirmed_transactions():
    proof, block = BLOCK_CHAIN.mine()
    if not proof:
        return "No transactions to mine"
    else:
        # Making sure we have the longest chain before announcing to the network
        chain_length = len(BLOCK_CHAIN.chain)
        # update the blockchain of all peers with the longest pairs
        consensus()
        if chain_length == len(BLOCK_CHAIN.chain):
            # announce the recently mined block to the network
            announce_new_block(BLOCK_CHAIN.last_block)
        return 'Block #{} is mined.'.format(BLOCK_CHAIN.last_block.index)


if __name__ == '__main__':
    app.run(debug=True, port=8000)
