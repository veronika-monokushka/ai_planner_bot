import asyncio
import socket
import ssl
import httpx
import requests

async def test_connection():
    print("="*60)
    print("ДИАГНОСТИКА ПОДКЛЮЧЕНИЯ К TELEGRAM API")
    print("="*60)
    
    token = "8745953888:AAEDEbxuIsidFoyUADRB-PDnedg-Epn7mwY"
    url = f"https://api.telegram.org/bot{token}/getMe"
    
    # 1. Проверка DNS
    print("\n1. ПРОВЕРКА DNS:")
    try:
        ip = socket.gethostbyname("api.telegram.org")
        print(f"   ✅ DNS работает: api.telegram.org -> {ip}")
    except Exception as e:
        print(f"   ❌ DNS ошибка: {e}")
    
    # 2. Проверка TCP соединения
    print("\n2. ПРОВЕРКА TCP СОЕДИНЕНИЯ:")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex(("api.telegram.org", 443))
        if result == 0:
            print("   ✅ TCP порт 443 открыт")
        else:
            print(f"   ❌ TCP ошибка: {result}")
        sock.close()
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
    
    # 3. Проверка SSL сертификата
    print("\n3. ПРОВЕРКА SSL:")
    try:
        context = ssl.create_default_context()
        with socket.create_connection(("api.telegram.org", 443), timeout=5) as sock:
            with context.wrap_socket(sock, server_hostname="api.telegram.org") as ssock:
                cert = ssock.getpeercert()
                print(f"   ✅ SSL работает")
                print(f"   Сертификат выдан: {cert.get('issuer', 'Unknown')}")
    except Exception as e:
        print(f"   ❌ SSL ошибка: {e}")
    
    # 4. Проверка через requests (синхронный)
    print("\n4. ПРОВЕРКА ЧЕРЕЗ REQUESTS:")
    try:
        import requests
        response = requests.get(url, timeout=10)
        print(f"   ✅ Requests работает!")
        print(f"   Статус: {response.status_code}")
        print(f"   Ответ: {response.json()}")
    except Exception as e:
        print(f"   ❌ Requests ошибка: {type(e).__name__}: {e}")
    
    # 5. Проверка через httpx (async)
    print("\n5. ПРОВЕРКА ЧЕРЕЗ HTTPX (обычный):")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10)
            print(f"   ✅ HTTPX работает!")
            print(f"   Статус: {response.status_code}")
            print(f"   Ответ: {response.json()}")
    except Exception as e:
        print(f"   ❌ HTTPX ошибка: {type(e).__name__}: {e}")
    
    # 6. Проверка через httpx с отключенной SSL
    print("\n6. ПРОВЕРКА ЧЕРЕЗ HTTPX (SSL отключен):")
    try:
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.get(url, timeout=10)
            print(f"   ✅ HTTPX с verify=False работает!")
            print(f"   Статус: {response.status_code}")
            print(f"   Ответ: {response.json()}")
    except Exception as e:
        print(f"   ❌ HTTPX с verify=False ошибка: {type(e).__name__}: {e}")
    
    # 7. Проверка через curl (если есть)
    print("\n7. ПРОВЕРКА АНТИВИРУСА/БРАНДМАУЭРА:")
    print("   Попробуйте вручную открыть в браузере:")
    print(f"   {url}")
    print("   Если открывается - проблема в Python/библиотеках")
    print("   Если не открывается - проблема в брандмауэре/антивирусе")
    
    print("\n" + "="*60)
    print("ИТОГ:")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(test_connection())