import functools
import flask
from flasgger import Swagger
from flask import Flask, jsonify, redirect
import pandas as pd
import random
import time
from datetime import datetime

from database_manager import DatabaseManager

app = Flask(__name__)
swagger = Swagger(app, template_file='swagger.yml')

dm = DatabaseManager()
illnesses = pd.read_csv('storage/databases/illnesses.csv').values
medicines = dm.get_table('medicines')


def requests_logger(f):
    @functools.wraps(f)
    def decorator(*args, **kwargs):
        uid = flask.request.args.get('uid', default=None)
        route = flask.request.path
        body_args = flask.request.json
        query_args = flask.request.args.to_dict()
        start_time = time.time()
        response, status_code = f(*args, **kwargs)
        time_spent = time.time() - start_time
        dm.add_record('requests', [uid, datetime.now().isoformat(),
                                   route, body_args, query_args, round(time_spent, 6),
                                   status_code,
                                   str(response.get_json()).replace('\n', '    ')])
        return response, status_code

    return decorator


@app.route('/')
def hello_world():
    return redirect('/apidocs')


@app.route('/api/log_front_request', methods=['POST'])
def log_front_request():
    data = flask.request.json
    if not data:
        return jsonify(message='Request must have json data'), 400
    dm.add_record('tg_requests', [datetime.now().isoformat(),
                                  data.get('uid'),
                                  data.get('username'),
                                  data.get('func_name'),
                                  data.get('input'),
                                  data.get('time_spent'),
                                  data.get('message')])
    return jsonify(message='OK'), 200


@app.route('/api/get_compliment')
@requests_logger
def get_compliment():
    uid = flask.request.args.get('uid', default='test')
    compliments = dm.get_table('compliments')
    history = dm.get_table('compliments_history')
    history['uid'] = history['uid'].apply(str)
    history['time_since_now'] = history.iso_eventtime.apply(
        lambda x: (datetime.now() - datetime.fromisoformat(x)).seconds)
    history = history[(history.uid == uid) &
                            (history.time_since_now <= 30)]
    index = int(history['compliment_index'].values[-1]) \
        if len(history) > 0 \
        else random.choice(compliments.index.values)
    result = dm.find_record_by_pk('compliments', index, 'text')
    if len(history) == 0:
        dm.add_record('compliments_history', [datetime.now().isoformat(), uid, index])
    return jsonify(message=result), 200


def prepare_illnesses(values):
    res_illnesses = set()
    for i in range(len(values)):
        if str(values[i]) == '1':
            for line in illnesses:
                if line[i + 1] == 1:
                    res_illnesses.add(line[0])
    if 'Сухая' in res_illnesses and 'Жирная' in res_illnesses:
        res_illnesses.add('Комбинированная')
        res_illnesses.remove('Сухая')
        res_illnesses.remove('Жирная')
    advices = {item: set() for item in medicines.index.values}
    for illness in res_illnesses:
        for k in advices:
            if medicines.loc[k].dropna().get(illness):
                advices[k].add(medicines.loc[k].get(illness))
    keys = [k for k in advices]
    for k in keys:
        if len(advices[k]) == 0:
            del advices[k]
        else:
            advices[k] = list(advices[k])
    return list(res_illnesses), advices


@app.route('/api/get_illnesses', methods=['GET'])
@requests_logger
def get_illnesses():
    uid = flask.request.args.get('uid', default='test')
    try:
        values = dm.find_record_by_pk('users', uid, ['q1', 'q2', 'q3', 'q4', 'q5', 'q6', 'q7']).values
    except KeyError as e:
        return jsonify(message=e.args[0]), 404
    user_illnesses, advices = prepare_illnesses(values)
    return jsonify(illnesses=user_illnesses, advices=advices, ), 200


@app.route('/api/get_illnesses', methods=['PUT'])
@requests_logger
def update_illnesses():
    json_data = flask.request.args
    values = [
        json_data.get('q1', default=0),
        json_data.get('q2', default=0),
        json_data.get('q3', default=0),
        json_data.get('q4', default=0),
        json_data.get('q5', default=0),
        json_data.get('q6', default=0),
        json_data.get('q7', default=0),
    ]
    uid = flask.request.args.get('uid', default='test')
    dm.update_or_add_record('users', uid, values)
    user_illnesses, advices = prepare_illnesses(values)
    return jsonify(illnesses=user_illnesses, advices=advices), 200


@app.route('/api/get_clinics')
@requests_logger
def get_clinics():
    response, status_code = get_illnesses()
    if status_code == 404:
        return jsonify(message=f'Нет информации о пройденном тесте!'), 404
    if status_code != 200:
        return jsonify(message=f'Произошла неопределенная ошибка {str(response.json)}'), 500
    uid_illnesses = response.json['illnesses']
    if len(uid_illnesses) == 0:
        return jsonify(message='Вы здоровы, клиника не нужна!'), 200
    clinics = dm.get_table('clinics')
    mapping = {}
    for clinic in clinics.index.values:
        mapping[clinic] = list(filter(
            lambda illness: clinics.loc[clinic][illness] == 1, uid_illnesses))
    clinics_ordered = sorted(mapping.keys(), key=lambda x: len(mapping[x]), reverse=True)
    if len(clinics_ordered) == 0:
        return jsonify(message='Нет подходящих клиник, но мы уже их ищем!'), 200
    best_clinic_name = clinics_ordered[0]
    best_clinic = clinics.loc[best_clinic_name]
    return jsonify(
        message=f'Клиника успешно обнаружена и способна излечить болезней: '
                f'{len(mapping[best_clinic_name])}',
        clinic_site=best_clinic['Сайт'],
        clinic_name=best_clinic_name,
        illnesses=mapping[best_clinic_name]
    ), 200


@app.route('/get_table/<name>')
def get_table(name):
    try:
        table = dm.get_table(name)
        return table.to_html(), 200
    except ModuleNotFoundError as e:
        return str(e), 404


@app.route('/api/get_info/<int:code>')
@requests_logger
def get_code_info(code):
    try:
        res = dm.find_record_by_pk('codes', code, 'Описание')
        return jsonify(message=res), 200
    except KeyError:
        return jsonify(message='Штрих-код не обнаружен в базе!'), 404


@app.route('/api/regular_compliments/set/<int:enable>', methods=['POST'])
@requests_logger
def update_regular_compliments(enable):
    if enable not in (1, 0):
        return jsonify(message=f'Option {enable} is unknown, use 0 or 1'), 400
    uid = flask.request.args.get('uid', default='test')
    dm.update_or_add_record('regular_compliments', uid, [enable])
    return jsonify(message='OK'), 200


@app.route('/api/regular_compliments/get_list')
@requests_logger
def get_regular_users():
    users = dm.get_table('regular_compliments')
    users = list(users[users.status == 1].index.values)
    return jsonify(message='OK', users=users), 200


if __name__ == '__main__':
    app.run()
