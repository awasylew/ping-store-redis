from flask import Flask, request, url_for, jsonify, render_template

"""
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Boolean, Float
from sqlalchemy.orm import sessionmaker
from sqlalchemy import func
from sqlalchemy import case, literal_column
"""
import redis
import json

import random
import datetime
import os

# REDIS - odpowiednikiem będzie dostęp do Redis, może ma sens wersja uogólniona? powinno dać się wybierać SQL albo Redis parametrem
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('STORE_DB')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = True

# REDIS - oby nie było potrzeba takiej zabawy z Redis
aw_testing = bool(os.getenv('aw_testing'))
if aw_testing:
    Base = declarative_base()
    class Dummy: pass
    request = Dummy()
# else:     # redis-off
#    db = SQLAlchemy(app)     # redis-off
#    Base = db.Model            # redis-off

# kv czyli key-value podobnie do db
kv=redis.StrictRedis(decode_responses=True)

"""
redis-off
REDIS a może jednak stosować strukturę (tę albo inną) do przekazywania danych
class PingResult(Base):

    __tablename__ = 'ping_results'

    id = Column(Integer, primary_key=True)
    time = Column(String(14))                   #YYYYmmddHHMMSS  # co jeśli dłuższe? dodać badanie długości?
    origin = Column(String(20))             # j.w.
    target = Column(String(20))             # j.w.
    success = Column(Boolean)
    rtt = Column(Float)

    def __repr__(self):
        return "PingResult(id=%s, time=%s, origin=%s, target=%s, succes=%s, rtt=%s)" % \
            (self.id, self.time, self.origin, self.target, self.success, self.rtt)
    def to_dict(self):
        return {'id':self.id, 'time':str(self.time), \
            'origin':str(self.origin), 'target':str(self.target), \
            'success':self.success, 'rtt':self.rtt}
"""

"""
REDIS
wartości w redis jako JSON
id - niestosowne; może trzeba odtworzyć dla kompatybilności? może wykorzystać tutaj jakieś przekształcenie klucza ping_result?
time - data/godzina/minuta tylko jako klucz; sekunda w wartości
origin - tylko jako klucz
target - tylko jako klucz
sucess - w wartości
rtt - w wartości

ping_result:A8:onet:20171216:08:34:6  -> PingResult{success:true, rtt:34.7}

list_origins -> SET{A8,ESP}                     //ttl - jakie wygasanie?
list_targets:A8  -> SET{onet,wp}                //ttl - wygasanie per origin?
list_days:A8:onet -> SET{20171216,20171217}
list_hours:A8:onet:20171216  -> SET{08,09,10}
list_minutes:A8:onet:20171216:8  -> SET{04,06,08,10}

hour_aggr:A8:onet:20171216:08:*
    :count (integer)
    :count_success (integer)
    :rtt_sum (integer/float) - czy może pozostać taka niepewność co do typu?
    :rtt_min (i/f)
    :rtt_max (i/f)

godziny, minuty, sekundy - zawsze dwycyfrowe, z ew. zerem na początku
"""

# REDIS nie będzie potrzeby
if aw_testing:
    engine = create_engine(os.getenv('STORE_TEST_DB'), echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    test_session = Session()
    db = Dummy()
    db.session = test_session
else:
    pass

# REDIS: niepotrzebne?
@app.route('/makedb')
def make_database():
    """zainicjowanie schematu bazy danych (potrzebne szczególnie dla baz ulotnych, typowo w pamięci)"""
    """test: na razie bez testowania, bo zbyt pokręcone mockowanie"""
    """test: brak bazy, operacja bazodanowa powoduje błąd"""
    """test: brak bazy, make_database(), operacja bazodanowa się udaje"""
    db.create_all()
    return 'db created!', 200

# REDIS - przerobione na wersję Redis, wymagany merge z SQL i test
@app.route('/sample-results')
def sample_results():
    """wstawienie przykładowych wyników ping (wartości losowe, czas bieżący)"""
    """bez testowania, bo to metoda nieprodukcyjna"""
    for i in range(100):
        time=(datetime.datetime.now()-datetime.timedelta(minutes=i)).strftime('%Y%m%d%H%M%S')
        rtt = float(random.randrange(50))/10
        if rtt < 0.2:
            rtt = None
        """ REDIS-off
        # dlaczego tutaj używamy post zamiast session.add?
        pings_post_generic({'origin':'sample-'+random.choice(['a', 'b', 'c']), \
            'target':'sample-'+random.choice(['1', '2', '3']), \
            'success':bool(rtt>0) rtt is not None, 'rtt':rtt ::if rtt>0 else None::, 'time':time})
        """
        add_ping_redis(origin='sample-'+random.choice(['a', 'b', 'c']),
            target='sample-'+random.choice(['1', '2', '3']),
            day=time[0:8], hour=time[8:10], minute=time[10:12], second=time[12:14],
            success=(rtt is not None),
            rtt=rtt)
    return 'posted!', 200

# REDIS: choroba... cała ta konstrukcja ścieśle nastawiona na SQLAlchemy
# lepsza organizacja query_add_args_*: jedne procedura ze wskazaniem, które części uwzględniać bool, z jakimś default?"""
def query_add_args_id(q):
    """dodanie do zapytania SQLAlchemy warunku na id jeśli występuje w parametrach wywołania HTTP"""
    """testy --> get_pings"""
    id = request.args.get('id')
    if id is not None:
        q = q.filter(PingResult.id==id)
    return q

def query_add_args_time(q):
    """dodanie do zapytania SQLAlchemy warunków czasowych jeśli występują w parametrach wywołania HTTP"""
    """testy --> get_pings"""
    start = request.args.get('start')
    if start is not None:
        q = q.filter(PingResult.time>=start)
    end = request.args.get('end')
    if end is not None:
        q = q.filter(PingResult.time<end)
    prefix = request.args.get('time_prefix')
    if prefix is not None:
        q = q.filter(PingResult.time.like(prefix+'%'))
    return q

def query_add_args_hosts(q):
    """dodanie do zapytania SQLAlchemy warunków dotyczących hostów jeśli występują w parametrach wywołania HTTP"""
    """testy --> get_pings"""
    origin = request.args.get('origin')
    if origin is not None:
        q = q.filter(PingResult.origin==origin)
    target = request.args.get('target')
    if target is not None:
        q = q.filter(PingResult.target==target)
    return q

def query_add_args_window(q):
    """dodanie do zapytania SQLAlchemy warunków ograniczająych liczbę wyników jeśli występują w parametrach wywołania HTTP"""
    """testy limit --> get_pings"""
    """test: offset??? jak to zrobić bez gwarantowanej kolejności?"""
    # jakiś default na limit?
    limit = request.args.get('limit')
    if limit is not None:
        q = q.limit(limit)
    offset = request.args.get('offset')
    if offset is not None:
        q = q.offset(offset)
    return q

def query_add(q, id=False, time=False, hosts=False, window=False):
    """uniwersalna metoda dodająca poszczególne rodzaje testów"""
    if id:
        q = query_add_args_id(q)
    if time:
        q = query_add_args_time(q)
    if hosts:
        q = query_add_args_hosts(q)
    if window:
        q = query_add_args_window(q)
    return q

# REDIS: gruby znak zapytania w jakiej części to odtwarzać - mało pasuje do key-value :(
def get_pings():
    # a powinien zwracać obiekty czy już słowniki?
    """zwrócenie listy wyników ping ograniczonych parametrami wywołania HTTP"""
    """test: dorobic jeszcze offset, ale najpierw sortowanie?"""
    q = db.session.query(PingResult)
    q = query_add(q, id=True, time=True, hosts=True, window=True)
    # jakies sortowanie?
    return q.all()

# ho, ho, ho - zrobić do tego unit testy!!!
# najlepiej od razu takie, które pojadą dla wersji SQL i Redis jednocześnie
def get_pings_redis(origin, target, start=None, end=None, time_prefix=None):
    result = []
    days = kv.smembers('list_days:'+origin+':'+target)
    for day in days:
        if (start is not None) and (day<start[:8]):
            continue
        if (end is not None) and (day>end[:8]):
            continue
        if (time_prefix is not None) and (day[:len(time_prefix)]!=time_prefix[:8]):
            continue
        hours = kv.smembers('list_hours:'+origin+':'+target+':'+day)
        for hour in hours:
            if (start is not None) and (day+hour<start[:10]):
                continue
            if (end is not None) and (day+hour>end[:10]):
                continue
            if (time_prefix is not None) and ((day+hour)[:len(time_prefix)]!=time_prefix[:10]):
                continue
            minutes = kv.smembers('list_minutes:'+origin+':'+target+':'+day+':'+hour)
            for minute in minutes:
                if (start is not None) and (day+hour+minute<start[:12]):
                    continue
                if (end is not None) and (day+hour+minute>end[:12]):
                    continue
                if (time_prefix is not None) and ((day+hour+minute)[:len(time_prefix)]!=time_prefix[:12]):
                    continue
                ping = json.loads(kv.get('ping_results:'+origin+':'+target+':'+day+':'+hour+':'+minute))
                second = ping['second']
                time = day+hour+minute+ping['second']
                if (start is not None) and (time<start):
                    continue
                if (end is not None) and (time>end):
                    continue
                if (time_prefix is not None) and (time[:len(time_prefix)]!=time_prefix):
                    continue
                result.append({'origin':origin, 'target':target, 'time':time,
                    'success':ping['success'], 'rtt':ping['rtt']})
    return result

@app.route('/pings')
def get_pings_redis_view():
    origin = request.args.get('origin')    # TODO musi być podany
    target = request.args.get('target')     # TODO musi być podany
    start = request.args.get('start')       # opcjonalny, jeśli nie ma to None jest przekazywany do get_pings_redis
    end = request.args.get('end')       # opcjonalny, jeśli nie ma to None jest przekazywany do get_pings_redis
    time_prefix = request.args.get('time_prefix')       # opcjonalny, jeśli nie ma to None jest przekazywany do get_pings_redis
    return jsonify(get_pings_redis(origin, target, start, end, time_prefix)), 200

#@app.route('/pings')
def get_pings_view():
    pd = [i.to_dict() for i in get_pings()]
    return jsonify(pd), 200

def get_pings_id(id):
    """zwrócenie pojedynczego wyniku wg id"""
    q = db.session.query(PingResult).filter(PingResult.id==id)
    return q.first()

@app.route('/pings/<int:id>')
def get_pings_id_view(id):
    """pojedynczy wyniku wg id w ścieżce"""
    r = get_pings_id(id)
    if r is None:
        return 'Not found', 404
    return jsonify(r.to_dict()), 200

# REDIS: zapisywanie pojedynczego jako LOG (z TTL?) oraz agregaty (z TTL?)
def pings_post_generic(args):
    """wstawienie pojedynczego pinga do bazy danych"""
    """test: pusta baza, wstawienie, w bazie dokładnie ten jeden"""
    """test: dwukrotne wstawione z tym samym id -> błąd"""
    """test: pusta baza, wstawienie, ponowne wstawienie (dokładnie taki sam czy zmieniony?), w bazie dokładnie jeden"""
    """test: różne wersje niepoprawnych argumentów z listy przykładowych"""
    # args powinno być neutralnym słownikiem, a nie dopasowane do request!
    # a może nie słownik, tylko zwykłe parametry wywołania?
    # dodać testy na sprawdzenia parametrów
    # jak już jeden, to nazwa generic średnia

    id = args.get('id')
	# dozwolony tutaj?
	# kontrole
	# błąd przy podaniu istniejącego?

    time = args.get('time')
    # kontrola czy jest
    # kontrola czy poprawny
    # kontrola czy nie odrzucić z powodu starości
    if time=="now":
        time = datetime.datetime.now().strftime('%Y%m%d%H%M%S')

    origin = args.get('origin')
    # kontrole ...

    target = args.get('target')
    # kontrole ...

    success = args.get('success')
    # kontrole ...

    rtt = args.get('rtt')
    # kontrole

    p = PingResult(id=id, time=time, origin=origin, target=target, \
        success=success, rtt=rtt)
    db.session.add(p)
    db.session.commit()
    # czy nie powinno być zabezpieczenia przed podwójnym wstawieniem tego samego?
    # np. wg klucza na origin+target+time?
    # cel: idempotentność przy ponowieniu wstawiania

    # wydzielić fragment ustalający scheme albo Location do oddzielnej procedury
    # i wtedy własne testy jednostkowe
    scheme = request.headers.get('X-Forwarded-Proto')       # metoda specyficzna na heroku, czy będzie dobrze działać w innych układach?
    if scheme is None:
        scheme = request.scheme

    return app.make_response((jsonify(p.to_dict()), 201, \
        {'Location':  url_for('get_pings_id_view', id=p.id, _scheme=scheme, _external=True)}))

#REDIS @app.route('/pings-old', methods=['POST'])
def pings_post():
    """wstawienie pojedynczego pinga metodą POST"""
    """test: sprawdzenie, że parametry dobrze przechodzą przez treść POSTa???"""
    return pings_post_generic(request.json)

#REDIS @app.route('/pings-post')    # do testów, !!! ping-probe umie na razie tylko GET, już nieprawda
def pings_post_pseudo():
    # zmienić nazwę na pseudo_post_pings
    args = {k:request.args.get(k) for k in request.args}
    succ_arg = args.get('success')
    success = succ_arg is not None and succ_arg.upper() not in ['FALSE', '0']
    args['success'] = success
    return pings_post_generic(args)

def add_ping(p):
    """wstawianie nowego obiektu PingResult do bazy"""
    # bez commit - zrobić w view
    # kiedy walidacja wartości w polach?
    # kiedy walidacja JSON?
    db.session.add(p)


#REDIS @app.route('/pings-old', methods=['POST'])
@app.route('/pings-post')
def pings_post_redis_view():
    # id = args.get('id')
    args=request.args
    time = args.get('time')
    if time=="now":
        time = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    origin = args.get('origin')
    target = args.get('target')
    success = args.get('success')
    rtt = args.get('rtt')
    add_ping_redis(origin, target, time[0:8], time[8:10], time[10:12], time[12:14], success, rtt)
    return 'posted!', 200

def add_ping_redis(origin, target, day, hour, minute, second, success, rtt):
    # TODO ustawianie ttl

    kv.sadd('list_origins', origin)
    kv.sadd('list_targets:'+origin, target)
    kv.sadd('list_days:'+origin+':'+target, day)
    kv.sadd('list_hours:'+origin+':'+target+':'+day, hour)
    kv.sadd('list_minutes:'+origin+':'+target+':'+day+':'+hour, minute)
    kv.set('ping_results:'+origin+':'+target+':'+day+':'+hour+':'+minute,
        json.dumps({'second':second, 'success':success, 'rtt':rtt}))

    key = 'hour_aggr:'+origin+':'+target+':'+day+':'+hour
    kv.incr(key+':count')
    if success:
        kv.incr(key+':count_success')
    else:
        kv.incrby(key+':count_success', 0)

    if rtt is not None:
        kv.incrbyfloat(key+':rtt_sum', rtt)
        rtt_min=kv.get(key+':rtt_min')
        if rtt_min is None:
            rtt_min=rtt
        else:
            rtt_min=min(float(rtt_min), float(rtt))
        kv.set(key+':rtt_min', str(rtt_min))
        rtt_max=kv.get(key+':rtt_max')
        if rtt_max is None:
            rtt_max=rtt
        else:
            rtt_max=max(float(rtt_max), float(rtt))
        kv.set(key+':rtt_max', str(rtt_max))

@app.route('/pings', methods=['POST'])
def ping_post_view():
    j = request.get_json(force=True) # brak obsługi błędów formatu #force z powodu zappa@lambda
    # dozwolony brak id, brak pozostałych spowoduje błąd
    if j['time'] == 'now':
        time = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    else:
        time = j['time']
    p = PingResult( id=j.get('id'), time=time, origin=j['origin'], \
        target=j['target'], success=j['success'], rtt=j['rtt'])
    add_ping(p)
    db.session.commit()
    return 'posted!'

# REDIS: usuwanie logów czy agregatów czy both?
@app.route('/pings', methods=['DELETE'])
def pings_delete():
    # zmienić nazwę na delete_pings
    """usuwanie wpisów wg zadanych kryteriów"""
    """test: przykładowa baza, kilka ręcznie przygotowanych warunków, sprawdzanie liczności wyniku po usunięciu"""
    """test: j.w. tylko z warunkami"""
    q = db.session.query(PingResult)
    """q = query_add_args_id(q)
    q = query_add_args_time(q)
    q = query_add_args_hosts(q)"""
    q = query_add(q, id=True, time=True, hosts=True)
    q.delete(synchronize_session=False)
    db.session.commit()
    return 'deleted!', 204

# REDIS hierarchia origins->targets->pingi/agregaty
# origins -> {ESP, A8}
# origins:1 -> ESP, origins:2 -> A8
#@app.route('/origins')
def get_origins_view():
    """listuje wszystkie origins do wyboru"""
    """test: pusta baza, kilka wstawień, sprawdzenie wyniku na zgodność"""
    """test: j.w. tylko z warunkami"""
    q = db.session.query(PingResult.origin).distinct()
    # jakieś sortowanie?
    """q = query_add_args_time(q)
    q = query_add_args_hosts(q)
    q = query_add_args_window(q)"""
    q = query_add(q, time=True, hosts=True, window=True)
    l = []
    for i in q:
        origin = i[0]     # i.origin?
        links = [{'rel':'targets', 'href':url_for('get_targets', origin=origin, _external=True)}]
            # url_for nie potrzebuje zabazy w scheme?
        l.append({'origin':origin, 'links':links})
    return jsonify(l), 200

@app.route('/origins')
def get_origins_redis_view():
    origins = kv.smembers('list_origins')
    result = []
    for origin in origins:
        links = [{'rel':'targets', 'href':url_for('get_targets_redis_view', origin=origin, _external=True)}]
        result.append({'origin':origin, 'links':links})
    return jsonify(result), 200

#@app.route('/targets')      # zmienić nazwę, bo jednak inna funkcja? routes? paths?
def get_targets():
    """listuje możliwe przejścia od origin do target"""
    """test: pusta baza, kilka wstawień, sprawdzenie wyniku na zgodność"""
    """test: j.w. tylko z warunkami"""
    q = db.session.query(PingResult.origin, PingResult.target).distinct() # tak na sztywno czy wg argumentów?
    """q = query_add_args_time(q)
    q = query_add_args_hosts(q)
    q = query_add_args_window(q)"""
    q = query_add(q, time=True, hosts=True, window=True)
    l = []
    for i in q:
        origin = i[0]       # i.origin?
        target = i[1]       # i.target?
        links = []
        links.append({'rel':'pings', 'href':url_for('get_pings_view', origin=origin, target=target, _external=True)})
        links.append({'rel':'minutes', 'href':url_for('get_minutes', origin=origin, target=target, _external=True)})
        links.append({'rel':'hours', 'href':url_for('get_hours', origin=origin, target=target, _external=True)})
        l.append({'target':target, 'links':links})
    return jsonify(l), 200

@app.route('/targets')
def get_targets_redis_view():
    origin = request.args.get('origin')    # TODO musi być obecny
    targets = kv.smembers('list_targets:'+origin)
    result = []
    for target in targets:
        links = []
        links.append({'rel':'pings', 'href':url_for('get_pings_redis_view', origin=origin, target=target, _external=True)})
        links.append({'rel':'minutes', 'href':url_for('get_minutes_redis_view', origin=origin, target=target, _external=True)})
        links.append({'rel':'hours', 'href':url_for('get_hours_redis_view', origin=origin, target=target, _external=True)})
        result.append({'target':target, 'links':links})
    return jsonify(result), 200

#@app.route('/minutes')
def get_minutes():
    """..."""
    """test: ..."""
    return get_periods('minute', 12)

#@app.route('/hours')
def get_hours():
    """..."""
    """test: ..."""
    return get_periods('hour', 10)

def get_periods( period_name, prefix_len ):
    """wyciąga zagregowane wyniki dla wybranego okresu (leksykograficznie)"""
    """test:..."""
    q = db.session.query(PingResult.origin.label('origin'),
        PingResult.target.label('target'), \
        func.substr(PingResult.time,1,prefix_len).label('prefix'),
        func.min(PingResult.rtt).label('min_rtt'),
        func.avg(PingResult.rtt).label('avg_rtt'),
        func.max(PingResult.rtt).label('max_rtt'),
        func.count(PingResult.success).label('count_all'),
        func.count(case([((PingResult.success==True), PingResult.success)], else_=literal_column("NULL"))).label('count_success'))
    """q = query_add_args_time(q)
    q = query_add_args_hosts(q)"""
    q = query_add(q, time=True, hosts=True)
    q = q.group_by( PingResult.origin, PingResult.target, \
        func.substr(PingResult.time,1,prefix_len))
    # czy powinno być offset/limit? czy to ma zastosowanie do GROUP BY?
    l = []
    for i in q:
        origin = i.origin #i[0]
        target = i.target #i[1]
        prefix = i.prefix #i[2]
        min_rtt = i.min_rtt #i[3]
        avg_rtt = i.avg_rtt #i[4]
        max_rtt = i.max_rtt #i[5]
        count_all = i.count_all #123 #count1.count()
        count_success = i.count_success #23 #
        l.append({'origin':origin, 'target':target, period_name:prefix, \
            'count':count_all, \
            'count_success':count_success, \
            'avg_rtt': avg_rtt, 'min_rtt': min_rtt, 'max_rtt': max_rtt, \
            'links':[{'rel':'pings', 'href':url_for('get_pings_view', origin=origin, \
                target=target, time_prefix=prefix, _external=True)}]})
    return jsonify(l), 200

def get_hours_redis(origin, target):
    result = []
    days = kv.smembers('list_days:'+origin+':'+target)
    for day in days:
        hours = kv.smembers('list_hours:'+origin+':'+target+':'+day)
        for hour in hours:
            key='hour_aggr:'+origin+':'+target+':'+day+':'+hour
            result.append({'origin':origin, 'target':target,
                'hour': day+hour,
                'count': int(kv.get(key+':count')),
                'count_success': int(kv.get(key+':count_success')),
                'avg_rtt': float(kv.get(key+':rtt_sum'))/
                    int(kv.get(key+':count_success')),
                'min_rtt': float(kv.get(key+':rtt_min')),
                'max_rtt': float(kv.get(key+':rtt_max')),
                'links':[{'rel':'pings', 'href':url_for('get_pings_redis_view',
                    origin=origin, target=target, time_prefix=day+hour, _external=True)}]})
    return result

def all_minutes(origin, target):
    for day in kv.smembers('list_days:'+origin+':'+target):
        for hour in kv.smembers('list_hours:'+origin+':'+target+':'+day):
            for minute in kv.smembers('list_minutes:'+origin+':'+target+':'+day+':'+hour):
                yield (day, hour, minute)

# może dodać ograniczenie na start/end/time-prefix
# może zrobić skróty for+for -> yield
# PROBLEM: nie ma danych do agregatów minutowych!!!
def get_minutes_redis(origin, target):
    result = []
    for (day, hour, minute) in all_minutes(origin, target):
        result.append({'origin':origin, 'target':target,
            'minute':day+hour+minute,
            'count': 1,
            'count_success':2,
            'avg_rtt':2.2, 'min_rtt':1.1, 'max_rtt':3.3,
            'links':[{'rel':'pings', 'href':url_for('get_pings_redis_view',
                origin=origin, target=target, time_prefix=day+hour+minute, _external=True)}]})
    return result


@app.route('/hours')
def get_hours_redis_view():
    origin = request.args.get('origin')    # TODO musi być podany
    target = request.args.get('target')     # TODO musi być podany
    return jsonify(get_hours_redis(origin, target)), 200

@app.route('/minutes')
def get_minutes_redis_view():
    origin = request.args.get('origin')    # TODO musi być podany
    target = request.args.get('target')     # TODO musi być podany
    return jsonify(get_minutes_redis(origin, target)), 200


@app.route('/')
def root():
    """strona pomocnicza"""
    return render_template('index.html')

if __name__ == '__main__':
    port = int(os.getenv("PORT"))
    # app.run(debug=True)
    app.run(host='0.0.0.0', port=port)
