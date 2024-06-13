import logging
import sys
import time
import requests
import os


from telebot import TeleBot
from dotenv import load_dotenv
from http import HTTPStatus

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """
    Проверяет доступность переменных окружения.
    :return: True если все переменные доступны,
    False и недоступная переменная в противном случае.
    """
    required_env_vars = ['PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID']
    for var in required_env_vars:
        if not os.getenv(var):
            return False, var
    else:
        return True,


def send_message(bot, message):
    pass


def get_api_answer(timestamp):
    """
    Делает запрос по API, и в случае успеха возвращает список домашних работ.
    :param timestamp: UNIX значение
    :return: список работ, приведенных к типам данных (list)
    """
    # Параметры для вызова API.
    params_to_call = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': {'from_date': timestamp}
    }
    try:
        get_api_homeworks = requests.get(**params_to_call)
        if get_api_homeworks.status_code != HTTPStatus.OK:
            raise logger.error(
                f'Сбой в работе программы: Эндпоинт {get_api_homeworks.url} '
                f'недоступен по причине {get_api_homeworks.reason} '
                f'{get_api_homeworks.status_code}')
        return get_api_homeworks.json()
    except requests.RequestException as re:
        logger.error(re)


def check_response(response):
    """
    Функция проверки корректности ответа от API.
    :param response: ответ от API, словарь со списком работ и датой.
    :return: список домашних работ.
    """
    if not isinstance(response, dict):
        logger.error(f'Ошибка в типе ответа API, '
                     f'ожидается словарь - получен: {type(response)}')
    required_keys = ('homeworks', 'current_date')
    for key in required_keys:
        if key not in response.keys():
            logger.error(f'Ошибка в ответе API, отсутствует ключ - {key}')
    else:
        return response.get('homeworks')


def parse_status(homework):
    pass

    #return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    # Проверяем, что все переменные есть,
    # иначе ошибка с названием отсутствующей переменной.
    if not check_tokens()[0]:
        logger.critical(
            f'Отсутствует обязательная переменная окружения: {check_tokens()[1]}')
        sys.exit('Программа принудительно остановлена!')

    # Создаем объект класса бота.
    bot = TeleBot(token='TELEGRAM_TOKEN')
    # Текущее время.
    current_timestamp = int(time.time())
    chat_id = TELEGRAM_CHAT_ID
    while True:
        try:
            response = get_api_answer(current_timestamp)
            print(response)
            current_timestamp = response.get(
                'current_data', current_timestamp)
            print(current_timestamp)
            check_response(get_api_answer(current_timestamp))
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            print(message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    # Создаем и настраиваем логер.
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler('log.txt', 'a', 'UTF-8')
    handler.setFormatter(logging.Formatter(
        '%(asctime)s:%(levelname)s:%(funcName)s:%(lineno)d - %(message)s'
    ))
    logger.addHandler(handler)
    main()
