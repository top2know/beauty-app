import flask
from flask import Flask, jsonify, redirect
import pandas as pd
import bot
import random

app = Flask(__name__)

illnesses = pd.read_csv('storage/databases/illnesses.csv').values
codes = pd.read_csv('storage/databases/codes.csv').values
compliments = pd.read_csv('storage/databases/compliments.csv', sep=';')['Text']


@app.route('/')
def hello_world():
    return 'Hello!'


@app.route('/get_compliment')
def get_compliment():
    return jsonify(message=compliments[random.randint(0, len(compliments))])


@app.route('/get_illnesses')
def get_illnesses():
    json_data = flask.request.args
    values = [
        json_data.get('step_1', default=0),
        json_data.get('step_2', default=0),
        json_data.get('step_3', default=0),
        json_data.get('step_4', default=0),
        json_data.get('step_5', default=0),
    ]
    res_illnesses = set()
    for i in range(len(values)):
        if values[i] == '1':
            for line in illnesses:
                if line[i + 1] == 1:
                    res_illnesses.add(line[0])
    return jsonify(illnesses=list(res_illnesses))


@app.route('/get_info/<code>')
def get_code_info(code):
    res = 'Штрих-код не обнаружен в базе!'
    for line in codes:
        if str(line[0]) == code:
            res = line[1]
            break
    return jsonify(message=res)





bot.run()


if __name__ == '__main__':
    app.run()
