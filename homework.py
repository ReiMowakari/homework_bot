import logging
import time
import requests
import os

from telebot import TeleBot, apihelper
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

# Настройки логирования.
logging.basicConfig(
    level=logging.INFO,
    filename='log.txt',
    filemode='a',
    format='%(asctime)s:%(levelname)s:%(funcName)s:%(lineno)d - %(message)s',
    encoding='utf-8'
)
logger = logging.getLogger(__name__)
logger.addHandler(
    logging.StreamHandler(),
)


def check_tokens():
    """Функция проверки наличия токенов."""
    no_tokens_msg = (
        'Программа принудительно остановлена. '
        'Отсутствует обязательная переменная окружения: ')
    tokens_bool = True
    required_tokens = (PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
    for token in required_tokens:
        if token is None:
            tokens_bool = False
            logger.critical(
                f'{no_tokens_msg} {token}')
    return tokens_bool


def send_message(bot, message):
    """Функция отправки сообщения в бот."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message
        )
        logger.debug(f'Сообщение отправлено: {message}')
        # Возвращаем булевое значение, что сообщение отправлено.
        return True
    except apihelper.ApiException as error:
        logger.error(f'Возникла ошибка при отправке сообщения: {error}')


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
    except requests.RequestException as re:
        logger.error(re)
        raise Exception(f'Ошибка получение запроса от API Yandex {re}') from re
    if get_api_homeworks.status_code != HTTPStatus.OK:
        message = (
            f'Сбой в работе программы: Эндпоинт {get_api_homeworks.url} '
            f'недоступен по причине {get_api_homeworks.reason} '
            f'{get_api_homeworks.status_code}'
        )
        return message
    return get_api_homeworks.json()


def check_response(response):
    """
    Функция проверки корректности ответа от API.
    :param response: ответ от API, словарь со списком работ и датой.
    :return: список домашних работ.
    """
    if not isinstance(response, dict):
        raise TypeError('Ошибка в типе ответа API, '
                        f'ожидается словарь - получен: {type(response)}')
    required_keys = ('homeworks', 'current_date')
    for key in required_keys:
        if key not in response.keys():
            raise KeyError(f'Ошибка в ответе API, отсутствует ключ - {key}')
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        raise TypeError('Homeworks не является списком')
    return homeworks


def parse_status(homework):
    """
    Функция извлекает из информации о.
    конкретной домашней работе статус этой работы.
    :param homework: принимает конкретную домашнюю работу
    :return: статус работы из словаря HOMEWORK_VERDICTS
    """
    # Если работа по ключу не найдена.
    if 'homework_name' not in homework:
        raise KeyError('В ответе от API отсутствует необходимый ключ.')
    # Получаем название работы по ключу.
    homework_name = homework.get('homework_name')
    # Получаем статус работы.
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_VERDICTS:
        raise AssertionError('Получен неизвестный статус работы'
                             f' {homework_status}')
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    # Создаем объект класса бота.
    bot = TeleBot(token=TELEGRAM_TOKEN)
    # Проверяем, что все переменные есть,
    # иначе ошибка с названием отсутствующей переменной.
    if not check_tokens():
        exit('Программа принудительно остановлена!')
    # Текущее время.
    current_timestamp = int(time.time())
    # Добавляем промежуточный статус работы.
    middle_status = 'reviewing'
    # Добавляем переменную для хранения последней ошибки.
    last_message_error = None
    while True:
        try:
            # Запрашиваем данные через API с текущем временем
            response = get_api_answer(current_timestamp)
            # Проверяем ответ API на корректность и наличие новых работ.
            new_homework = check_response(response)
            # Если новая работа есть и статус,
            # отличный от "в работе" отправляем сообщение.
            if new_homework and middle_status != new_homework[0]['status']:
                message = parse_status(new_homework[0])
                send_message(bot, message)
                middle_status = new_homework[0]['status']
            # Если статус не менялся
            logger.debug('Статус домашней работы не изменился.')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            # Добавляем проверку на избежание дублей.
            if last_message_error != message:
                # Сохраняем результат функции.
                result = send_message(bot, message)
                # Если сообщение отправлено - перезаписываем текст ошибки.
                if result:
                    last_message_error = message
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
