import os
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import CommandHandler, MessageHandler, Filters, Updater, ConversationHandler
import configparser
import requests
import pandas as pd

import pyzbar.pyzbar as pyzbar
import cv2

TEST_START, STEP_1, STEP_2, STEP_3, STEP_4, STEP_5 = range(6)
ASK_CODE = 0


config = configparser.ConfigParser()
config.read("config")
host_name = config['BOT']['host']


def start(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="""Hello, my fellow user!

Start /test for completing test
Use /code for scanning or writing code
Try /compliment for good mood""")


def echo(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text="""Are you lost? 
Start /test for completing test
Use /code for scanning or writing code
Try /compliment for good mood""")


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
    update.message.reply_text('Голова болит?',
                              reply_markup=ReplyKeyboardMarkup(
                                  [reply_keyboard],
                                  one_time_keyboard=True
                              ))
    return STEP_1


def get_step_2(update, context):
    answer = update.message.text
    context.user_data['step_1'] = 1 if answer == 'Да' else 0
    reply_keyboard = ['Нет', 'Да']
    update.message.reply_text('А колени болят?',
                              reply_markup=ReplyKeyboardMarkup(
                                  [reply_keyboard],
                                  one_time_keyboard=True
                              ))
    return STEP_2


def get_step_3(update, context):
    answer = update.message.text
    context.user_data['step_2'] = 1 if answer == 'Да' else 0
    reply_keyboard = ['Нет', 'Да']
    update.message.reply_text('А туловище болит?',
                              reply_markup=ReplyKeyboardMarkup(
                                  [reply_keyboard],
                                  one_time_keyboard=True
                              ))
    return STEP_3


def get_step_4(update, context):
    answer = update.message.text
    context.user_data['step_3'] = 1 if answer == 'Да' else 0
    reply_keyboard = ['Нет', 'Да']
    update.message.reply_text('А бок болит?',
                              reply_markup=ReplyKeyboardMarkup(
                                  [reply_keyboard],
                                  one_time_keyboard=True
                              ))
    return STEP_4


def get_step_5(update, context):
    answer = update.message.text
    context.user_data['step_4'] = 1 if answer == 'Да' else 0
    reply_keyboard = ['Нет', 'Да']
    update.message.reply_text('А нога болит?',
                              reply_markup=ReplyKeyboardMarkup(
                                  [reply_keyboard],
                                  one_time_keyboard=True
                              ))
    return STEP_5


def finalize_test(update, context):
    answer = update.message.text
    context.user_data['step_5'] = 1 if answer == 'Да' else 0
    values = context.user_data

    response = requests.get(f'{host_name}/get_illnesses', params=values)

    response = response.json()

    if len(response['illnesses']) == 0:
        update.message.reply_text(f'Вы здоровы!')
    else:
        update.message.reply_text(f'Количество потенциальных болезней: {len(response["illnesses"])}\n'
                                  f'Перечень: ' + ', '.join(response['illnesses']))

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


def cancel(update, context):
    update.message.reply_text('Выполнение прервано!')

    return ConversationHandler.END




def run():
    updater = Updater(token=config['BOT']['token'], use_context=True)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('compliment', get_compliment))
    dispatcher.add_handler(CommandHandler('help', echo))

    test_handler = ConversationHandler(
        entry_points=[CommandHandler('test', get_step_1)],
        states={
            STEP_1: [MessageHandler(Filters.text & ~Filters.command, get_step_2)],
            STEP_2: [MessageHandler(Filters.text & ~Filters.command, get_step_3)],
            STEP_3: [MessageHandler(Filters.text & ~Filters.command, get_step_4)],
            STEP_4: [MessageHandler(Filters.text & ~Filters.command, get_step_5)],
            STEP_5: [MessageHandler(Filters.text & ~Filters.command, finalize_test)]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    dispatcher.add_handler(test_handler)

    code_handler = ConversationHandler(
        entry_points=[CommandHandler('code', get_code_message)],
        states={
            ASK_CODE: [MessageHandler(Filters.text & ~Filters.command, get_code_from_text),
                       MessageHandler(Filters.photo & ~Filters.command, get_code_from_image)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    dispatcher.add_handler(code_handler)

    echo_handler = MessageHandler(Filters.text & (~Filters.command), echo)
    echo_handler2 = MessageHandler(Filters.document & (~Filters.command), echo)
    dispatcher.add_handler(echo_handler)
    dispatcher.add_handler(echo_handler2)

    updater.start_polling()


if __name__ == '__main__':
    run()
