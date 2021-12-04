import os
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import CommandHandler, MessageHandler, Filters, Updater, ConversationHandler
import configparser
import requests
import pandas as pd

import pyzbar.pyzbar as pyzbar
import cv2

TEST_START, STEP_1, STEP_2, STEP_3, STEP_4, STEP_5, STEP_6, STEP_7 = range(8)
ASK_CODE = 10
WAIT_FOR_FEEDBACK = 15


config = configparser.ConfigParser()
config.read("config")
host_name = config['BOT']['host']


def start(update, context):

    reply_keyboard = [
        'Пройти тест',
        'Записаться в клинику',
        'Загрузить штрих-код',
        'Обратная связь',
        'Получить комплимент']

    update.message.reply_text("""Привет!

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


def echo(update, context):

    reply_keyboard = [
        'Пройти тест',
        'Записаться в клинику',
        'Загрузить штрих-код',
        'Обратная связь',
        'Получить комплимент']

    update.message.reply_text("""Команды:
/test - пройти тест
/code - узнать сочетаемость продукта с вашей кожей по штрих-коду
/feedback - оставить обратную связь
/clinic - записаться в клинику для детальной диагностики кожи
/compliment - для хорошего настроения""",
                              reply_markup=ReplyKeyboardMarkup(
                                  [reply_keyboard],
                                  one_time_keyboard=True
                              ))


def get_compliment(update, context):
    response = requests.get(f'{host_name}/get_compliment')
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text=response.json()['message'])


def csv_to_pandas_df(file_link):
    with open('my_file.csv', "wb") as file:
        response = requests.get(file_link)
        file.write(response.content)
    res = pd.read_csv('my_file.csv')
    os.remove('my_file.csv')
    return res


def get_step_1(update, context):
    reply_keyboard = ['Нет', 'Да']
    update.message.reply_text('Ваша кожа склонна к шелушениям?',
                              reply_markup=ReplyKeyboardMarkup(
                                  [reply_keyboard],
                                  one_time_keyboard=True
                              ))
    return STEP_1


def get_step_2(update, context):
    answer = update.message.text
    context.user_data['step_1'] = 1 if answer == 'Да' else 0
    reply_keyboard = ['Нет', 'Да']
    update.message.reply_text('Ваша кожа склонна к воспалениям(анке) и черным точкам?',
                              reply_markup=ReplyKeyboardMarkup(
                                  [reply_keyboard],
                                  one_time_keyboard=True
                              ))
    return STEP_2


def get_step_3(update, context):
    answer = update.message.text
    context.user_data['step_2'] = 1 if answer == 'Да' else 0
    reply_keyboard = ['Нет', 'Да']
    update.message.reply_text('Ваша кожа склонна к жирному блеску?',
                              reply_markup=ReplyKeyboardMarkup(
                                  [reply_keyboard],
                                  one_time_keyboard=True
                              ))
    return STEP_3


def get_step_4(update, context):
    answer = update.message.text
    context.user_data['step_3'] = 1 if answer == 'Да' else 0
    reply_keyboard = ['Нет', 'Да']
    update.message.reply_text('У вас бывали какие-либо аллергические реакции на коже?',
                              reply_markup=ReplyKeyboardMarkup(
                                  [reply_keyboard],
                                  one_time_keyboard=True
                              ))
    return STEP_4


def get_step_5(update, context):
    answer = update.message.text
    context.user_data['step_4'] = 1 if answer == 'Да' else 0
    reply_keyboard = ['Нет', 'Да']
    update.message.reply_text('Вас беспокоят морщины на лице?',
                              reply_markup=ReplyKeyboardMarkup(
                                  [reply_keyboard],
                                  one_time_keyboard=True
                              ))
    return STEP_5


def get_step_6(update, context):
    answer = update.message.text
    context.user_data['step_5'] = 1 if answer == 'Да' else 0
    reply_keyboard = ['Нет', 'Да']
    update.message.reply_text('У вас бывали раздражения от холода/ветра/воды?',
                              reply_markup=ReplyKeyboardMarkup(
                                  [reply_keyboard],
                                  one_time_keyboard=True
                              ))
    return STEP_6


def get_step_7(update, context):
    answer = update.message.text
    context.user_data['step_6'] = 1 if answer == 'Да' else 0
    reply_keyboard = ['Нет', 'Да']
    update.message.reply_text('Какими средствами для лица обычно пользуетесь? Какая ценовая категория?',
                              # reply_markup=ReplyKeyboardMarkup(
                              #    [reply_keyboard],
                              #    one_time_keyboard=True
                              )
    return STEP_7


def finalize_test(update, context):
    answer = update.message.text
    print('ПОЛУЧЕН ОТВЕТ НА ВОПРОС 7:', answer)
    context.user_data['step_7'] = 0 #1 if answer == 'Да' else 0
    values = context.user_data

    response = requests.get(f'{host_name}/get_illnesses', params=values)

    response = response.json()

    if len(response['illnesses']) == 0:
        update.message.reply_text(f'С вашей кожей все хорошо!')
    else:
        update.message.reply_text(f'Количество потенциальных проблем с кожей: {len(response["illnesses"])}\n'
                                  f'Перечень: ' + ', '.join(response['illnesses']))
        advices = response['advices']
        if 'Рекомендуемые вещества в составе' in advices:
            update.message.reply_text('Рекомендуемые вещества в составе: '
                                      + ','.join(advices['Рекомендуемые вещества в составе']))
            del advices['Рекомендуемые вещества в составе']
        update.message.reply_text("""Рекомендуемые средства:
""" + '\n'.join([k + ': ' + ','.join(response['advices'][k]) for k in advices]))

    return ConversationHandler.END


def get_code_message(update, context):
    update.message.reply_text('Введите номер штрих-кода или пришлите фотографию')
    return ASK_CODE


def get_code_from_text(update, context):
    code = update.message.text
    update.message.reply_text(requests.get(f'{host_name}/get_info/{code}').json()['message'])
    return ConversationHandler.END


def get_code_from_image(update, context):
    path = context.bot.get_file(update.message.photo[-1].file_id).file_path
    print(path)
    with open('file.jpg', 'wb') as f:
        f.write(requests.get(path).content)

    def decode(im):
        # Find barcodes and QR codes
        decoded_objects = pyzbar.decode(im)
        # Print results
        for obj in decoded_objects:
            print('Type : ', obj.type)
            print('Data : ', obj.data, '\n')
        return decoded_objects

    im = cv2.imread('file.jpg')
    decodedObjects = decode(im)

    if len(decodedObjects) == 0:
        update.message.reply_text('Штрих-коды не обнарудены!')
    elif len(decodedObjects) > 1:
        update.message.reply_text('Несколько штрих-кодов!')
    else:
        update.message.reply_text(requests.get(
            f'{host_name}/get_info/{decodedObjects[0].data.decode("UTF-8")}').json()['message'])

    return ConversationHandler.END


def get_clinic(update, context):
    update.message.reply_text('Мы уже работаем над данной возможностью!')
    print('ПРОИЗОШЕЛ ЗАПРОС КЛИНИКИ!')
    return ConversationHandler.END


def ask_feedback(update, context):
    update.message.reply_text('Введите текст в следующем сообщении.')
    return WAIT_FOR_FEEDBACK


def get_feedback(update, context):
    print('ПОЛУЧЕНА ОБРАТНАЯ СВЯЗЬ:', update.message.text)
    update.message.reply_text('Спасибо за обратную связь, она помогает нам стать лучше!')
    return ConversationHandler.END


def cancel(update, context):
    update.message.reply_text('Выполнение прервано!')

    return ConversationHandler.END


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
        entry_points=[CommandHandler('test', get_step_1),
                      MessageHandler(Filters.regex('Пройти тест'), get_step_1)],
        states={
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
