import requests
import json
import os
from tqdm import tqdm
from datetime import datetime, timezone

class VK:
    """
    Класс для взаимодействия с API VK.
    """
    def __init__(self, access_token):
        """
        Инициализация класса VK.

        :param access_token: Токен доступа к API VK.
        """
        self.access_token = access_token

    def get_photos(self, user_id):
        """
        Получает фотографии пользователя с профиля VK.

        :param user_id: ID пользователя VK.
        :return: Список фотографий.
        """
        url = 'https://api.vk.com/method/photos.get'
        params = {
            'owner_id': user_id,
            'album_id': 'profile',
            'extended': 1,
            'access_token': self.access_token,
            'v': '5.131'
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json().get('response', {}).get('items', [])

class YandexDisk:
    """
    Класс для взаимодействия с API Яндекс.Диска.
    """
    def __init__(self, token):
        """
        Инициализация класса YandexDisk.

        :param token: Токен доступа к API Яндекс.Диска.
        """
        self.token = token

    def get_upload_link(self, file_path):
        """
        Получает ссылку для загрузки файла на Яндекс.Диск.

        :param file_path: Путь к файлу на диске.
        :return: Ссылка для загрузки.
        """
        url = 'https://cloud-api.yandex.net/v1/disk/resources/upload'
        headers = {'Authorization': f'OAuth {self.token}'}
        params = {'path': file_path, 'overwrite': 'true'}
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json().get('href')

    def upload_file(self, file_path, file_name):
        """
        Загружает файл на Яндекс.Диск.

        :param file_path: Путь к файлу на локальном диске.
        :param file_name: Имя файла на Яндекс.Диске.
        """
        href = self.get_upload_link(f'vk_photos/{file_name}')
        with open(file_path, 'rb') as file:
            requests.put(href, files={'file': file})
            requests.put(href, files={'file': file}).raise_for_status()

class PhotoBackup:
    """
    Класс для резервного копирования фотографий с VK на Яндекс.Диск.
    """
    def __init__(self, vk, yandex_disk):
        """
        Инициализация класса PhotoBackup.

        :param vk: Экземпляр класса VK.
        :param yandex_disk: Экземпляр класса YandexDisk.
        """
        self.vk = vk
        self.yandex_disk = yandex_disk

    def get_max_size_photo(self, photo):
        """
        Находит фотографию максимального размера.

        :param photo: Словарь с информацией о фотографии.
        :return: Словарь с информацией о фотографии максимального размера.
        """
        return max(photo['sizes'], key=lambda x: x['width'] * x['height'])

    def download_and_upload_photos(self, photos, count=5):
        """
        Скачивает и загружает фотографии на Яндекс.Диск.

        :param photos: Список фотографий.
        :param count: Количество фотографий для скачивания (по умолчанию 5).
        :return: Список информации о загруженных фотографиях.
        """
        photos_info = []
        for photo in tqdm(photos[:count], desc='Downloading photos'):
            max_size = self.get_max_size_photo(photo)
            url = max_size['url']
            likes = photo['likes']['count']
            date = datetime.fromtimestamp(photo['date'], timezone.utc).strftime('%Y-%m-%d')
            file_name = f'{likes}_{date}.jpg'
            response = requests.get(url)
            response.raise_for_status()
            with open(file_name, 'wb') as file:
                file.write(response.content)
            self.yandex_disk.upload_file(file_name, file_name)
            photos_info.append({'file_name': file_name, 'size': max_size['type']})
            os.remove(file_name)
        return photos_info

    def save_photos_info(self, photos_info, file_name='photos_info.json'):
        """
        Сохраняет информацию о загруженных фотографиях в JSON файл.

        :param photos_info: Список информации о загруженных фотографиях.
        :param file_name: Имя файла для сохранения информации (по умолчанию 'photos_info.json').
        """
        with open(file_name, 'w') as json_file:
            json.dump(photos_info, json_file, indent=4)

    def run(self, user_id):
        """
        Запускает процесс резервного копирования фотографий.

        :param user_id: ID пользователя VK.
        """
        photos = self.vk.get_photos(user_id)

        # Вычисляем размеры фотографий
        photos_with_sizes = [(photo, self.get_max_size_photo(photo)['width'] * self.get_max_size_photo(photo)['height']) for photo in photos]

        # Сортируем фотографии по размеру
        photos_with_sizes.sort(key=lambda x: x[1], reverse=True)

        # Берем топ-5 фотографий
        top_photos = [photo for photo, size in photos_with_sizes[:5]]

        photos_info = self.download_and_upload_photos(top_photos)
        self.save_photos_info(photos_info)

def main():
    """
    Основная функция для запуска процесса резервного копирования фотографий.
    """
    user_id = input('Введите ID пользователя VK: ')
    vk_access_token = input('Введите токен VK: ')
    yandex_token = input('Введите токен Яндекс.Диска: ')

    vk = VK(vk_access_token)
    yandex_disk = YandexDisk(yandex_token)
    photo_backup = PhotoBackup(vk, yandex_disk)
    photo_backup.run(user_id)

if __name__ == '__main__':
    main()