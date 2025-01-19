import pytest
from fastapi.testclient import TestClient
from script import app  # Замените на правильный модуль с вашим FastAPI-приложением

# Фикстура для синхронного клиента
@pytest.fixture
def client():
    client = TestClient(app)
    return client

# Тест 1: Проверка корневого маршрута
def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Weather API Server is running"}

# Тест 2: Проверка получения данных о погоде
def test_get_weather(client):
    response = client.get("/weather?latitude=40.7128&longitude=-74.0060")
    assert response.status_code == 200
    assert "temperature" in response.json()

# Тест 3: Добавление города
def test_add_city(client):
    response = client.post(
        "/add_city",
        params={"city_name": "New York", "latitude": 40.7128, "longitude": -74.0060},
    )
    assert response.status_code == 200

# Тест 4: Получение списка отслеживаемых городов
def test_get_tracked_cities(client):
    response = client.get("/tracked_cities")
    assert response.status_code == 200
    assert isinstance(response.json(), dict)

# Тест 5: Регистрация пользователя
def test_register_user(client):
    response = client.post("/register_user", json={"username": "test_user"})
    assert response.status_code == 200
    assert "user_id" in response.json()

# Тест 6: Добавление города для пользователя
def test_add_city_to_user(client):
    # Зарегистрировать пользователя
    user_response = client.post("/register_user", json={"username": "test_user2"})
    assert user_response.status_code == 200
    user_id = user_response.json().get("user_id")

    # Добавить город с координатами для пользователя
    city_data = {
        "city_name": "New York",
        "latitude": 40.7128,
        "longitude": -74.0060
    }
    response = client.post(
        f"/add_city/{user_id}",  # Используем путь с {user_id}
        json=city_data,
    )
    assert response.status_code == 200
    assert response.json() == {"message": "Город добавлен.", "cities": [city_data]}

# Тест 7: Получение погоды для пользователя
def test_get_weather_for_user(client):
    # Зарегистрировать пользователя
    user_response = client.post("/register_user", json={"username": "test_user3"})
    assert user_response.status_code == 200
    user_id = user_response.json().get("user_id")

    # Добавить город с координатами для пользователя
    city_data = {
        "city_name": "New York",
        "latitude": 40.7128,
        "longitude": -74.0060
    }
    city_response = client.post(
        f"/add_city/{user_id}",  # Используем путь с {user_id}
        json=city_data,
    )
    assert city_response.status_code == 200

    # Получить погоду для города пользователя
    response = client.get(f"/weather/{user_id}?city_name=New York")
    assert response.status_code == 200
    assert "temperature" in response.json()

