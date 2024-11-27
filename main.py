from fastapi import FastAPI, Form, Request, WebSocket, WebSocketDisconnect
from typing import Annotated
import openai
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('OPENAI_API_KEY')

# Set OpenAI API key
openai.api_key = api_key

app = FastAPI()
templates = Jinja2Templates(directory="Templates")

chat_responses = []

from fastapi.responses import HTMLResponse

@app.get("/", response_class=HTMLResponse)
async def chat_page(request: Request):
    headers = {
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache"
    }
    return templates.TemplateResponse("home.html", {"request": request, "chat_responses": []}, headers=headers)


# Initialize chat log
chat_log = [{'role': 'system',
             'content': 'You are a python tutor AI, completely dedicated to teach users how to learn python from scratch. Please provide clear instructions on the Python concepts, best practices and syntax. Help create a path of learning for users to be able to create real life, production ready python applications.'}]

@app.websocket("/ws")
async def chat(websocket: WebSocket):
    await websocket.accept()
    while True:
        try:
            user_input = await websocket.receive_text()
            chat_log.append({'role': 'user', 'content': user_input})
            chat_responses.append(user_input)

            # Call the OpenAI API with streaming enabled
            response = openai.ChatCompletion.create(
                model='gpt-4',
                messages=chat_log,
                temperature=0.6,
                stream=True
            )

            ai_response = ''
            for chunk in response:  # Use standard `for` loop
                if 'delta' in chunk.choices[0] and 'content' in chunk.choices[0].delta:
                    ai_content = chunk.choices[0].delta.content
                    ai_response += ai_content
                    await websocket.send_text(ai_content)

            # Add the full AI response to chat_log and chat_responses
            chat_log.append({'role': 'assistant', 'content': ai_response})
            chat_responses.append(ai_response)

        except WebSocketDisconnect:
            print("Client disconnected.")
            break
        except Exception as e:
            error_message = f"Error: {str(e)}"
            print(error_message)
            await websocket.send_text(error_message)
            break

@app.get("/image", response_class=HTMLResponse)
async def image_page(request: Request):
    return templates.TemplateResponse("image.html", {"request": request})

@app.post("/image", response_class=HTMLResponse)
async def create_image(request: Request, user_input: Annotated[str, Form()]):
    
    response = openai.Image.create(
        prompt = user_input,
        n=1,
        size="256x256"
    )
    
    image_url = response['data'][0]['url']
    return templates.TemplateResponse("image.html", {"request": request, "image_url": image_url})
