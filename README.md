# Weather API Project
Этот проект представляет собой API для получения прогноза погоды для отслеживаемых городов, а также для регистрации пользователей, добавляющих города в свой список для отслеживания. Он использует FastAPI для обработки запросов и хранит данные в JSON файлах.
## Установка

1. Клонируйте репозиторий:
    ```bash
    git clone https://github.com/.git
    cd weather-api
    ```

2. Установите виртуальное окружение (рекомендуется):
    ```bash
    python -m venv venv
    source venv/bin/activate  # для Linux или macOS
    venv\Scripts\activate     # для Windows
    ```

3. Установите зависимости:
    ```bash
    pip install -r requirements.txt
    ```

4. Запустите приложение:
    ```bash
    uvicorn main:app --reload
    ```

5. Откройте браузер и перейдите по адресу [http://127.0.0.1:8000](http://127.0.0.1:8000), чтобы использовать API.
