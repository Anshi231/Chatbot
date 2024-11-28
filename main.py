from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import openai
import os
from dotenv import load_dotenv
from typing import Annotated

load_dotenv()
api_key = os.getenv('OPENAI_API_KEY')

# Set OpenAI API key
openai.api_key = api_key

app = FastAPI()
templates = Jinja2Templates(directory="Templates")

# Initialize chat log
chat_log = [{'role': 'system', 'content': 'You are a Python tutor AI, dedicated to teaching Python concepts, best practices, and real-world applications.'}]


@app.get("/", response_class=HTMLResponse)
async def chat_page(request: Request):
    headers = {
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache"
    }
    return templates.TemplateResponse("home.html", {"request": request}, headers=headers)


@app.websocket("/ws")
async def chat(websocket: WebSocket):

    await websocket.accept()

    while True:
        user_input = await websocket.receive_text()
        chat_log.append({'role': 'user', 'content': user_input})
        chat_responses.append(user_input)

        try:
            response = openai.chat.completions.create(
                model='gpt-4',
                messages=chat_log,
                temperature=0.6,
                stream=True
            )

            ai_response = ''

            for chunk in response:
                if chunk.choices[0].delta.content is not None:
                    ai_response += chunk.choices[0].delta.content
                    await websocket.send_text(chunk.choices[0].delta.content)
            chat_responses.append(ai_response)

        except Exception as e:
            await websocket.send_text(f'Error: {str(e)}')
            break


@app.post("/", response_class=HTMLResponse)
async def chat(request: Request, user_input: Annotated[str, Form()]):

    chat_log.append({'role': 'user', 'content': user_input})
    chat_responses.append(user_input)

    response = openai.chat.completions.create(
        model='gpt-4',
        messages=chat_log,
        temperature=0.6
    )

    bot_response = response.choices[0].message.content
    chat_log.append({'role': 'assistant', 'content': bot_response})
    chat_responses.append(bot_response)

    return templates.TemplateResponse("home.html", {"request": request, "chat_responses": chat_responses})

@app.post("/image", response_class=HTMLResponse)
async def create_image(request: Request, user_input: Annotated[str, Form()]):
    try:
        response = openai.Image.create(
            prompt=user_input,
            n=1,
            size="256x256"
        )
        image_url = response.data[0].url
        return templates.TemplateResponse("image.html", {"request": request, "image_url": image_url})
    except Exception as e:
        error_message = f"Error generating image: {str(e)}"
        return templates.TemplateResponse("image.html", {"request": request, "error_message": error_message})
