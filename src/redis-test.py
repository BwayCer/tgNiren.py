#!/usr/bin/env python3


import redis

dbR = redis.StrictRedis(
    host = 'localhost',
    port = 6379,
    decode_responses = True
)
print('---')
print(dbR.get('b'))
print(dbR.keys())
dbR.set('a', 3)
print(type(dbR.get('a')))
for idx in range(3):
    dbR.rpush('l', idx)
l = dbR.lrange('l', 0, -1)
print(type(l), l)
# print(type(dbR.get('a')))
# dbR.set('name', 'junxi')  # key是"foo" value是"bar" 将键值对存入redis缓存
# print(dbR['name'])
# print(dbR.get('name'))  # 取出键name对应的值
# print(type(dbR.get('name')))

with dbR.pipeline() as pipe:
    while True:
        try:
            pipe.watch('a')
            current_value = pipe.get('a')
            next_value = int(current_value) + 1
            pipe.multi()
            pipe.set('a', next_value)
            pipe.execute()
            break
        except redis.WatchError:
            continue

# redis 指令
# docker run --rm -d --name redis-lab -p 6379:6379 redis
# docker exec -it redis-lab bash
# reis-cli --raw
# https://redis.io/commands/keys
# KEYS *
#
# python
# https://www.jianshu.com/p/2639549bedc8

