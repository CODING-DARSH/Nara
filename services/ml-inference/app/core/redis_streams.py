"""
NARA — Redis Streams helper (replaces Kafka everywhere)

Redis Streams gives us the same core guarantees we were using Kafka for:
  - an ordered, durable log per topic (stream)
  - multiple independent consumer groups reading the same stream
  - at-least-once delivery via explicit ACK (XACK) after processing

Mapping from Kafka concepts -> Redis Streams:
  - topic            -> stream key (e.g. "food.events.raw")
  - producer.send     -> XADD
  - consumer group    -> XGROUP (created once, idempotently)
  - consumer.poll      -> XREADGROUP (blocking, with a consumer name)
  - auto_offset_reset=earliest -> XGROUP CREATE ... $ vs 0 (see create_group)
  - manual commit      -> XACK after successful processing

Same file is copy-pasted (or shared via a common package) into every
service that previously imported aiokafka — ingestion, ml-inference,
user-intelligence, recommendation. Each service still owns its own
REDIS_URL / group name via its own config, this module just needs a
redis.asyncio client passed in.
"""
import json
import structlog
from redis.asyncio import Redis

log = structlog.get_logger()


async def emit(redis: Redis, stream: str, payload: dict, key: str = None):
    """
    Replaces: producer.send_and_wait(topic, value=payload, key=key_bytes)

    Redis Streams doesn't have a native "key" concept the way Kafka does
    (Kafka uses key for partition routing) — we don't need partitioning
    here at this scale, so we just fold key into the payload for anyone
    who wants to filter/group by it downstream.
    """
    fields = {"payload": json.dumps(payload)}
    if key:
        fields["key"] = key
    msg_id = await redis.xadd(stream, fields)
    log.info("redis_stream.emitted", stream=stream, key=key, msg_id=msg_id)
    return msg_id


async def ensure_group(redis: Redis, stream: str, group: str):
    """
    Idempotent consumer-group creation — mirrors Kafka's auto_offset_reset
    behavior. mkstream=True creates the stream itself if it doesn't exist
    yet (a producer may not have run before the first consumer starts).
    id="0" means a brand-new group starts from the beginning of the
    stream, same as Kafka's auto_offset_reset="earliest".
    """
    try:
        await redis.xgroup_create(stream, group, id="0", mkstream=True)
        log.info("redis_stream.group_created", stream=stream, group=group)
    except Exception as e:
        # BUSYGROUP = group already exists, which is the expected steady
        # state after the first run — anything else is a real problem.
        if "BUSYGROUP" not in str(e):
            raise


async def consume_loop(
    redis: Redis,
    stream: str,
    group: str,
    consumer_name: str,
    handler,
    block_ms: int = 5000,
):
    """
    Replaces: `async for message in consumer:` in the old Kafka loop.

    handler(payload: dict, key: str | None) is called once per message.
    On success the message is XACK'd (removed from the group's pending
    list). On handler exception, the message is intentionally NOT acked —
    it stays pending and will be redelivered on the next XREADGROUP call
    (or can be claimed by XCLAIM/XAUTOCLAIM for a dead-consumer scenario,
    not implemented here since we run a single consumer per group, same
    as our single-Kafka-consumer setup did).

    Runs forever, same shape as the old `while True:` reconnect loop —
    call this from inside your own try/except + backoff wrapper exactly
    like the Kafka version did, this function itself doesn't retry.
    """
    await ensure_group(redis, stream, group)

    while True:
        entries = await redis.xreadgroup(
            groupname=group,
            consumername=consumer_name,
            streams={stream: ">"},   # ">" = only new, undelivered messages
            count=10,
            block=block_ms,
        )
        if not entries:
            continue  # timed out waiting, loop again — same as Kafka's poll timeout

        for _stream_name, messages in entries:
            for msg_id, fields in messages:
                payload = json.loads(fields.get("payload", "{}"))
                key = fields.get("key")
                try:
                    await handler(payload, key)
                    await redis.xack(stream, group, msg_id)
                except Exception as e:
                    log.error(
                        "redis_stream.handler_failed",
                        stream=stream, msg_id=msg_id, error=str(e),
                        exc_info=True,
                    )
                    # not acked — will be redelivered next XREADGROUP call