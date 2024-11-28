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
chat_log = [{'role': 'system', 'content': 'You are a Python tutor AI, completely dedicated to teaching Python concepts, best practices, and real-world applications.'}]


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
        try:
            user_input = await websocket.receive_text()
            chat_log.append({'role': 'user', 'content': user_input})

            # Call OpenAI API with streaming enabled
            response = openai.ChatCompletion.create(
                model='gpt-4',
                messages=chat_log,
                temperature=0.6,
                stream=True
            )

            # Stream the response to the client
            for chunk in response:
                if 'delta' in chunk.choices[0] and 'content' in chunk.choices[0].delta:
                    ai_content = chunk.choices[0].delta.content
                    await websocket.send_text(ai_content)

            # Append full AI response to the chat log
            full_response = "".join([chunk.choices[0].delta.content for chunk in response if 'delta' in chunk.choices[0]])
            chat_log.append({'role': 'assistant', 'content': full_response})

        except WebSocketDisconnect:
            print("Client disconnected.")
            break
        except Exception as e:
            error_message = f"Error: {str(e)}"
            print(error_message)
            await websocket.send_text(error_message)
            break
