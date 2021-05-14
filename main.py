import asyncio
import requests
import json
import aiohttp
import lxml
from bs4 import BeautifulSoup as bs
from custom_loger import logger


RESULT = []
headers = {
    'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
    ' (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36',
    'accept-language': 'en-US,en;q=0.9',
}


def get_all_urls(url):  # собираем все url с главной страницы
    page_content = requests.get(url, headers=headers).content.decode('utf-8')
    document = bs(page_content, 'lxml')
    urls = [
        ''.join([
            'https://lite.ua-1x-bet.com', i['href']
            ]) for i in document.find_all(
            'a', {'class': "dashboard-game-block__link dashboard-game-block-link"})
        ]
    logger.info('All urls collected')
    return urls


async def parser(session, url):  # отправляем асинхронно реквесты
    async with session.get(url) as response:
        content = await response.read()
        info = get_items(bs(content.decode('utf-8'), 'lxml'))
        RESULT.append(info)
        logger.info(f'Url {url} done!')


def check_button_status(button):  # проверяем активность опции
    check = button.find_all('span', {'class': "ico market__ico ico--lock"})
    if check:
        return False
    return True


def get_marker_info(all_markers, name):  # собираем информацию по маркетам
    for i in all_markers:
        parse_name = i.find('span', {'class': "game-markets-column__highlight"}).text
        if parse_name == name:
            all_elements = i.find_all('button', {'class': "market game-markets-column__market market market--is-bold-value market--size-m market--theme-gray-100"})
            outcomes = []
            for btn in all_elements:
                values = btn.text.split()
                try:
                    num = float(values[1])
                except ValueError:
                    continue
                temp_dict = {
                    'active': check_button_status(btn),
                    'odd': num,
                    'type': values[0].replace('W', '')
                }
                outcomes.append(temp_dict)
            return outcomes


def get_items(soup):  # получаем json с  одного объекта
    commands = soup.find('div', {'class': "scoreboard-intro"})
    commands_and_score = [i.strip() for i in commands.text.split('\n') if i.strip()]
    all_markers = soup.find_all('div', {'class': "accordion game-markets-column-accordion accordion--theme-gray"})
    res_json = {
        'away': commands_and_score[0],
        'home': commands_and_score[-1],
        'currentScore': f'{commands_and_score[1]}:{commands_and_score[2]}',
        'markets': [{
                     'title': '1X2 Regulartime',
                     'outcomes': get_marker_info(all_markers, '1X2'),
                   },
                    {
                     'title': 'Both Teams To Score',
                     'outcomes': get_marker_info(all_markers, 'Both Teams To Score'),
                    },
                  ]
                 }
    return res_json


async def start(url):  # создаем сессию и задачи
    logger.info('START')
    async with aiohttp.ClientSession(headers=headers) as session:
        tasks = [asyncio.ensure_future(
            parser(session, i)) for i in get_all_urls(url)]
        await asyncio.wait(tasks)


def main(url):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start(BASE_URL))
    with open('results.json', 'w') as json_file:
        json.dump(RESULT, json_file)
    logger.info('Write in to file DOne!')


if __name__ == "__main__":
    BASE_URL = 'https://lite.ua-1x-bet.com/live/Football'
    try:
        main(BASE_URL)
    except ValueError as e:
        logger.error(e)
