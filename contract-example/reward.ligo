(* This is simple example of reward programme contract that interacts with
    Juster and mint tokens for each participant who provided liquidity or made
    bets in events created by whitelisted addresses during given period of time
*)


(* Period type is combination of two timestamps, it is used to determine reward
    programme allowable period of time: *)
type periodType is record [
    startTime : timestamp;
    endTime : timestamp;
]


(* Reward program storage: *)
type storage is record [
    (* Juster address that used to interact with views: *)
    juster : address;

    (* FA2 token address and its id that minted as reward for participants: *)
    tokenAddress : address;
    tokenId : nat;

    (* Manager who controls reward program: *)
    manager : address;

    (* Mapping (unlimited set) with participants and event ids that was claimed
        (to prevent multi-claim): *)
    claimedRewards : big_map(address*nat, unit);

    (* Allowed event creators: this is white list of addresses that accepted by
        programme, it is used to prevent fake event creation claims *)
    trustedCreators : set(address);

    (* Flag used to pause contract by admin *)
    isPaused : bool;

    (* Boundaries of the period during which event can be applied for reward: *)
    allowedPeriod : periodType;

    (* Metadata used to add contract info implementing TZIP-16 *)
    metadata : big_map (string, bytes);
]


(* This is type that returned by getPosition view of Juster: *)
type positionType is record [
    providedLiquidityAboveEq : tez;
    providedLiquidityBelow : tez;
    betsAboveEq : tez;
    betsBelow : tez;
    liquidityShares : nat;
    depositedLiquidity : tez;
    depositedBets : tez;
    isWithdrawn : bool;
]


(* This is type that returned by getEvent view of Juster: *)
type eventType is record [
    currencyPair : string;
    createdTime : timestamp;
    targetDynamics : nat;
    betsCloseTime : timestamp;
    measureOracleStartTime : option(timestamp);
    startRate : option(nat);
    measurePeriod : nat;
    isClosed : bool;
    closedOracleTime : option(timestamp);
    closedRate : option(nat);
    closedDynamics : option(nat);
    isBetsAboveEqWin : option(bool);
    poolAboveEq : tez;
    poolBelow : tez;
    totalLiquidityShares : nat;
    liquidityPercent : nat;
    measureStartFee : tez;
    expirationFee : tez;
    rewardCallFee : tez;
    oracleAddress : address;
    maxAllowedMeasureLag : nat;
    isForceMajeure : bool;
    creator : address;
]

(* This is token mint entrypoint parameters: *)
type mintParams is record [
    token_id : nat;
    amount : nat;
    receiver : address;
]

(* This is params that called to update storage values: *)
type updateParams is record [
    tokenAddress : address;
    tokenId : nat;
    juster : address;
    manager : address;
    trustedCreators : set(address);
    allowedPeriod : periodType;
]

(* Entrypoints:
    - claimRewards called with eventId from user who participated in this event
    - triggerPause called to pause/unpause reward program
    - acceptAdmin called to accept given admin rights from a contract
    - releaseAdmin called to return admin rights from contract to admin
    - update called to change reward program storage params (this is useful
        during debug but it is probably not to have this in mainnet)
*)
type claimRewardType is record [ eventId : nat; participant : address ];
type action is
| ClaimReward of claimRewardType
| TriggerPause of unit
| AcceptAdmin of contract(unit)
| ReleaseAdmin of contract(address)
| Update of updateParams


(* Claim reward logic implementation: *)
function claimReward(
    const eventId : nat;
    const participant : address;
    var store : storage) : (list(operation)*storage) is
block {
    (* Checking that contract is not paused: *)
    if store.isPaused then failwith("Contract is paused") else skip;

    (* To get position for participant it is required to construct key: *)
    const key = (participant, eventId);

    (* Requesting position info: *)
    const positionOption : option(positionType) = Tezos.call_view
        ("getPosition", key, store.juster);
    const position = case positionOption of
    | Some(id) -> id
    | None -> (failwith("Juster.getPosition view is not found") : positionType)
    end;

    (* Requesting event info: *)
    const eventOption : option(eventType) = Tezos.call_view
        ("getEvent", eventId, store.juster);
    const event = case eventOption of
    | Some(id) -> id
    | None -> (failwith("Juster.getEvent view is not found") : eventType)
    end;

    (* Reward conditions: *)
    (* 1. Checking that event was created during given period of time *)
    if event.createdTime < store.allowedPeriod.startTime then
        failwith("Event created before reward period") else skip;
    if event.createdTime > store.allowedPeriod.endTime then
        failwith("Event created after reward period") else skip;

    (* 2. Checking that event was finished *)
    if event.isClosed then skip else
        failwith("Reward allowed only for closed events");

    (* 3. Checking that event was not finished with force majeure *)
    if event.isForceMajeure then
        failwith("Reward is not allowed for canceled events") else skip;

    (* 4. Checking that event created by trusted party *)
    if Set.mem(event.creator, store.trustedCreators) then skip else
        failwith("Event should be created by trusted creator");

    (* 5. Checking that reward was not claimed before *)
    if Big_map.mem(key, store.claimedRewards) then
        failwith("Reward already claimed") else skip;

    (* Calculating reward amount as provided liquidity + bets value *)
    const rewardAmount = position.depositedBets + position.depositedLiquidity;

    (* Emitting mint token operation *)
    const mintEntrypoint =
        case (Tezos.get_entrypoint_opt("%mint", store.tokenAddress)
              : option(contract(mintParams))) of
        | None -> (failwith("Token.mint is not found") : contract(mintParams))
        | Some(con) -> con
        end;

    const mint = record [
        token_id = store.tokenId;
        amount = rewardAmount / 1mutez;
        receiver = participant;
    ];

    const operations = list[Tezos.transaction(mint, 0tez, mintEntrypoint)];

    (* Recording claimed reward *)
    store.claimedRewards := Big_map.add(key, Unit, store.claimedRewards);

} with (operations, store)


(* Stop/contunue reward program logic implementation: *)
function triggerPause(var store : storage) : (list(operation)*storage) is
if Tezos.sender = store.manager then
    ((nil : list(operation)), store with record [isPaused = not store.isPaused])
else
    failwith("Only admin can call trigger pause");


(* Accepts admin calling given entrypoint to accept rights from contract: *)
function acceptAdmin(
    const entrypoint : contract(unit);
    const store : storage) : (list(operation)*storage) is
if Tezos.sender = store.manager then
    (list[Tezos.transaction(Unit, 0tez, entrypoint)], store)
else
    failwith("Only admin can call accept admin");


(* Proposes admin calling given entrypoint to release rights from contract: *)
function releaseAdmin(
    const entrypoint : contract(address);
    const store : storage) : (list(operation)*storage) is
if Tezos.sender = store.manager then
    (list[Tezos.transaction(store.manager, 0tez, entrypoint)], store)
else
    failwith("Only admin can call release admin");


(* Updates storage with different reward program params that can be useful
    for debug purposes: *)
function update(
    const params : updateParams;
    const store : storage) : (list(operation)*storage) is
if Tezos.sender = store.manager then
    ((nil : list(operation)), store with record [
        tokenAddress = params.tokenAddress;
        tokenId = params.tokenId;
        juster = params.juster;
        manager = params.manager;
        trustedCreators = params.trustedCreators;
        allowedPeriod = params.allowedPeriod;
    ])
else
    failwith("Only admin can call release admin");


function main(
    const params : action;
    const store : storage) : (list(operation)*storage) is
case params of
| ClaimReward(p) -> claimReward(p.eventId, p.participant, store)
| TriggerPause -> triggerPause(store)
| AcceptAdmin(entrypoint) -> acceptAdmin(entrypoint, store)
| ReleaseAdmin(entrypoint) -> releaseAdmin(entrypoint, store)
| Update(params) -> update(params, store)
end;

