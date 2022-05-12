import json
import asyncio
import websockets
import datetime as dt
from ABIs import pancakeABI2, pancakeABI, uniswap_pair_abi, falcx_abi
from web3 import Web3
from eth_account.signers.local import LocalAccount
from eth_account.account import Account
import time
import os

ETH_ACCOUNT_FROM: LocalAccount = Account.from_key(os.environ.get("ETH_PRIVATE_FROM")) # Import key from env variable
node = 'https://speedy-nodes-nyc.moralis.io/6a8ebb0f30beab5fbf4974ca/bsc/mainnet'  # BSC mainnet node url, can you use mine, it's free to use
web3 = Web3(Web3.HTTPProvider(node))
pancakeSwapRouterAddress = web3.toChecksumAddress('0x10ed43c718714eb63d5aa57b78b54704e256024e') # Set pancakeSwap v2
contract_router = web3.eth.contract(address=pancakeSwapRouterAddress, abi=pancakeABI) # Contract abstraction with ABI
token = web3.toChecksumAddress('0x9573c88aE3e37508f87649f87c4dd5373C9F31e0')  # Set the target token address here
bnb = web3.toChecksumAddress('0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c')
pair_contract = web3.eth.contract(web3.toChecksumAddress('0x9bE14747D7115ed8D1414C2dFA221DBDAb894002'),
                                  abi=uniswap_pair_abi)
reserves = pair_contract.functions.getReserves().call()
price = reserves[0]/reserves[1]
bnb_amount = 10**10 # Set the amount of BNB you want to use
token_amount = price*bnb_amount*0.4 # Set the amount of token you want to buy, set this in advance if we can predict initial liquidity, 0.4 == 60% slippage tolerance
nonce = web3.eth.getTransactionCount(ETH_ACCOUNT_FROM.address)

async def snipe():
    """
    Token sniper for use on panckakeSwap (bsc mainnet)
    Usually the token is locked for a period of time, so the buy order is sent after the lock expires.
    Works by watching the address of the token or pool contract for "unlock" event 
    and sending buy order to the router contract.
    The priority is to buy as soon as possible, but the sell orders are to be handled manually by the user.
    """

    uri = "wss://api.blocknative.com/v0"
    async with websockets.connect(uri) as ws:
        res = await ws.send(json.dumps({'timeStamp': str(dt.datetime.now().isoformat()),
                                        'dappId': '24f5031e-358e-4b47-9147-23f64a68cb94',
                                        'version': '1',
                                        'blockchain': {
                                            'system': 'ethereum',
                                            'network': 'bsc-main'},
                                        'categoryCode': 'initialize',
                                        'eventCode': 'checkDappId'}))
        print(res)
        subscribe_msg = {
            'timeStamp': str(dt.datetime.now().isoformat()),
            'dappId': '24f5031e-358e-4b47-9147-23f64a68cb94',
            "categoryCode": "configs",
            'version': '1',
            'blockchain': {
                'system': 'ethereum',
                'network': 'bsc-main'},
            "eventCode": "put",
            "config": {
                "scope": '0x10ed43c718714eb63d5aa57b78b54704e256024e',
                "filters": [{"_join": "AND", "terms": [{"contractCall.methodName": "addLiquidityETH"}, # Set event to watch, uses blocknative which was faster than local node
                                                      {"contractCall.params.token": token}
                                                      ]}],
                "abi": pancakeABI,
                "watchAddress": True
            }
        }

        res2 = await ws.send(json.dumps(subscribe_msg))

        print(res2)
        while True:
            t = await ws.recv()
            data = json.loads(t)
            if 'event' not in data.keys() or 'transaction' not in data['event'].keys() or \
                    'amountTokenDesired' not in data['event']['contractCall']['params']:
                print(t)
                continue

            for i in range(5): 
                # This was set to 5 for testing purposes, 
                # usually you'd want a spambot contract which can spam 
                # hundreds of transactions to have a higher chance of success
                # This script doesn't use a contract, so using multiple (5) transactions won't increase chance of success (nonce error)
                
                price = reserves[0]/reserves[1]  # Comment this out if don't want to set price dynamically
                token_amount = price*bnb_amount*0.4  # Comment this out if don't want to set price dynamically

                buy = contract_router.functions.swapExactETHForTokens(int(token_amount),
                                                                      [bnb, token],
                                                                      ETH_ACCOUNT_FROM.address,
                                                                      int(time.time()) + 3600).buildTransaction(
                    {'value': bnb_amount,
                     'gasPrice': int(data['event']['transaction']['gasPrice']), # Set gas price equal to the gas price of the event (or maybe + 1, to guarantee inclusion after the event)
                     'nonce': nonce+i})

                signed_transaction_buy = web3.eth.account.sign_transaction(buy, ETH_ACCOUNT_FROM.privateKey)
                tx_hash = web3.eth.sendRawTransaction(signed_transaction_buy.rawTransaction)
                print(tx_hash)
            print(data)
            print(dt.datetime.now())
            print(data['event']['transaction']['hash'])
            break


asyncio.get_event_loop().run_until_complete(snipe())
