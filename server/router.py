from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from blockchain import blockchain
from sync import sync
from block import Block

import os
import json
import config as conf
import json
import threading
import mine
import apscheduler

# Instantiate the Node
app = Flask(__name__)
CORS(app)


@app.route('/')
def index():
    return render_template('./index.html')

@app.route('/configure')
def configure():
    return render_template('./configure.html')

@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.form

    # Check that the required fields are in the POST'ed data
    required = ['sender_address', 'recipient_address', 'amount', 'signature']
    if not all(k in values for k in required):
        return 'Missing values', 400
    # Create a new Transaction
    transaction_result = blockchain.submit_transaction(values['sender_address'], values['recipient_address'], values['amount'], values['signature'])

    if transaction_result == False:
        response = {'message': 'Invalid Transaction!'}
        return jsonify(response), 406
    else:
        response = {'message': 'Transaction will be added to Block '+ str(transaction_result)}
        return jsonify(response), 201

@app.route('/transactions/get', methods=['GET'])
def get_transactions():
    #Get transactions from transactions pool
    chaindata_dir = '../transaction/'+conf.TRANSACTION_DIR
    transactions  = []   
    for i, filename in enumerate(sorted(os.listdir(chaindata_dir))):
        with open('%s%s' %(chaindata_dir, filename)) as file:
            transaction = json.load(file)
            transactions.append(transaction)
    transactions=sorted(transactions, key=lambda x: x['value'],reverse=True)
    response = {'transactions': transactions}
    return jsonify(response), 200

@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.block_list_dict(),
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200

@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.form
    nodes = values.get('nodes').replace(" ", "").split(',')

    if nodes is None:
        return "Error: Please supply a valid list of nodes", 400

    for node in nodes:
        blockchain.register_node(node)

    response = {
        'message': 'New nodes have been added',
        'total_nodes': [node for node in blockchain.nodes],
    }
    return jsonify(response), 201


@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            'message': 'Our chain was replaced',
            'new_chain': blockchain.chain
        }
    else:
        response = {
            'message': 'Our chain is authoritative',
            'chain': blockchain.chain
        }
    return jsonify(response), 200


@app.route('/nodes/get', methods=['GET'])
def get_nodes():
    nodes = list(blockchain.nodes)
    response = {'nodes': nodes}
    return jsonify(response), 200

@app.route('/blockchain.json', methods=['GET'])
def get_blockchain():
    local_chain = sync.sync_local()
    json_blocks = json.dumps(local_chain.block_list_dict())
    return json_blocks


@app.route('/someone_mined_new_block', methods=['POST'])
def import_block_from_other_node():
    print('------------------------------')
    print(' * Someone has minned new block, receiving...')
    new_block_dict = json.loads(request.data)
    print(new_block_dict['hash'])
    mine.sched.add_job(mine.validate_possible_block, args=[
                  new_block_dict], id='validate_possible_block')
    return 'I received a block'