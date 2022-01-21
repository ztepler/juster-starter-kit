from pytezos import ContractInterface, pytezos
from datetime import datetime

SHELL = 'https://rpc.tzkt.io/hangzhou2net/'
KEY_FILENAME = 'key.json'
REWARD_FN = 'reward.tz'
CONTRACT_METADATA_URI = 'ipfs://QmQV9jS7ma8iAbEB7dfBDrJrn1uQ1XkucFhnSy1c9Fp8dd'
TOKEN_ADDRESS = 'KT1HZm1fXYwPxokWVvpit8Hn9bu88yGUUgMy'
TOKEN_ID = 0
JUSTER = 'KT197iHRJaAGw3oGpQj21YYV1vK9Fa5ShoMn'
TRUSTED_CREATORS = [
    'tz1U2zsFffCTcTvWddAfHfc2gUvEHepaVT1L'
]


def to_hex(string):
    return string.encode().hex()


def generate_storage(manager):
    return {
        'juster': JUSTER,
        'tokenAddress': TOKEN_ADDRESS,
        'tokenId': TOKEN_ID,
        'manager': manager,
        'claimedRewards': {},
        'trustedCreators': TRUSTED_CREATORS,
        'isPaused': False,
        'allowedPeriod': {
            'startTime': int(datetime(2022, 1, 1).timestamp()),
            'endTime': int(datetime(2022, 2, 1).timestamp())
        },
        'metadata': {'': to_hex(CONTRACT_METADATA_URI)}
    }


def activate_and_reveal(client):
    print(f'activating account...')
    op = client.activate_account().send()
    client.wait(op)

    op = client.reveal().send()
    client.wait(op)


def deploy_reward_program(client):
    print(f'deploying reward program...')
    contract = ContractInterface.from_file(REWARD_FN).using(
        key=KEY_FILENAME, shell=SHELL)
    storage = generate_storage(manager=client.key.public_key_hash())

    opg = contract.originate(initial_storage=storage).send()
    print(f'success: {opg.hash()}')
    client.wait(opg)

    # Searching for Reward Program contract address:
    opg = client.shell.blocks['head':].find_operation(opg.hash())
    op_result = opg['contents'][0]['metadata']['operation_result']
    address = op_result['originated_contracts'][0]
    print(f'token address: {address}')
    return address


if __name__ == '__main__':

    client = pytezos.using(key=KEY_FILENAME, shell=SHELL)

    """
    1. If key hasn't been used before, this function will allow to activate key:
    """
    if client.balance() < 1e-5:
        activate_and_reveal(client)

    """
    2. Reward Program deploy
    """
    reward_program_address = deploy_reward_program(client)

