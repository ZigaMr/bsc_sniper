# bsc_sniper
A BSC mainnet sniper bot for early panckakeSwap token launches. 

Uses blocknative websocket API to monitor mempool for addLiquidity/unlock/custom events and places buy orders as soon possible.

For production it is better to use custom contracts which allow us to spam network with hundreds of txs and increase the probability of being the first to buy after listing.

To run the code install Web3 and eth_account libraries (python3).

Use at your own risk.
  
