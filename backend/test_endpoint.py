import requests

# Test login
print("Testing login...")
login_response = requests.post('http://localhost:8000/api/v1/auth/login', json={
    'email': 'demo@shot-news.com', 
    'password': 'demo123'
})

print(f"Login status: {login_response.status_code}")
if login_response.status_code == 200:
    data = login_response.json()
    token = data.get('access_token')
    print(f"Token: {token[:50]}...")
    
    # Test digest with token
    print("\nTesting digest with token...")
    headers = {'Authorization': f'Bearer {token}'}
    digest_response = requests.get('http://localhost:8000/api/v1/digest/daily', headers=headers)
    
    print(f"Digest status: {digest_response.status_code}")
    print(f"Digest response: {digest_response.text}")
else:
    print(f"Login error: {login_response.text}")
