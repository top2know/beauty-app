import functools
import os
import logging
import time

from telegram import ReplyKeyboardMarkup
from telegram.ext import CommandHandler, MessageHandler, Filters, Updater, ConversationHandler
import configparser
import requests
import pandas as pd

import pyzbar.pyzbar as pyzbar
import cv2

logging.basicConfig(filename='output.log',
                    level=logging.INFO)

TEST_START, STEP_0, STEP_1, STEP_2, STEP_3, STEP_4, STEP_5, STEP_6, STEP_7 = range(9)
ASK_CODE = 10
WAIT_FOR_FEEDBACK = 15

config = configparser.ConfigParser()
config.read("config")
host_name = config['BOT']['host']


def action_logger(f):
    @functools.wraps(f)
    def decorator(*args, **kwargs):
        update, context = [*args]
        start_time = time.time()
        res, message = f(*args, **kwargs)
        requests.post(f'{host_name}/api/log_front_request', json={
            'uid': update.effective_user.id,
            'input': update.message.text,
            'username': update.effective_user.username,
            'time_spent': round(time.time() - start_time, 6),
            'func_name': f.__name__,
            'message': str(message).replace('\n', '    ')
        })
        return res

    return decorator


@action_logger
def start(update, context):
    reply_keyboard = [
        'Пройти тест',
        'Записаться в клинику',
        'Загрузить штрих-код',
        'Обратная связь',
        'Получить комплимент']

    message = update.message.reply_text("""Привет!

Команды:
/test - пройти тест
/code - узнать сочетаемость продукта с вашей кожей по штрих-коду
/feedback - оставить обратную связь
/clinic - записаться в клинику для детальной диагностики кожи
/compliment - для хорошего настроения""",
                                        reply_markup=ReplyKeyboardMarkup(
                                            [reply_keyboard],
                                            one_time_keyboard=True
                                        ))
    return ConversationHandler.END, 'OK'


@action_logger
def echo(update, context):
    reply_keyboard = [
        'Пройти тест',
        'Записаться в клинику',
        'Загрузить штрих-код',
        'Обратная связь',
        'Получить комплимент']

    message = update.message.reply_text("""Привет!

Команды:
/test - пройти тест
/code - узнать сочетаемость продукта с вашей кожей по штрих-коду
/feedback - оставить обратную связь
/clinic - записаться в клинику для детальной диагностики кожи
/compliment - для хорошего настроения""",
                                        reply_markup=ReplyKeyboardMarkup(
                                            [reply_keyboard],
                                            one_time_keyboard=True
                                        ))
    return ConversationHandler.END, 'OK'


@action_logger
def get_compliment(update, context):
    response = requests.get(f'{host_name}/api/get_compliment', params={
        'uid': update.effective_user.id
    })
    message = context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=response.json()['message'])
    return ConversationHandler.END, message.text


def csv_to_pandas_df(file_link):
    with open('my_file.csv', "wb") as file:
        response = requests.get(file_link)
        file.write(response.content)
    res = pd.read_csv('my_file.csv')
    os.remove('my_file.csv')
    return res


def test_results(update, response, messages):
    if len(response['illnesses']) == 0:
        messages.append(update.message.reply_text(f'С вашей кожей все хорошо!').text)
    else:
        messages.append(
            update.message.reply_text(f'Количество потенциальных проблем с кожей: {len(response["illnesses"])}\n'
                                      f'Перечень: ' + ', '.join(response['illnesses'])).text)
        advices = response['advices']
        if 'Рекомендуемые вещества в составе' in advices:
            messages.append(update.message.reply_text('Рекомендуемые вещества в составе: '
                                                      + ','.join(advices['Рекомендуемые вещества в составе'])).text)
            del advices['Рекомендуемые вещества в составе']
        messages.append(update.message.reply_text("""Рекомендуемые средства:
""" + '\n'.join([k + ': ' + ','.join(response['advices'][k]) for k in advices])).text)
    return messages


@action_logger
def get_step_0(update, context):
    response = requests.get(f'{host_name}/api/get_illnesses',
                            params={
                                'uid': update.effective_user.id
                            })
    if response.status_code == 404:
        return get_step_1(update, context), 'Had no illnesses, switch to test!'
    response = response.json()
    base_message = update.message.reply_text(f'Вы уже проходили тест!').text

    messages = test_results(update, response, [base_message])

    reply_keyboard = ['Нет', 'Да']
    messages.append(update.message.reply_text('Хотите ли вы пройти тест еще раз?',
                                              reply_markup=ReplyKeyboardMarkup(
                                                  [reply_keyboard],
                                                  one_time_keyboard=True
                                              )).text)
    return STEP_0, 'Had previous test results'


@action_logger
def get_step_05(update, context):
    answer = update.message.text
    if answer == 'Да':
        return get_step_1(update, context), 'Retake test'
    return ConversationHandler.END, 'No need to retake test'


@action_logger
def get_step_1(update, context):
    reply_keyboard = ['Нет', 'Да']
    message = update.message.reply_text('Ваша кожа склонна к шелушениям?',
                                        reply_markup=ReplyKeyboardMarkup(
                                            [reply_keyboard],
                                            one_time_keyboard=True
                                        ))
    return STEP_1, message.text


@action_logger
def get_step_2(update, context):
    answer = update.message.text
    context.user_data['q1'] = 1 if answer == 'Да' else 0
    reply_keyboard = ['Нет', 'Да']
    message = update.message.reply_text('Ваша кожа склонна к воспалениям(анке) и черным точкам?',
                                        reply_markup=ReplyKeyboardMarkup(
                                            [reply_keyboard],
                                            one_time_keyboard=True
                                        ))
    return STEP_2, message.text


@action_logger
def get_step_3(update, context):
    answer = update.message.text
    context.user_data['q2'] = 1 if answer == 'Да' else 0
    reply_keyboard = ['Нет', 'Да']
    message = update.message.reply_text('Ваша кожа склонна к жирному блеску?',
                                        reply_markup=ReplyKeyboardMarkup(
                                            [reply_keyboard],
                                            one_time_keyboard=True
                                        ))
    return STEP_3, message.text


@action_logger
def get_step_4(update, context):
    answer = update.message.text
    context.user_data['q3'] = 1 if answer == 'Да' else 0
    reply_keyboard = ['Нет', 'Да']
    message = update.message.reply_text('У вас бывали какие-либо аллергические реакции на коже?',
                                        reply_markup=ReplyKeyboardMarkup(
                                            [reply_keyboard],
                                            one_time_keyboard=True
                                        ))
    return STEP_4, message.text


@action_logger
def get_step_5(update, context):
    answer = update.message.text
    context.user_data['q4'] = 1 if answer == 'Да' else 0
    reply_keyboard = ['Нет', 'Да']
    message = update.message.reply_text('Вас беспокоят морщины на лице?',
                                        reply_markup=ReplyKeyboardMarkup(
                                            [reply_keyboard],
                                            one_time_keyboard=True
                                        ))
    return STEP_5, message.text


@action_logger
def get_step_6(update, context):
    answer = update.message.text
    context.user_data['q5'] = 1 if answer == 'Да' else 0
    reply_keyboard = ['Нет', 'Да']
    message = update.message.reply_text('У вас бывали раздражения от холода/ветра/воды?',
                                        reply_markup=ReplyKeyboardMarkup(
                                            [reply_keyboard],
                                            one_time_keyboard=True
                                        ))
    return STEP_6, message.text


@action_logger
def get_step_7(update, context):
    answer = update.message.text
    context.user_data['q6'] = 1 if answer == 'Да' else 0
    reply_keyboard = ['Нет', 'Да']
    message = update.message.reply_text('Какими средствами для лица обычно пользуетесь? Какая ценовая категория?',
                                        # reply_markup=ReplyKeyboardMarkup(
                                        #     [reply_keyboard],
                                        #     one_time_keyboard=True
                                        # )
                                        )
    return STEP_7, message.text


@action_logger
def finalize_test(update, context):
    context.user_data['q7'] = 0  # 1 if answer == 'Да' else 0
    values = context.user_data
    values['uid'] = update.effective_user.id

    response = requests.put(f'{host_name}/api/get_illnesses', params=values)

    response = response.json()
    messages = test_results(update, response, [])
    return ConversationHandler.END, f'Test completed successfully with {len(messages)} sent messages'


@action_logger
def get_code_message(update, context):
    message = update.message.reply_text('Введите номер штрих-кода или пришлите фотографию')
    return ASK_CODE, message.text


@action_logger
def get_code_from_text(update, context):
    code = update.message.text
    message = update.message.reply_text(requests.get(f'{host_name}/api/get_info/{code}').json()['message'])
    return ConversationHandler.END, message.text


@action_logger
def get_code_from_image(update, context):
    path = context.bot.get_file(update.message.photo[-1].file_id).file_path
    # print(path)
    with open('file.jpg', 'wb') as f:
        f.write(requests.get(path).content)

    def decode(img):
        # Find barcodes and QR codes
        decoded_objects = pyzbar.decode(img)
        # Print results
        # for obj in decoded_objects:
            # print('Type : ', obj.type)
            # print('Data : ', obj.data, '\n')
        return decoded_objects

    im = cv2.imread('file.jpg')
    decodedObjects = decode(im)

    if len(decodedObjects) == 0:
        message = update.message.reply_text('Штрих-коды не обнаружены!')
    elif len(decodedObjects) > 1:
        message = update.message.reply_text('Несколько штрих-кодов!')
    else:
        message = update.message.reply_text(requests.get(
                f'{host_name}/api/get_info/{decodedObjects[0].data.decode("UTF-8")}').json()['message'])

    return ConversationHandler.END, message.text


@action_logger
def get_clinic(update, context):
    response = requests.get(f'{host_name}/api/get_clinics',
                            params={
                                'uid': update.effective_user.id
                            })
    if response.status_code == 404:
        message = update.message.reply_text('Нет информации о пройденном тесте, '
                                            'возможно, вам нужна команда /test')
    elif response.status_code != 200:
        message = update.message.reply_text('Что-то пошло не так :(')
    else:
        response = response.json()
        if response.get('clinic_name') is None:
            message = update.message.reply_text(response['message'])
        else:
            message = update.message.\
                reply_text(f"Лучшая клиника: {response['clinic_name']}\n"
                           f"Сайт: {response['clinic_site']}\n\n"
                           f"Работают со следующими проблемами с кожей: {', '.join(response['illnesses'])})")
    return ConversationHandler.END, message.text


@action_logger
def ask_feedback(update, context):
    message = update.message.reply_text('Введите текст в следующем сообщении.')
    return WAIT_FOR_FEEDBACK, message.text


@action_logger
def get_feedback(update, context):
    message = update.message.reply_text('Спасибо за обратную связь, она помогает нам стать лучше!')
    return ConversationHandler.END, message.text


@action_logger
def cancel(update, context):
    message = update.message.reply_text('Выполнение прервано!')
    return ConversationHandler.END, message.text


def run():
    updater = Updater(token=config['BOT']['token'], use_context=True)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('compliment', get_compliment))
    dispatcher.add_handler(MessageHandler(Filters.regex('Получить комплимент'), get_compliment))
    dispatcher.add_handler(CommandHandler('clinic', get_clinic))
    dispatcher.add_handler(MessageHandler(Filters.regex('Записаться в клинику'), get_clinic))
    dispatcher.add_handler(CommandHandler('help', echo))
    dispatcher.add_handler(MessageHandler(Filters.regex('Помощь'), echo))

    test_handler = ConversationHandler(
        entry_points=[CommandHandler('test', get_step_0),
                      MessageHandler(Filters.regex('Пройти тест'), get_step_0)],
        states={
            STEP_0: [MessageHandler(Filters.text & ~Filters.command, get_step_05)],
            STEP_1: [MessageHandler(Filters.text & ~Filters.command, get_step_2)],
            STEP_2: [MessageHandler(Filters.text & ~Filters.command, get_step_3)],
            STEP_3: [MessageHandler(Filters.text & ~Filters.command, get_step_4)],
            STEP_4: [MessageHandler(Filters.text & ~Filters.command, get_step_5)],
            STEP_5: [MessageHandler(Filters.text & ~Filters.command, get_step_6)],
            STEP_6: [MessageHandler(Filters.text & ~Filters.command, get_step_7)],
            STEP_7: [MessageHandler(Filters.text & ~Filters.command, finalize_test)]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    dispatcher.add_handler(test_handler)

    code_handler = ConversationHandler(
        entry_points=[CommandHandler('code', get_code_message),
                      MessageHandler(Filters.regex('Загрузить штрих-код'), get_code_message)],
        states={
            ASK_CODE: [MessageHandler(Filters.text & ~Filters.command, get_code_from_text),
                       MessageHandler(Filters.photo & ~Filters.command, get_code_from_image)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    dispatcher.add_handler(code_handler)

    feedback_handler = ConversationHandler(
        entry_points=[CommandHandler('feedback', ask_feedback),
                      MessageHandler(Filters.regex('Обратная связь'), ask_feedback)],
        states={
            WAIT_FOR_FEEDBACK: [MessageHandler(Filters.text & ~Filters.command, get_feedback)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    dispatcher.add_handler(feedback_handler)

    echo_handler = MessageHandler(Filters.text & (~Filters.command), echo)
    echo_handler2 = MessageHandler(Filters.document & (~Filters.command), echo)
    dispatcher.add_handler(echo_handler)
    dispatcher.add_handler(echo_handler2)

    updater.start_polling()


if __name__ == '__main__':
    run()
