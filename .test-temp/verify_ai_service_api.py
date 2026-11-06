import asyncio
import sys
sys.path.insert(0, r'C:\ACP_System\.test-packages')
sys.path.insert(0, r'C:\ACP_System\ahcp-ai-service')
import app
import httpx

async def main():
    transport = httpx.ASGITransport(app=app.app)
    async with httpx.AsyncClient(transport=transport, base_url='http://test') as client:
        headers = {'X-API-Key': 'test-secret'}
        start = await client.post('/session', headers=headers, json={'language': 'en', 'known_answers': {'full_name': 'Saved Patient'}})
        assert start.status_code == 200, start.text
        payload = start.json()
        assert payload['question_number'] == 1
        assert payload['question'] == 'What is your full name?'
        session_id = payload['session_id']
        answer = await client.post('/chat', headers=headers, json={'session_id': session_id, 'message': 'Aarav Sharma'})
        assert answer.status_code == 200, answer.text
        result = answer.json()
        assert result['question_number'] == 1 and result['answer'] == 'Aarav Sharma'
        assert result['next_question']['question_number'] == 2
        print('AI service HTTP endpoints passed: clean Q1, full name saved, DOB next')

asyncio.run(main())
