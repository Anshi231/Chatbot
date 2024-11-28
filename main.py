from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Form, Request
import openai
from fastapi.responses import HTMLResponse
import os
from dotenv import load_dotenv
from typing import Annotated
from fastapi.templating import Jinja2Templates

load_dotenv()
api_key = os.getenv('OPENAI_API_KEY')

# Set OpenAI API key
openai.api_key = api_key

app = FastAPI()

templates = Jinja2Templates(directory="Templates")  # Ensure this line is present

chat_responses = []

chat_log = [
    {
        'role': 'system',
        'content': (
            'You are a Python tutor AI, completely dedicated to teaching Python concepts, '
            'best practices, and real-world applications.'
        )
    }
]

# **Add this GET route to handle requests to the root URL**
@app.get("/", response_class=HTMLResponse)
async def chat_page(request: Request):
    return templates.TemplateResponse("home.html", {"request": request, "chat_responses": chat_responses})

@app.websocket("/ws")
async def chat(websocket: WebSocket):
    await websocket.accept()

    while True:
        user_input = await websocket.receive_text()
        chat_log.append({'role': 'user', 'content': user_input})
        chat_responses.append(user_input)

        try:
            response = openai.ChatCompletion.create(
                model='gpt-4',
                messages=chat_log,
                temperature=0.6,
                stream=True
            )

            ai_response = ''

            # Iterate over the streamed chunks
            for chunk in response:
                # Check if 'content' is in the delta to avoid KeyError
                if 'content' in chunk.choices[0].delta:
                    content = chunk.choices[0].delta['content']
                    ai_response += content  # Collect the full response
                    await websocket.send_text(content)  # Stream to client

            # After streaming, append the assistant's response to chat history
            chat_log.append({'role': 'assistant', 'content': ai_response})
            chat_responses.append(ai_response)

        except Exception as e:
            await websocket.send_text(f'Error: {str(e)}')
            break

@app.post("/", response_class=HTMLResponse)
async def chat(request: Request, user_input: Annotated[str, Form()]):
    chat_log.append({'role': 'user', 'content': user_input})
    chat_responses.append(user_input)

    response = openai.ChatCompletion.create(
        model='gpt-4',
        messages=chat_log,
        temperature=0.6
    )

    bot_response = response.choices[0].message.content
    chat_log.append({'role': 'assistant', 'content': bot_response})
    chat_responses.append(bot_response)

    return templates.TemplateResponse("home.html", {"request": request, "chat_responses": chat_responses})

@app.get("/image", response_class=HTMLResponse)
async def image_page(request: Request):
    return templates.TemplateResponse("image.html", {"request": request})

@app.post("/image", response_class=HTMLResponse)
async def create_image(request: Request, user_input: Annotated[str, Form()]):
    response = openai.Image.create(
        prompt=user_input,
        n=1,
        size="256x256"
    )

    image_url = response['data'][0]['url']
    return templates.TemplateResponse("image.html", {"request": request, "image_url": image_url})
