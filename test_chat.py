import requests
import json
import time

def test_chat():
    # Create a session to maintain cookies
    s = requests.Session()
    s.headers.update({
        'User-Agent': 'Mozilla/5.0',
        'Accept': 'text/html,application/json',
        'Accept-Language': 'en-US,en;q=0.5'
    })
    
    # Login first
    login_data = {
        'email': 'test@example.com',
        'password': 'test123'
    }
    
    # Get the login page first to get any CSRF token if needed
    r = s.get('http://127.0.0.1:5000/patient/login', allow_redirects=True)
    print('Login page status:', r.status_code)
    print('Cookies after login page:', s.cookies.get_dict())
    
    # Perform login
    r = s.post('http://127.0.0.1:5000/patient/login', 
               data=login_data, 
               allow_redirects=True)
    print('Login status:', r.status_code)
    print('Login URL after redirect:', r.url)
    print('Cookies after login:', s.cookies.get_dict())
    
    # Small delay to ensure session is established
    time.sleep(1)
    
    # Get the chat page
    r = s.get('http://127.0.0.1:5000/chat')
    print('\nChat page status:', r.status_code)
    print('Cookies before chat:', s.cookies.get_dict())
    
    # Test chat with a simple greeting
    chat_data = {
        'message': 'hi'
    }
    r = s.post('http://127.0.0.1:5000/api/chat', 
               json=chat_data,
               headers={'Content-Type': 'application/json'})
    print('\nChat status:', r.status_code)
    print('Chat response:', r.text)
    
    if r.status_code == 401:
        print('Session cookies:', s.cookies.get_dict())
    
    # Test chat with a herb query
    chat_data = {
        'message': 'Tell me about Ashwagandha'
    }
    r = s.post('http://127.0.0.1:5000/api/chat', 
               json=chat_data,
               headers={'Content-Type': 'application/json'})
    print('\nHerb query status:', r.status_code)
    print('Herb response:', r.text)
    
    # Test chat with a symptom query
    chat_data = {
        'message': 'I have stress and anxiety'
    }
    r = s.post('http://127.0.0.1:5000/api/chat', 
               json=chat_data,
               headers={'Content-Type': 'application/json'})
    print('\nSymptom query status:', r.status_code)
    print('Symptom response:', r.text)

if __name__ == '__main__':
    test_chat() 