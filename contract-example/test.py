from datetime import datetime
import pytest
from pytezos import (
    pytezos,
    ContractInterface,
    MichelsonRuntimeError,
    Unit
)


REWARD_FN = 'reward.tz'
USER_A = 'tz1S6V1YfUqt7facXpdk68JQ11mD8qUh5Yex'
USER_B = 'tz1U2zsFffCTcTvWddAfHfc2gUvEHepaVT1L'
USER_C = 'tz1d2CUbfiZaCoDxT1doLUeS4n9e5tCUDtL9'
ADMIN = 'tz1PQ1aDt6p7zwFpyBZQr2VnLS3D2yCmq3s1'
JUSTER = 'KT197iHRJaAGw3oGpQj21YYV1vK9Fa5ShoMn'
TOKEN =  'KT1RJ6PbjHpwc3M5rw5s2Nbmefwbuwbdxton'
ORACLE =  'KT1PMQZxQTrFPJn3pEaj9rvGfJA9Hvx7Z1CL'


def create_storage(claimed_rewards=None, is_paused=False):
    """ Returns defaul storage for reward program for test purposes """

    claimed_rewards = claimed_rewards or {}

    return {
        'juster': JUSTER,
        'tokenAddress': TOKEN,
        'tokenId': 0,
        'manager': ADMIN,
        'claimedRewards': claimed_rewards,
        'trustedCreators': [ADMIN],
        'isPaused': is_paused,
        'allowedPeriod': {
            'startTime': int(datetime(2022, 1, 1).timestamp()),
            'endTime': int(datetime(2022, 2, 1).timestamp())
        },
        'metadata': {}
    }

def create_position(
            provided=0,
            bets=0,
        ):
    """ Creates position for test purposes """

    return {
        'providedLiquidityAboveEq': provided,
        'providedLiquidityBelow': provided,
        'betsAboveEq': bets,
        'betsBelow': 0,
        'liquidityShares': provided,
        'depositedLiquidity': provided,
        'depositedBets': bets,
        'isWithdrawn': False
    }


def create_event(
            created_time=None,
            bets_period=3600,
            measure_period=3600,
            is_closed=True,
            is_force_majeure=False,
            creator=ADMIN
        ):
    """ Creates event for test purposes """

    created_time = created_time or int(datetime(2022, 1, 15, 0, 0).timestamp())
    lag_time = 5*60

    return {
        'currencyPair': 'XTZ-USD',
        'createdTime': created_time,
        'targetDynamics': 1_000_000,
        'betsCloseTime': created_time + bets_period,
        'measureOracleStartTime': created_time + bets_period + lag_time,
        'startRate': 420,
        'measurePeriod': measure_period,
        'isClosed': is_closed,
        'closedOracleTime': created_time + bets_period + measure_period + lag_time,
        'closedRate': 420 if is_closed else None,
        'closedDynamics': 1_000_000 if is_closed else None,
        'isBetsAboveEqWin': True if is_closed else None,
        'poolAboveEq': 1000,
        'poolBelow': 1000,
        'totalLiquidityShares': 100,
        'liquidityPercent': 0,
        'measureStartFee': 0,
        'expirationFee': 0,
        'rewardCallFee': 0,
        'oracleAddress': ORACLE,
        'maxAllowedMeasureLag': 20*60,
        'isForceMajeure': is_force_majeure,
        'creator': creator
    }


def test_should_create_mint_operation_for_provided_bets():
    reward = ContractInterface.from_file(REWARD_FN)
    init_storage = create_storage()

    # Preparing claim reward call with view response where USER_A
    # bets above for 100 mutez:
    bets_amount = 100
    claim_reward_params = {'eventId': 0, 'participant': USER_A}

    view_results = {
        f'{JUSTER}%getPosition': create_position(bets=bets_amount),
        f'{JUSTER}%getEvent': create_event()
    }

    result = reward.claimReward(claim_reward_params).interpret(
        storage=init_storage,
        sender=USER_A,
        view_results=view_results)

    assert len(result.operations) == 1
    op = result.operations[0]
    assert op['destination'] == TOKEN
    assert op['parameters']['entrypoint'] == 'mint'
    assert op['parameters']['value']['args'][0]['args'][0]['int'] == str(bets_amount)
    assert op['parameters']['value']['args'][0]['args'][1]['string'] == USER_A


def test_should_create_mint_operation_for_provided_liquidity():
    reward = ContractInterface.from_file(REWARD_FN)
    init_storage = create_storage()

    # Preparing claim reward call with view response where USER_B
    # provided liquidity for 1 xtz:
    provided_amount = 1_000_000
    claim_reward_params = {'eventId': 42, 'participant': USER_B}

    view_results = {
        f'{JUSTER}%getPosition': create_position(provided=provided_amount),
        f'{JUSTER}%getEvent': create_event()
    }

    result = reward.claimReward(claim_reward_params).interpret(
        storage=init_storage,
        sender=USER_A,
        view_results=view_results)

    assert len(result.operations) == 1
    op = result.operations[0]
    assert op['destination'] == TOKEN
    assert op['parameters']['entrypoint'] == 'mint'
    assert op['parameters']['value']['args'][0]['args'][0]['int'] == str(provided_amount)
    assert op['parameters']['value']['args'][0]['args'][1]['string'] == USER_B


def test_should_fail_if_already_paid_reward():
    reward = ContractInterface.from_file(REWARD_FN)

    # Creating storage where USER_A already claimed reward for event 0:
    init_storage = create_storage(claimed_rewards={(USER_A, 0): Unit})

    claim_reward_params = {'eventId': 0, 'participant': USER_A}

    view_results = {
        f'{JUSTER}%getPosition': create_position(),
        f'{JUSTER}%getEvent': create_event()
    }

    with pytest.raises(MichelsonRuntimeError) as cm:
        result = reward.claimReward(claim_reward_params).interpret(
            storage=init_storage,
            sender=USER_C,
            view_results=view_results)

    assert 'Reward already claimed' in str(cm.value)


def test_should_fail_if_event_created_before_period_starts():
    reward = ContractInterface.from_file(REWARD_FN)
    init_storage = create_storage()
    claim_reward_params = {'eventId': 0, 'participant': USER_A}

    time_before_period = int(datetime(1984, 1, 15).timestamp())
    view_results = {
        f'{JUSTER}%getPosition': create_position(),
        f'{JUSTER}%getEvent': create_event(created_time=time_before_period)
    }

    with pytest.raises(MichelsonRuntimeError) as cm:
        result = reward.claimReward(claim_reward_params).interpret(
            storage=init_storage,
            sender=USER_C,
            view_results=view_results)

    assert 'Event created before reward period' in str(cm.value)


def test_should_fail_if_event_created_after_period_starts():
    reward = ContractInterface.from_file(REWARD_FN)
    init_storage = create_storage()
    claim_reward_params = {'eventId': 0, 'participant': USER_A}

    time_after_period = int(datetime(2047, 1, 15).timestamp())
    view_results = {
        f'{JUSTER}%getPosition': create_position(),
        f'{JUSTER}%getEvent': create_event(created_time=time_after_period)
    }

    with pytest.raises(MichelsonRuntimeError) as cm:
        result = reward.claimReward(claim_reward_params).interpret(
            storage=init_storage,
            sender=USER_C,
            view_results=view_results)

    assert 'Event created after reward period' in str(cm.value)


def test_should_fail_if_event_created_after_period_starts():
    reward = ContractInterface.from_file(REWARD_FN)
    init_storage = create_storage()
    claim_reward_params = {'eventId': 0, 'participant': USER_A}

    time_after_period = int(datetime(2047, 1, 15).timestamp())
    view_results = {
        f'{JUSTER}%getPosition': create_position(),
        f'{JUSTER}%getEvent': create_event(created_time=time_after_period)
    }

    with pytest.raises(MichelsonRuntimeError) as cm:
        result = reward.claimReward(claim_reward_params).interpret(
            storage=init_storage,
            sender=USER_C,
            view_results=view_results)

    assert 'Event created after reward period' in str(cm.value)


def test_should_fail_if_event_is_not_closed():
    reward = ContractInterface.from_file(REWARD_FN)
    init_storage = create_storage()
    claim_reward_params = {'eventId': 0, 'participant': USER_A}

    view_results = {
        f'{JUSTER}%getPosition': create_position(),
        f'{JUSTER}%getEvent': create_event(is_closed=False)
    }

    with pytest.raises(MichelsonRuntimeError) as cm:
        result = reward.claimReward(claim_reward_params).interpret(
            storage=init_storage,
            sender=USER_C,
            view_results=view_results)

    assert 'Reward allowed only for closed events' in str(cm.value)


def test_should_fail_if_event_was_finished_in_force_majeure():
    reward = ContractInterface.from_file(REWARD_FN)
    init_storage = create_storage()
    claim_reward_params = {'eventId': 0, 'participant': USER_A}

    view_results = {
        f'{JUSTER}%getPosition': create_position(),
        f'{JUSTER}%getEvent': create_event(is_force_majeure=True)
    }

    with pytest.raises(MichelsonRuntimeError) as cm:
        result = reward.claimReward(claim_reward_params).interpret(
            storage=init_storage,
            sender=USER_C,
            view_results=view_results)

    assert 'Reward is not allowed for canceled events' in str(cm.value)


def test_should_fail_if_event_was_created_by_not_trusted_party():
    reward = ContractInterface.from_file(REWARD_FN)
    init_storage = create_storage()
    claim_reward_params = {'eventId': 0, 'participant': USER_A}

    view_results = {
        f'{JUSTER}%getPosition': create_position(),
        f'{JUSTER}%getEvent': create_event(creator=USER_C)
    }

    with pytest.raises(MichelsonRuntimeError) as cm:
        result = reward.claimReward(claim_reward_params).interpret(
            storage=init_storage,
            sender=USER_C,
            view_results=view_results)

    assert 'Event should be created by trusted creator' in str(cm.value)


def test_should_register_as_claimed_after_claim():
    reward = ContractInterface.from_file(REWARD_FN)
    init_storage = create_storage()
    claim_reward_params = {'eventId': 0, 'participant': USER_A}

    view_results = {
        f'{JUSTER}%getPosition': create_position(),
        f'{JUSTER}%getEvent': create_event()
    }

    result = reward.claimReward(claim_reward_params).interpret(
        storage=init_storage,
        sender=USER_C,
        view_results=view_results)

    assert result.storage['claimedRewards'][(USER_A, 0)] == Unit


def test_should_allow_admin_to_pause_contract():
    reward = ContractInterface.from_file(REWARD_FN)
    init_storage = create_storage()

    result = reward.triggerPause().interpret(storage=init_storage, sender=ADMIN)

    assert result.storage['isPaused']


def test_should_not_allow_user_to_pause_contract():
    reward = ContractInterface.from_file(REWARD_FN)
    init_storage = create_storage()

    with pytest.raises(MichelsonRuntimeError) as cm:
        result = reward.triggerPause().interpret(
            storage=init_storage, sender=USER_A)


def test_should_allow_admin_to_unpause_contract():
    reward = ContractInterface.from_file(REWARD_FN)
    init_storage = create_storage(is_paused=True)

    result = reward.triggerPause().interpret(storage=init_storage, sender=ADMIN)

    assert not result.storage['isPaused']


def test_should_not_allow_to_pay_reward_if_paused():
    reward = ContractInterface.from_file(REWARD_FN)
    init_storage = create_storage(is_paused=True)

    claim_reward_params = {'eventId': 0, 'participant': USER_A}

    view_results = {
        f'{JUSTER}%getPosition': create_position(),
        f'{JUSTER}%getEvent': create_event()
    }

    with pytest.raises(MichelsonRuntimeError) as cm:
        result = reward.claimReward(claim_reward_params).interpret(
            storage=init_storage,
            sender=USER_C,
            view_results=view_results)

    assert 'Contract is paused' in str(cm.value)


def test_should_allow_to_release_admin_rights():
    reward = ContractInterface.from_file(REWARD_FN)
    init_storage = create_storage()

    result = reward.releaseAdmin(f'{TOKEN}%change_manager').interpret(
        storage=init_storage,
        sender=ADMIN)

    assert len(result.operations) == 1
    op = result.operations[0]
    assert op['destination'] == TOKEN
    assert op['parameters']['entrypoint'] == 'change_manager'
    assert op['parameters']['value']['string'] == ADMIN


def test_should_fail_to_release_admin_if_caller_is_not_admin():
    reward = ContractInterface.from_file(REWARD_FN)
    init_storage = create_storage()

    with pytest.raises(MichelsonRuntimeError) as cm:
        result = reward.releaseAdmin(f'{TOKEN}%change_manager').interpret(
            storage=init_storage,
            sender=USER_C)

    assert 'Only admin can call release admin' in str(cm.value)


def test_update_params_from_manager_should_succeed():
    reward = ContractInterface.from_file(REWARD_FN)
    init_storage = create_storage()

    new_creators = list(init_storage['trustedCreators'])
    new_creators.append(USER_B)

    update_params = {
        'tokenAddress': init_storage['tokenAddress'],
        'tokenId': init_storage['tokenId'],
        'juster': init_storage['juster'],
        'manager': init_storage['manager'],
        'trustedCreators': new_creators,
        'allowedPeriod': init_storage['allowedPeriod']
    }

    result = reward.update(update_params).interpret(
        storage=init_storage,
        sender=ADMIN)

    assert sorted(result.storage['trustedCreators']) == sorted(new_creators)


def test_update_params_from_not_manager_should_fail():
    reward = ContractInterface.from_file(REWARD_FN)
    init_storage = create_storage()

    update_params = {
        'tokenAddress': init_storage['tokenAddress'],
        'tokenId': init_storage['tokenId'],
        'juster': init_storage['juster'],
        'manager': init_storage['manager'],
        'trustedCreators': init_storage['trustedCreators'],
        'allowedPeriod': init_storage['allowedPeriod']
    }

    with pytest.raises(MichelsonRuntimeError) as cm:
        result = reward.update(update_params).interpret(
            storage=init_storage,
            sender=USER_C)

    assert 'Only admin can call release admin' in str(cm.value)


def test_should_allow_to_accept_admin_rights():
    reward = ContractInterface.from_file(REWARD_FN)
    init_storage = create_storage()

    result = reward.acceptAdmin(f'{TOKEN}%accept_ownership').interpret(
        storage=init_storage,
        sender=ADMIN)

    assert len(result.operations) == 1
    op = result.operations[0]
    assert op['destination'] == TOKEN
    assert op['parameters']['entrypoint'] == 'accept_ownership'


def test_should_fail_to_release_admin_if_caller_is_not_admin():
    reward = ContractInterface.from_file(REWARD_FN)
    init_storage = create_storage()

    with pytest.raises(MichelsonRuntimeError) as cm:
        result = reward.acceptAdmin(f'{TOKEN}%accept_ownership').interpret(
            storage=init_storage,
            sender=USER_C)

    assert 'Only admin can call accept admin' in str(cm.value)

