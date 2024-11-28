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

            # Initialize response
            ai_response = ""

            # Stream response to frontend
            for chunk in response:
                if "choices" in chunk and "delta" in chunk.choices[0]:
                    delta_content = chunk.choices[0].delta.get("content", "")
                    ai_response += delta_content
                    await websocket.send_text(delta_content)

            # Format bullet points for responses
            if user_input.strip().lower().startswith("list") or user_input.strip().endswith("points"):
                ai_response = "- " + "\n- ".join(ai_response.split("\n"))

            # Append full AI response to chat log
            chat_log.append({'role': 'assistant', 'content': ai_response})

        except WebSocketDisconnect:
            print("Client disconnected.")
            break
        except Exception as e:
            error_message = f"Error: {str(e)}"
            print(error_message)
            await websocket.send_text(error_message)
            break


@app.post("/image", response_class=HTMLResponse)
async def create_image(request: Request, user_input: Annotated[str, Form()]):

    response = openai.Image.create(
        prompt=user_input,
        n=1,
        size="256x256"
    )

    image_url = response.data[0].url
    return templates.TemplateResponse("image.html", {"request": request, "image_url": image_url})
