from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import openai
import os
from dotenv import load_dotenv
import markdown  # Ensure this import is included

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

            ai_response = ''
            for chunk in response:
                if 'delta' in chunk.choices[0] and 'content' in chunk.choices[0].delta:
                    ai_content = chunk.choices[0].delta.content
                    ai_response += ai_content

                    # Check if the response contains code blocks (```):
                    if "```" in ai_content:
                        ai_content = markdown.markdown(ai_content, extensions=["fenced_code"])

                    await websocket.send_text(ai_content)

            # Append full AI response to the chat log
            chat_log.append({'role': 'assistant', 'content': ai_response})

        except WebSocketDisconnect:
            print("Client disconnected.")
            break
        except Exception as e:
            error_message = f"Error: {str(e)}"
            print(error_message)
            await websocket.send_text(error_message)
            break
