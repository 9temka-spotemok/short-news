#!/usr/bin/env python3
"""
Railway Deployment Test Script
Тестирует развернутое приложение на Railway
"""

import asyncio
import httpx
import json
import sys
from typing import Dict, Any

class RailwayTester:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def test_health_endpoint(self) -> bool:
        """Тестирует endpoint /health"""
        print("🔍 Тестирование /health endpoint...")
        
        try:
            response = await self.client.get(f"{self.base_url}/health")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Health check успешен: {data}")
                return True
            else:
                print(f"❌ Health check неуспешен: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка health check: {e}")
            return False
    
    async def test_root_endpoint(self) -> bool:
        """Тестирует корневой endpoint"""
        print("\n🔍 Тестирование корневого endpoint...")
        
        try:
            response = await self.client.get(f"{self.base_url}/")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Корневой endpoint работает: {data}")
                return True
            else:
                print(f"❌ Корневой endpoint не работает: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка корневого endpoint: {e}")
            return False
    
    async def test_migrations_status(self) -> bool:
        """Тестирует статус миграций"""
        print("\n🔍 Тестирование статуса миграций...")
        
        try:
            response = await self.client.get(f"{self.base_url}/migrations/status")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Статус миграций: {data}")
                return True
            else:
                print(f"❌ Ошибка получения статуса миграций: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка статуса миграций: {e}")
            return False
    
    async def test_api_endpoints(self) -> bool:
        """Тестирует основные API endpoints"""
        print("\n🔍 Тестирование API endpoints...")
        
        endpoints = [
            "/api/v1/health",
            "/api/v1/news/",
            "/api/v1/companies/",
            "/api/v1/categories/",
        ]
        
        results = []
        for endpoint in endpoints:
            try:
                response = await self.client.get(f"{self.base_url}{endpoint}")
                
                if response.status_code in [200, 404]:  # 404 может быть нормальным для пустых данных
                    print(f"✅ {endpoint}: {response.status_code}")
                    results.append(True)
                else:
                    print(f"❌ {endpoint}: {response.status_code}")
                    results.append(False)
                    
            except Exception as e:
                print(f"❌ {endpoint}: {e}")
                results.append(False)
        
        return all(results)
    
    async def test_cors_headers(self) -> bool:
        """Тестирует CORS заголовки"""
        print("\n🔍 Тестирование CORS заголовков...")
        
        try:
            response = await self.client.options(f"{self.base_url}/")
            headers = response.headers
            
            cors_headers = [
                'access-control-allow-origin',
                'access-control-allow-methods',
                'access-control-allow-headers'
            ]
            
            found_headers = []
            for header in cors_headers:
                if header in headers:
                    found_headers.append(header)
                    print(f"✅ {header}: {headers[header]}")
                else:
                    print(f"❌ Отсутствует {header}")
            
            if len(found_headers) >= 2:
                print("✅ CORS настроен правильно")
                return True
            else:
                print("❌ CORS настроен неправильно")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка проверки CORS: {e}")
            return False
    
    async def test_response_time(self) -> bool:
        """Тестирует время ответа"""
        print("\n🔍 Тестирование времени ответа...")
        
        try:
            import time
            start_time = time.time()
            
            response = await self.client.get(f"{self.base_url}/health")
            
            end_time = time.time()
            response_time = end_time - start_time
            
            if response.status_code == 200:
                print(f"✅ Время ответа: {response_time:.2f} секунд")
                
                if response_time < 5.0:
                    print("✅ Время ответа в пределах нормы")
                    return True
                else:
                    print("⚠️  Время ответа превышает 5 секунд")
                    return False
            else:
                print(f"❌ Ошибка ответа: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка измерения времени ответа: {e}")
            return False
    
    async def run_all_tests(self) -> Dict[str, bool]:
        """Запускает все тесты"""
        print(f"🚀 Тестирование Railway приложения: {self.base_url}")
        print("=" * 60)
        
        tests = [
            ("Health Check", self.test_health_endpoint),
            ("Root Endpoint", self.test_root_endpoint),
            ("Migrations Status", self.test_migrations_status),
            ("API Endpoints", self.test_api_endpoints),
            ("CORS Headers", self.test_cors_headers),
            ("Response Time", self.test_response_time),
        ]
        
        results = {}
        for test_name, test_func in tests:
            try:
                result = await test_func()
                results[test_name] = result
            except Exception as e:
                print(f"❌ Ошибка в тесте {test_name}: {e}")
                results[test_name] = False
        
        return results
    
    async def close(self):
        """Закрывает HTTP клиент"""
        await self.client.aclose()

async def main():
    """Основная функция"""
    if len(sys.argv) != 2:
        print("Использование: python test_railway.py <URL>")
        print("Пример: python test_railway.py https://your-app.up.railway.app")
        sys.exit(1)
    
    base_url = sys.argv[1]
    
    tester = RailwayTester(base_url)
    
    try:
        results = await tester.run_all_tests()
        
        print("\n" + "=" * 60)
        print("📊 Результаты тестирования:")
        
        passed = 0
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ ПРОЙДЕН" if result else "❌ ПРОВАЛЕН"
            print(f"{test_name}: {status}")
            if result:
                passed += 1
        
        print(f"\nИтого: {passed}/{total} тестов пройдено")
        
        if passed == total:
            print("🎉 Все тесты пройдены! Приложение работает корректно.")
            return 0
        else:
            print("⚠️  Некоторые тесты провалены. Проверьте логи и конфигурацию.")
            return 1
            
    finally:
        await tester.close()

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⏹️  Тестирование прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Неожиданная ошибка: {e}")
        sys.exit(1)
