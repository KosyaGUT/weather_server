import httpx
import asyncio
import uvicorn
import json
from fastapi import FastAPI, Query, HTTPException
from typing import List
from contextlib import asynccontextmanager
from pydantic import BaseModel
from datetime import datetime

app = FastAPI()

# Пути к JSON файлам
CITIES_FILE = "tracked_cities.json"
USERS_FILE = "users.json"


# Загрузка данных из JSON файлов
def load_json_data(file_path: str):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        return []


def save_json_data(file_path: str, data: list):
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


# Загрузка начальных данных
tracked_cities = load_json_data(CITIES_FILE)
users = load_json_data(USERS_FILE)
user_id_counter = max([user["id"] for user in users], default=0) + 1


@app.get("/")
async def root():
    return {"message": "Weather API Server is running"}


# Метод №1: Получение погоды по координатам
@app.get("/weather")
async def get_weather(latitude: float = Query(...), longitude: float = Query(...)):
    """
    Метод принимает широту и долготу, возвращает текущую погоду.
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current_weather": "true"
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        data = response.json()

    # Извлекаем нужные данные из ответа
    current_weather = data.get("current_weather", {})
    temperature = current_weather.get("temperature")
    wind_speed = current_weather.get("windspeed")
    pressure = current_weather.get("pressure")

    return {
        "temperature": temperature,
        "wind_speed": wind_speed,
        "pressure": pressure
    }


# Метод №2: Добавление города для отслеживания
@app.post("/add_city")
async def add_city(city_name: str, latitude: float, longitude: float):
    """
    Метод принимает название города и его координаты, добавляет город в список для отслеживания.
    """
    # Проверяем, что город ещё не добавлен
    for city in tracked_cities:
        if city["city_name"].lower() == city_name.lower():
            return {"message": f"{city_name} уже отслеживается."}

    # Добавляем город в список
    tracked_cities.append({
        "city_name": city_name,
        "latitude": latitude,
        "longitude": longitude,
        "weather": None  # Погода будет обновлена позже
    })

    # Сохраняем обновлённый список городов в файл
    save_json_data(CITIES_FILE, tracked_cities)

    return {"message": f"{city_name} был добавлен в список отслеживания."}


async def update_weather():
    """
    Фоновая задача для обновления погоды каждые 15 минут.
    """
    while True:
        for city in tracked_cities:
            url = "https://api.open-meteo.com/v1/forecast"
            params = {
                "latitude": city["latitude"],
                "longitude": city["longitude"],
                "current_weather": "true"
            }
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(url, params=params)
                    data = response.json()
                    current_weather = data.get("current_weather", {})
                    city["weather"] = {
                        "temperature": current_weather.get("temperature"),
                        "wind_speed": current_weather.get("windspeed"),
                        "pressure": current_weather.get("pressure")
                    }
            except Exception as e:
                print(f"Ошибка обновления погоды для {city['city_name']}: {e}")

        # Сохраняем обновлённые данные о городах в файл
        save_json_data(CITIES_FILE, tracked_cities)

        print("Обновление погоды завершено.")
        await asyncio.sleep(900)  # 15 минут


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Контекстный менеджер для управления жизненным циклом приложения.
    """
    task = asyncio.create_task(update_weather())  # Запускаем обновление погоды
    yield  # Ожидаем работы приложения
    task.cancel()  # Завершаем фоновую задачу при завершении приложения


# Назначаем lifespan для приложения
app.router.lifespan_context = lifespan


# Метод №3: Получение списка отслеживаемых городов
@app.get("/tracked_cities")
async def get_tracked_cities():
    """
    Метод возвращает список городов, для которых доступен прогноз погоды.
    """
    if not tracked_cities:
        return {"message": "Нет отслеживаемых городов."}

    cities = [city["city_name"] for city in tracked_cities]
    return {"tracked_cities": cities}


# Модуль №3.1: Отобразить погоду города
@app.get("/tracked_cities/{city_name}")
async def get_tracked_city(city_name: str):
    """
    Отображает погоду для указанного города, если он есть в списке отслеживаемых городов.
    Если данные о погоде ещё не обновлены, использует метод get_weather.
    """
    # Ищем город в списке отслеживаемых
    for city in tracked_cities:
        if city["city_name"].lower() == city_name.lower():
            # Если данные о погоде есть, возвращаем их
            if city["weather"]:
                return {
                    "city_name": city["city_name"],
                    "latitude": city["latitude"],
                    "longitude": city["longitude"],
                    "weather": city["weather"]
                }
            else:
                # Если данных о погоде нет, используем метод get_weather для получения данных
                weather_data = await get_weather(latitude=city["latitude"], longitude=city["longitude"])
                return {
                    "city_name": city["city_name"],
                    "latitude": city["latitude"],
                    "longitude": city["longitude"],
                    "weather": weather_data
                }

    # Если город не найден
    return {"message": f"Город {city_name} не найден в списке отслеживаемых."}


@app.get("/weather_by_city_and_time")
async def get_weather_by_city_and_time(
        city_name: str,
        datetime_str: str = Query(..., description="Дата и время в формате YYYY-MM-DD HH:MM"),
        parameters: List[str] = Query(
            ...,
            description="Параметры погоды, например: temperature, wind_speed, precipitation"
        ),
):
    """
    Возвращает прогноз погоды для указанного города, даты и времени по заданным параметрам.
    """
    # Ищем город в списке отслеживаемых
    city = next((c for c in tracked_cities if c["city_name"].lower() == city_name.lower()), None)
    if not city:
        return {"error": f"Город {city_name} не найден в списке отслеживаемых."}

    # Параметры для запроса к Open-Meteo
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": city["latitude"],
        "longitude": city["longitude"],
        "hourly": ",".join(parameters),
        "timezone": "auto",
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            data = response.json()
    except Exception as e:
        return {"error": f"Ошибка при запросе к API: {e}"}

    # Проверяем наличие данных
    hourly_data = data.get("hourly", {})
    if not hourly_data:
        return {"error": "Данные о погоде отсутствуют в ответе API."}

    times = hourly_data.get("time", [])
    if not times:
        return {"error": "Временные данные отсутствуют в прогнозе API."}

    # Преобразуем время в datetime
    try:
        forecast_times = [datetime.strptime(t, "%Y-%m-%dT%H:%M") for t in times]
        requested_datetime = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
    except ValueError as e:
        return {"error": f"Неверный формат даты и времени: {e}"}

    # Находим ближайшее время
    closest_index = min(
        range(len(forecast_times)),
        key=lambda i: abs(forecast_times[i] - requested_datetime),
    )

    # Формируем результат для заданных параметров
    result = {}
    for param in parameters:
        if param in hourly_data:
            result[param] = hourly_data[param][closest_index]
        else:
            result[param] = "Нет данных"

    return {
        "city_name": city_name,
        "requested_datetime": requested_datetime.strftime("%Y-%m-%d %H:%M"),
        "closest_time": forecast_times[closest_index].strftime("%Y-%m-%d %H:%M"),
        "weather": result,
    }


# Дополнительное задание №1
# Регистрация пользователя и добавление города для пользователя
class UserRegistration(BaseModel):
    username: str


class City(BaseModel):
    city_name: str
    latitude: float
    longitude: float


# Регистрация пользователя
@app.post("/register_user")
async def register_user(user: UserRegistration):
    global user_id_counter
    if user.username in (u["username"] for u in users):
        raise HTTPException(status_code=400, detail="Пользователь с таким именем уже существует.")
    user_id = user_id_counter
    users.append({
        "id": user_id,
        "username": user.username,
        "cities": []
    })
    user_id_counter += 1

    # Сохраняем обновлённые данные о пользователях в файл
    save_json_data(USERS_FILE, users)

    return {"user_id": user_id, "username": user.username}


# Добавление города пользователю
@app.post("/add_city/{user_id}")
async def add_city(user_id: int, city: City):
    user = next((u for u in users if u["id"] == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден.")
    user["cities"].append(city.dict())

    # Сохраняем обновлённые данные о пользователях в файл
    save_json_data(USERS_FILE, users)

    return {"message": "Город добавлен.", "cities": user["cities"]}


# Метод получения прогноза погоды обновлен для работы с пользователями
@app.get("/weather/{user_id}")
async def get_weather_for_user(user_id: int, city_name: str):
    """
    Получение погоды для города, добавленного пользователем.
    Использует метод №1 для получения данных.
    """
    user = next((u for u in users if u["id"] == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден.")

    city = next((c for c in user["cities"] if c["city_name"].lower() == city_name.lower()), None)
    if not city:
        raise HTTPException(status_code=404, detail=f"Город {city_name} не найден для пользователя.")

    # Вызов метода №1 для получения данных
    return await get_weather(latitude=city["latitude"], longitude=city["longitude"])


if __name__ == "__main__":
    uvicorn.run("main:app", host='127.0.0.1', port=8000, reload=True)
